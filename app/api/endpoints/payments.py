import os
import uuid
import httpx
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List

from app.auth.dependencies import get_current_admin
from app.core.config import settings

IPAKYULI_BASE_URL = "https://ecom.ipakyulibank.uz/api/transfer"
JSON_RPC_VERSION = "2.0"

router = APIRouter()
logger = logging.getLogger("payments")

class PaymentCreateRequest(BaseModel):
    order_id: str = Field(..., description="Your internal order identifier")
    amount: int = Field(..., gt=0, description="Amount in the smallest currency unit (e.g., tiyin)")
    description: str = Field(..., max_length=255)
    success_url: Optional[str] = Field(None, description="Redirect URL after successful payment (defaults to main page)")
    fail_url: str = Field(..., description="Redirect URL after failed/cancelled payment")
    expires_in_minutes: Optional[int] = Field(None, ge=1, le=1440, description="Minutes until transfer expires")
    card_systems: Optional[List[str]] = Field(
        None,
        description="Optional list to restrict allowed card networks, e.g. ['UZCARD','HUMO','VISA','MASTERCARD','UNIONPAY'] if supported by provider/merchant setup"
    )

class PaymentCreateResponse(BaseModel):
    transfer_id: str
    payment_url: str

class PaymentStatusResponse(BaseModel):
    transfer_id: str
    status: str
    amount: int
    order_id: str
    description: Optional[str] = None
    expires_at: Optional[str] = None  # ISO8601 in Tashkent time (UTC+5) if available

class PaymentCancelResponse(BaseModel):
    transfer_id: str
    cancelled: bool
    status: Optional[str] = None

