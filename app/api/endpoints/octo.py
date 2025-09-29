import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Body
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from app.auth.dependencies import get_current_user, get_current_admin
from app.services.octo import createPayment, refundPayment
from app.db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.payment import create_payment, get_payment_by_uuid, get_payment_by_shop_tx, update_payment_status
from app.models.payment import PaymentStatus
from app.crud.order import update_order_status
from app.models.order import OrderStatus
from app.core.cache import invalidate_cache_pattern

router = APIRouter()
logger = logging.getLogger(__name__)

class CreatePaymentIn(BaseModel):
    order_id: int = Field(..., ge=1, description="ID заказа (internal numeric primary key)")
    model_config = {
        "json_schema_extra": {
            "example": {"order_id": 2},
        }
    }

class CreatePaymentOut(BaseModel):
    pay_url: str
    payment_uuid: Optional[str] = None
    shop_transaction_id: Optional[str] = None
    order_id: Optional[int] = None

class RefundIn(BaseModel):
    payment_uuid: str
    amount: int = Field(..., gt=0, description="Сумма возврата в UZS")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "payment_uuid": "f4f28a3e-3b60-4a3a-8c2e-0e9f7a1e8b05",
                "amount": 13000
            }
        }
    }

class RefundOut(BaseModel):
    success: bool
    message: Optional[str] = None

