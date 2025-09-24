import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, AliasChoices
from typing import Optional, Any, Dict
from app.auth.dependencies import get_current_user, get_current_admin
from app.services.octo import createPayment, refundPayment

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

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"total_sum": 125000, "description": "Оплата заказа #123"},
                {"amount": 125000, "desc": "Оплата заказа #123"},
            ]
        }
    }

class CreatePaymentOut(BaseModel):
    pay_url: str
    payment_uuid: Optional[str] = None

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
async def create_octo_payment(body: CreatePaymentIn, user=Depends(get_current_user)):
    res = await createPayment(body.total_sum, body.description)
    if not res.success or not res.octo_pay_url:
        logger.warning("OCTO createPayment failed: %s", res.errMessage)
        raise HTTPException(status_code=400, detail=res.errMessage or "OCTO error")
    return CreatePaymentOut(pay_url=res.octo_pay_url, payment_uuid=res.octo_payment_UUID)

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

@router.post("/notify", summary="Octo notify webhook")
async def octo_notify(request: Request, body: OctoNotifyIn):
    try:
        payload = await request.json()
    except Exception:
        payload = body.model_dump() if body else {}
    logger.info("OCTO notify received: %s", payload)
    # Here you can verify signatures if OCTO provides, and update order statuses accordingly.
    return {"ok": True}
