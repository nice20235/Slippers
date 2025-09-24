import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Body
from pydantic import BaseModel, Field, AliasChoices
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
    # Accept multiple common keys from frontend: amount/total/total_sum
    total_sum: int = Field(
        ..., gt=0,
        description="Сумма платежа в тийинах (UZS)",
        validation_alias=AliasChoices("total_sum", "amount", "total", "sum"),
    )
    # Accept description/desc/title
    description: str = Field(
        ..., max_length=255,
        description="Краткое описание товара/услуги",
        validation_alias=AliasChoices("description", "desc", "title"),
    )
    # Optional link to an existing order
    order_id: Optional[int] = Field(
        None,
        ge=1,
        description="ID заказа для связывания платежа",
        validation_alias=AliasChoices("order_id", "orderId", "order"),
    )

    model_config = {
        "json_schema_extra": {
            # Keep model examples for schema generators; we'll also set Body examples in the route
            "example": {"total_sum": 125000, "description": "Оплата заказа #123", "orderId": 2},
            "examples": [
                {"total_sum": 125000, "description": "Оплата заказа #123"},
                {"amount": 125000, "desc": "Оплата заказа #123"},
                {"amount": 125000, "title": "Оплата заказа #123", "orderId": 2}
            ]
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

@router.post("/create", response_model=CreatePaymentOut, summary="Create Octo Payment", responses={
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
    body: CreatePaymentIn = Body(
        ...,
        example={
            "total_sum": 125000,
            "description": "Оплата заказа #123",
            "orderId": 2,
        },
        examples={
            "basic": {
                "summary": "Minimal",
                "value": {"total_sum": 125000, "description": "Оплата заказа #123"},
            },
            "withAliases": {
                "summary": "Using aliases",
                "value": {"amount": 125000, "title": "Оплата заказа #123", "orderId": 2},
            },
        },
    ),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await createPayment(body.total_sum, body.description)
    if not res.success or not res.octo_pay_url:
        logger.warning("OCTO createPayment failed: %s", res.errMessage)
        raise HTTPException(status_code=400, detail=res.errMessage or "OCTO error")
    # Persist a payment row for tracking
    try:
        if res.shop_transaction_id:
            await create_payment(
                db,
                shop_transaction_id=res.shop_transaction_id,
                amount=float(body.total_sum),
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
async def refund_octo_payment(body: RefundIn, admin=Depends(get_current_admin)):
    res = await refundPayment(body.payment_uuid, body.amount)
    if not res.success:
        logger.warning("OCTO refund failed: %s", res.errMessage)
        raise HTTPException(status_code=400, detail=res.errMessage or "OCTO error")
    return RefundOut(success=True, message="Refund initiated")

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
    # Map external status to internal
    mapped = None
    if status in {"paid", "success", "paid_and_captured"}:
        mapped = PaymentStatus.PAID
    elif status in {"refunded", "refund"}:
        mapped = PaymentStatus.REFUNDED
    elif status in {"failed", "error"}:
        mapped = PaymentStatus.FAILED
    elif status in {"cancelled", "canceled"}:
        mapped = PaymentStatus.CANCELLED
    else:
        mapped = PaymentStatus.PENDING
    updated = await update_payment_status(
        db,
        payment,
        status=mapped,
        octo_payment_uuid=payment_uuid,
        raw=str(payload)[:3900],
    )
    # If this payment is linked to an order and got paid, confirm the order
    if mapped == PaymentStatus.PAID and getattr(updated, "order_id", None):
        try:
            await update_order_status(db, updated.order_id, OrderStatus.CONFIRMED)
        except Exception as e:
            logger.warning("Failed to update order %s status after payment: %s", updated.order_id, e)
    # Invalidate caches so clients don't see stale 'pending' orders
    try:
        await invalidate_cache_pattern("orders:")
        if getattr(updated, "order_id", None):
            await invalidate_cache_pattern(f"order:{updated.order_id}:")
    except Exception:
        pass
    return {"ok": True}
