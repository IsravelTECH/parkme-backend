from fastapi import APIRouter, Request
import stripe
import os

router = APIRouter()


stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

@router.post("/create-checkout-session")
async def create_checkout_session(request: Request):
    try:
        data = await request.json()
    except:
        return {"error": "Invalid JSON received"}

    amount = int(data.get("amount", 50))

    if amount < 50:
        amount = 50

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "inr",
                "product_data": {
                    "name": "Parking Booking",
                },
                "unit_amount": amount * 100,
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url="http://127.0.0.1:5500/frontend/paymentsuccess.html",
        cancel_url="http://127.0.0.1:5500/frontend/payment1.html",
    )

    return {"id": session.id}