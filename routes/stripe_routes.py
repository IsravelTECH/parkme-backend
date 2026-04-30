from fastapi import APIRouter, Request
import stripe
import os
from database import database
from bson import ObjectId

router = APIRouter()

@router.post("/create-checkout-session")
async def create_checkout_session(request: Request):

    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

    if not stripe.api_key:
        return {"error": "Stripe key missing"}

    try:
        data = await request.json()
    except Exception:
        return {"error": "Invalid JSON"}

    booking_id = data.get("booking_id")

    if not booking_id:
        return {"error": "Missing booking_id"}

    # 🔥 GET BOOKING FROM DB
    booking = await database.bookings.find_one({"_id": ObjectId(booking_id)})

    if not booking:
        return {"error": "Booking not found"}

    # ✅ GET REAL AMOUNT FROM DB (IMPORTANT)
    amount = int(booking.get("total_price", 0))

    # ✅ Safety check
    if amount < 50:
        amount = 50

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],

            line_items=[{
                "price_data": {
                    "currency": "inr",
                    "product_data": {
                        "name": f"Parking - {booking.get('parking_name', 'Spot')}",
                    },
                    "unit_amount": amount * 100,  # paise
                },
                "quantity": 1,
            }],

            mode="payment",

            # ✅ VERY IMPORTANT (for success page)
            metadata={
                "booking_id": str(booking_id)
            },

            success_url="https://effortless-choux-d62f15.netlify.app/paymentsuccess.html?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="https://effortless-choux-d62f15.netlify.app/payment1.html",
        )

        return {"id": session.id}

    except Exception as e:
        print("STRIPE ERROR:", e)
        return {"error": "Stripe session failed"}