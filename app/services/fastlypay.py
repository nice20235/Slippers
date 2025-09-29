import httpx
import uuid
from typing import Optional, Tuple

BASE_URL = "https://api.fastlypay.local"  # Mock base URL (not actually called)

async def create_payment(amount: float, order_id: int) -> Tuple[str, str]:
    """Mock call to FastlyPay create payment endpoint.
    Returns (payment_uuid, redirect_url).
    In real implementation, you'd sign requests and handle errors.
    """
    # Simulate external API: generate UUID locally
    payment_uuid = str(uuid.uuid4())
    redirect_url = f"https://fastlypay.local/pay/{payment_uuid}?order_id={order_id}"
    # Example of how a real call would look (kept commented):
    # async with httpx.AsyncClient(timeout=10) as client:
    #     resp = await client.post(f"{BASE_URL}/payments", json={"amount": amount, "order_id": order_id})
    #     resp.raise_for_status()
    #     data = resp.json()
    #     payment_uuid = data["payment_uuid"]
    #     redirect_url = data["redirect_url"]
    return payment_uuid, redirect_url

async def refund_payment(payment_uuid: str) -> bool:
    """Mock call to FastlyPay refund endpoint.
    Returns True if refund accepted.
    """
    # async with httpx.AsyncClient(timeout=10) as client:
    #     resp = await client.post(f"{BASE_URL}/refunds", json={"payment_uuid": payment_uuid})
    #     resp.raise_for_status()
    #     data = resp.json()
    #     return data.get("status") == "ok"
    return True