async def call_ipakyuli_api(method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Generic helper for Ipakyuli JSON-RPC calls.

    Error handling strategy:
    - Transport or JSON decode problems => 502
    - JSON-RPC level error object => 400 with code + message
    - Business logic error (result.code != 0) => 400 with code + message
    In all cases we log the upstream payload at WARNING level for traceability (without card data since we never handle it).
    """
    access_token = settings.IPAKYULI_ACCESS_TOKEN
    if not access_token:
        raise HTTPException(status_code=500, detail="IPAKYULI_ACCESS_TOKEN not configured")

    payload = {
        "jsonrpc": JSON_RPC_VERSION,
        "id": uuid.uuid4().hex,
        "method": method,
        "params": params,
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.post(IPAKYULI_BASE_URL, json=payload, headers=headers)
        except httpx.RequestError as e:
            logger.error("Ipakyuli connection error %s %s", method, e)
            raise HTTPException(status_code=502, detail=f"Ipakyuli connection error: {e}")

    try:
        data = resp.json()
    except ValueError:
        logger.error("Invalid JSON from Ipakyuli (%s): %s", method, resp.text[:500])
        raise HTTPException(status_code=502, detail="Invalid JSON response from Ipakyuli")

    # Transport level error
    if "error" in data and data["error"]:
        err = data["error"] or {}
        code = err.get("code")
        message = err.get("message", "Unknown Ipakyuli error")
        logger.warning("Ipakyuli JSON-RPC error method=%s code=%s message=%s payload=%s", method, code, message, data)
        raise HTTPException(status_code=400, detail={"code": code, "message": message})

    result = data.get("result")
    if not result:
        logger.error("Missing result in Ipakyuli response method=%s raw=%s", method, data)
        raise HTTPException(status_code=502, detail="Missing result in Ipakyuli response")

    # Business logic error inside result
    if isinstance(result, dict) and result.get("code", 0) != 0:
        logger.warning("Ipakyuli business error method=%s code=%s message=%s result=%s", method, result.get("code"), result.get("message"), result)
        raise HTTPException(status_code=400, detail={"code": result.get("code"), "message": result.get("message", "Ipakyuli error")})

    logger.debug("Ipakyuli success method=%s result_keys=%s", method, list(result.keys()) if isinstance(result, dict) else type(result))
    return result

@router.post("/create", response_model=PaymentCreateResponse, summary="Create a payment transfer")
async def create_payment(req: PaymentCreateRequest, current_admin: dict = Depends(get_current_admin)):
    # Determine main page
    from app.core.config import settings
    # Pick first allowed origin if configured and not wildcard
    main_origin = None
    if settings.ALLOWED_ORIGINS:
        first = settings.ALLOWED_ORIGINS.split(',')[0].strip()
        if first and first != '*':
            main_origin = first.rstrip('/')
    default_success = (main_origin or '') + '/' if main_origin else '/'

    details = {
        "description": req.description,
        # Provide both snake_case and camelCase keys for redirect URLs to maximize compatibility
        "success_url": (req.success_url or default_success),
        "successUrl": (req.success_url or default_success),
        "fail_url": req.fail_url,
        "failUrl": req.fail_url,
    }

    params = {
        "order_id": req.order_id,
        "amount": req.amount,
        "details": details,
    }
    if req.expires_in_minutes is not None:
        params["expires_in_minutes"] = req.expires_in_minutes
    if req.card_systems:
        # Pass through requested card systems; actual acceptance depends on provider configuration
        params["card_systems"] = req.card_systems

    result = await call_ipakyuli_api("transfer.create_token", params)

    transfer_id = result.get("transfer_id") or result.get("id") or result.get("transferId")
    payment_url = result.get("payment_url") or result.get("payment_url_web") or result.get("url")

    if not transfer_id or not payment_url:
        raise HTTPException(status_code=502, detail="Incomplete create response from Ipakyuli")

    return PaymentCreateResponse(transfer_id=transfer_id, payment_url=payment_url)

@router.get("/{transfer_id}/status", response_model=PaymentStatusResponse, summary="Get payment status")
async def payment_status(transfer_id: str, current_admin: dict = Depends(get_current_admin)):
    # Upstream validation error indicated it expects 'id' (GetTransferByIdDto), so send both keys.
    result = await call_ipakyuli_api("transfer.get", {"id": transfer_id, "transfer_id": transfer_id})
    raw_expires = result.get("expires_at") or result.get("expiresAt")
    tz_expires_str = None
    if raw_expires:
        from datetime import datetime, timezone, timedelta
        iso = raw_expires.replace("Z", "+00:00")
        try:
            dt_utc = datetime.fromisoformat(iso)
            if dt_utc.tzinfo is None:
                dt_utc = dt_utc.replace(tzinfo=timezone.utc)
            tashkent = timezone(timedelta(hours=5))  # UTC+5
            dt_tk = dt_utc.astimezone(tashkent)
            # Human friendly format without microseconds
            tz_expires_str = dt_tk.strftime("%Y-%m-%d %H:%M:%S") 
        except Exception:
            tz_expires_str = raw_expires  # fallback original
    status_out = result.get("status", "unknown")
    return PaymentStatusResponse(
        transfer_id=transfer_id,
        status=status_out,
        amount=result.get("amount", 0),
        # Try multiple possible key styles for order id echo
        order_id=(
            result.get("order_id")
            or result.get("orderId")
            or result.get("merchant_order_id")
            or result.get("merchantOrderId")
            or ""
        ),
        description=(result.get("details") or {}).get("description") if isinstance(result.get("details"), dict) else None,
    expires_at=tz_expires_str,
    )

@router.post("/{transfer_id}/cancel", response_model=PaymentCancelResponse, summary="Cancel a payment transfer")
async def cancel_payment(transfer_id: str, current_admin: dict = Depends(get_current_admin)):
    result = await call_ipakyuli_api("transfer.cancel", {"id": transfer_id, "transfer_id": transfer_id})
    return PaymentCancelResponse(
        transfer_id=transfer_id,
        cancelled=True,
        status=result.get("status"),
    )