@router.post("/create", response_model=CreatePaymentOut, summary="Create Octo Payment (by order only)", responses={
    200: {
        "description": "Ссылка на оплату создана",
        "content": {
            "application/json": {
                "example": {
                    "pay_url": "https://octo.uz/pay/abcd...",
                    "payment_uuid": "f4f28a3e-3b60-4a3a-8c2e-0e9f7a1e8b05"
                }
            }
        }
    },
    400: {
        "description": "Ошибка OCTO",
        "content": {
            "application/json": {
                "example": {"detail": "Merchant status [emailok] is not allowed for non-test Payments."}
            }
        }
    }
})
async def create_octo_payment(
    body: CreatePaymentIn = Body(..., example={"order_id": 2}),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Load order to derive amount & description
    from app.crud.order import get_order
    order = await get_order(db, body.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    total_sum = int(round(order.total_amount))
    if total_sum <= 0:
        raise HTTPException(status_code=400, detail="Order total is zero; cannot create payment")
    description = f"Оплата заказа #{order.order_id}" if getattr(order, 'order_id', None) else f"Оплата заказа {order.id}"
    res = await createPayment(total_sum, description)
    if not res.success or not res.octo_pay_url:
        logger.warning("OCTO createPayment failed: %s", res.errMessage)
        raise HTTPException(status_code=400, detail=res.errMessage or "OCTO error")
    # Persist a payment row for tracking
    try:
        if res.shop_transaction_id:
            await create_payment(
                db,
                shop_transaction_id=res.shop_transaction_id,
                amount=float(total_sum),
                currency="UZS",
                order_id=body.order_id,
                octo_payment_uuid=res.octo_payment_UUID,
            )
    except Exception as e:
        logger.warning("Failed to persist payment row: %s", e)
    return CreatePaymentOut(
        pay_url=res.octo_pay_url,
        payment_uuid=res.octo_payment_UUID,
        shop_transaction_id=res.shop_transaction_id,
        order_id=body.order_id,
    )

@router.post("/refund", response_model=RefundOut, summary="Refund Octo Payment", responses={
    200: {
        "description": "Возврат инициирован",
        "content": {"application/json": {"example": {"success": True, "message": "Refund initiated"}}}
    },
    400: {
        "description": "Ошибка OCTO",
        "content": {"application/json": {"example": {"detail": "Minimum refund is >= 13000 UZS (1 USD)"}}}
    }
})
async def refund_octo_payment(body: RefundIn, admin=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    res = await refundPayment(body.payment_uuid, body.amount)
    if not res.success:
        logger.warning("OCTO refund failed: %s", res.errMessage)
        raise HTTPException(status_code=400, detail=res.errMessage or "OCTO error")
    payment = await get_payment_by_uuid(db, body.payment_uuid)
    if payment and getattr(payment, "order_id", None):
        try:
            await update_order_status(db, payment.order_id, OrderStatus.REFUNDED)
            logger.info("Order %s set to REFUNDED after refund of payment %s", payment.order_id, payment.id)
        except Exception as e:
            logger.warning("Failed to update order status to REFUNDED: %s", e)
    return RefundOut(success=True, message="Refund initiated; order marked refunded if linked")

# Optional: minimal notify webhook to satisfy notify_url requirement
class OctoNotifyIn(BaseModel):
    payment_uuid: Optional[str] = None
    shop_transaction_id: Optional[str] = None
    status: Optional[str] = None
    amount: Optional[int] = None
    extra: Dict[str, Any] | None = None
    model_config = {
        "json_schema_extra": {
            "example": {
                "shop_transaction_id": "<from_create_payment_response>",
                "status": "paid"
            }
        }
    }

@router.post("/notify", summary="Octo notify webhook")
async def octo_notify(request: Request, body: OctoNotifyIn, db: AsyncSession = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception:
        payload = body.model_dump() if body else {}
    logger.info("OCTO notify received: %s", payload)
    # TODO: verify signature if OCTO provides one
    shop_tx = payload.get("shop_transaction_id") or body.shop_transaction_id
    payment_uuid = payload.get("payment_uuid") or body.payment_uuid
    status = (payload.get("status") or body.status or "").lower()
    # Load payment record by shop_transaction_id first
    payment = None
    if shop_tx:
        payment = await get_payment_by_shop_tx(db, shop_tx)
    if not payment and payment_uuid:
        payment = await get_payment_by_uuid(db, payment_uuid)
    if not payment:
        logger.warning("Payment record not found for notify: shop_tx=%s uuid=%s", shop_tx, payment_uuid)
        return {"ok": True}

    # If payment is not linked to an order, try to bind from payload (best-effort)
    if getattr(payment, "order_id", None) is None:
        try:
            maybe_order_id = (
                payload.get("order_id")
                or payload.get("orderId")
                or (payload.get("extra") or {}).get("orderId")
            )
            if maybe_order_id is not None:
                payment.order_id = int(maybe_order_id)
                db.add(payment)
                await db.commit()
                await db.refresh(payment)
                logger.info("Linked payment %s to order_id=%s from notify payload", payment.id, payment.order_id)
        except Exception as e:
            logger.warning("Failed to link order_id from notify payload: %s", e)
    # Map external status to internal
    mapped = None
    # Normalize and map a broader set of success statuses
    if status in {"paid", "success", "succeeded", "paid_and_captured", "captured", "completed"}:
        mapped = PaymentStatus.PAID
    elif status in {"refunded", "refund"}:
        mapped = PaymentStatus.REFUNDED
    elif status in {"failed", "error"}:
        mapped = PaymentStatus.FAILED
    elif status in {"cancelled", "canceled"}:
        mapped = PaymentStatus.CANCELLED
    else:
        mapped = PaymentStatus.PENDING

    logger.info(
        "Notify status '%s' mapped to %s (payment_id=%s, order_id=%s)",
        status,
        mapped,
        getattr(payment, "id", None),
        getattr(payment, "order_id", None),
    )
    updated = await update_payment_status(
        db,
        payment,
        status=mapped,
        octo_payment_uuid=payment_uuid,
        raw=str(payload)[:3900],
    )
    # Update order status based on payment lifecycle events
    if getattr(updated, "order_id", None):
        if mapped == PaymentStatus.PAID:
            try:
                await update_order_status(db, updated.order_id, OrderStatus.PAID)
                logger.info("Order %s set to PAID due to successful payment %s", updated.order_id, updated.id)
            except Exception as e:
                logger.warning("Failed to update order %s status after payment: %s", updated.order_id, e)
        elif mapped == PaymentStatus.REFUNDED:
            try:
                await update_order_status(db, updated.order_id, OrderStatus.REFUNDED)
                logger.info("Order %s set to REFUNDED due to refund of payment %s", updated.order_id, updated.id)
            except Exception as e:
                logger.warning("Failed to update order %s status after refund: %s", updated.order_id, e)
    elif mapped == PaymentStatus.PAID:
        logger.warning("Payment %s marked PAID but not linked to any order. Ensure orderId is sent on create.", getattr(updated, "id", None))
    # Invalidate caches so clients don't see stale 'pending' orders
    try:
        await invalidate_cache_pattern("orders:")
        if getattr(updated, "order_id", None):
            await invalidate_cache_pattern(f"order:{updated.order_id}:")
    except Exception:
        pass
    return {"ok": True}
