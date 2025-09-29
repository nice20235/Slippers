from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.models.order import Order, OrderStatus
from sqlalchemy import select
from app.services.fastlypay import create_payment, refund_payment

router = APIRouter()

class CreatePaymentIn(BaseModel):
    order_id: int = Field(..., gt=0)

class CreatePaymentOut(BaseModel):
    order_id: int
    redirect_url: str

class RefundIn(BaseModel):
    order_id: int = Field(..., gt=0)

class RefundOut(BaseModel):
    order_id: int
    status: str

async def _get_order(db: AsyncSession, order_id: int) -> Order | None:
    result = await db.execute(select(Order).where(Order.id == order_id))
    return result.scalar_one_or_none()

@router.post("/create-payment", response_model=CreatePaymentOut)
async def create_fastlypay_payment(body: CreatePaymentIn, db: AsyncSession = Depends(get_db)):
    order = await _get_order(db, body.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.payment_uuid:
        # Idempotent: return existing redirect url pattern if already has payment
        # (We don't expose payment_uuid itself.)
        return CreatePaymentOut(order_id=order.id, redirect_url=f"https://fastlypay.local/pay/{order.payment_uuid}?order_id={order.id}")
    payment_uuid, redirect_url = await create_payment(order.total_amount, order.id)
    order.payment_uuid = payment_uuid
    await db.commit()
    return CreatePaymentOut(order_id=order.id, redirect_url=redirect_url)

@router.post("/refund", response_model=RefundOut)
async def refund_fastlypay_payment(body: RefundIn, db: AsyncSession = Depends(get_db)):
    order = await _get_order(db, body.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status == OrderStatus.REFUNDED:
        raise HTTPException(status_code=400, detail="Order already refunded")
    if not order.payment_uuid:
        raise HTTPException(status_code=400, detail="Order has no payment to refund")
    ok = await refund_payment(order.payment_uuid)
    if not ok:
        raise HTTPException(status_code=400, detail="Refund failed")
    order.status = OrderStatus.REFUNDED
    await db.commit()
    return RefundOut(order_id=order.id, status=order.status.value)