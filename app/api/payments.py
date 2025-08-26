import os
import requests
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Optional

API_URL = "https://ecom.ipakyulibank.uz/api/transfer"
ACCESS_TOKEN = os.getenv("IPAKYULI_ACCESS_TOKEN")

payments_router = APIRouter(prefix="/payments", tags=["payments"])

# Pydantic models
class PaymentCreateRequest(BaseModel):
    order_id: str = Field(...)
    amount: int = Field(..., gt=0)
    description: str = Field(...)
    success_url: str = Field(...)
    fail_url: str = Field(...)

class PaymentCreateResponse(BaseModel):
    transfer_id: str
    payment_url: str

class PaymentStatusResponse(BaseModel):
    status: str
    details: dict

class PaymentCancelRequest(BaseModel):
    transfer_id: str

class PaymentCancelResponse(BaseModel):
    code: int
    message: str

# Helper for auth header
def get_auth_headers():
    if not ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="Bank ACCESS_TOKEN not set")
    return {"Authorization": f"Bearer {ACCESS_TOKEN}"}

# 1. Create payment
@payments_router.post("/create", response_model=PaymentCreateResponse)
def create_payment(data: PaymentCreateRequest):
    payload = {
        "method": "transfer.create_token",
        "params": {
            "order_id": data.order_id,
            "amount": data.amount,
            "description": data.description,
            "success_url": data.success_url,
            "fail_url": data.fail_url
        }
    }
    try:
        resp = requests.post(API_URL, json=payload, headers=get_auth_headers(), timeout=10)
        resp.raise_for_status()
        result = resp.json()
        if result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])
        transfer_id = result["result"]["transfer_id"]
        payment_url = result["result"]["payment_url"]
        return PaymentCreateResponse(transfer_id=transfer_id, payment_url=payment_url)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))

# 2. Check payment status
@payments_router.get("/status/{transfer_id}", response_model=PaymentStatusResponse)
def payment_status(transfer_id: str):
    payload = {
        "method": "transfer.get",
        "params": {"transfer_id": transfer_id}
    }
    try:
        resp = requests.post(API_URL, json=payload, headers=get_auth_headers(), timeout=10)
        resp.raise_for_status()
        result = resp.json()
        if result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])
        status_ = result["result"]["status"]
        details = result["result"]
        return PaymentStatusResponse(status=status_, details=details)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))

# 3. Cancel payment
@payments_router.post("/cancel", response_model=PaymentCancelResponse)
def cancel_payment(data: PaymentCancelRequest):
    payload = {
        "method": "transfer.cancel",
        "params": {"transfer_id": data.transfer_id}
    }
    try:
        resp = requests.post(API_URL, json=payload, headers=get_auth_headers(), timeout=10)
        resp.raise_for_status()
        result = resp.json()
        if result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])
        code = result["result"].get("code", 0)
        message = result["result"].get("message", "")
        return PaymentCancelResponse(code=code, message=message)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))
