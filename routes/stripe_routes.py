from fastapi import APIRouter, Request
import stripe
import os

router = APIRouter()

@router.post("/create-checkout-session")
async def create_checkout_session(request: Request):

    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

    if not stripe.api_key:
        return {"error": "Stripe key missing"}

    try:
        data = await request.json()
    except:
        data = {}

    amount = int(data.get("amount", 0))

    if amount <= 0:
        return {"error": "Invalid amount"}

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "inr",
                "product_data": {
                    "name": "Parking Booking",
                },
                "unit_amount": amount * 100,  # ₹10 → 1000 paise
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url="https://effortless-choux-d62f15.netlify.app/paymentsuccess.html",
        cancel_url="https://effortless-choux-d62f15.netlify.app/payment1.html",
    )

    return {"id": session.id}