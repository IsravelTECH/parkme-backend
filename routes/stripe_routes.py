import os
import stripe
from fastapi import APIRouter, Request, HTTPException
from database import database
from bson import ObjectId
from datetime import datetime, timezone

router = APIRouter()

@router.post("/create-checkout-session")
async def create_checkout_session(request: Request):
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

    if not stripe.api_key:
        return {"error": "Stripe configuration key missing"}

    try:
        data = await request.json()
    except Exception:
        return {"error": "Invalid JSON format"}

    booking_id = data.get("booking_id")
    if not booking_id:
        return {"error": "Missing booking_id"}

    try:
        booking = await database.bookings.find_one({"_id": ObjectId(booking_id)})
    except Exception:
        return {"error": "Invalid booking ID format"}

    if not booking:
        return {"error": "Booking not found"}

    # Minimum Stripe INR checkout amount is ₹50
    amount = int(booking.get("total_price", 0))
    if amount < 50:
        amount = 50

    frontend_url = os.getenv("FRONTEND_URL", "https://effortless-choux-d62f15.netlify.app").rstrip("/")

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "inr",
                    "product_data": {
                        "name": f"Parking Reservation - {booking.get('parking_name', 'Spot')}",
                    },
                    "unit_amount": amount * 100,  # paise
                },
                "quantity": 1,
            }],
            mode="payment",
            metadata={
                "booking_id": str(booking_id)
            },
            success_url=f"{frontend_url}/paymentsuccess.html?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{frontend_url}/payment1.html",
        )

        return {"id": session.id}

    except Exception as e:
        print("STRIPE ERROR:", e)
        return {"error": "Failed to create Stripe payment session"}

@router.post("/stripe-webhook")
async def stripe_webhook(request: Request):
    """
    Asynchronous server-side Stripe webhook handler.
    Ensures that bookings are confirmed and slots reserved even if
    the user's browser closes before redirecting to paymentsuccess.html.
    """
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    # If webhook secret is configured, verify signature
    if webhook_secret and sig_header:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Webhook signature verification failed: {e}")
    else:
        # Fallback to direct event json parsing if secret is not set in dev
        import json
        try:
            event = json.loads(payload.decode("utf-8"))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid webhook payload")

    event_type = event.get("type")

    if event_type == "checkout.session.completed":
        session = event.get("data", {}).get("object", {})
        booking_id = session.get("metadata", {}).get("booking_id")

        if booking_id:
            try:
                booking = await database.bookings.find_one({"_id": ObjectId(booking_id)})
                if booking and booking.get("status") != "active":
                    # Atomically decrement slot
                    await database.parkings.update_one(
                        {"_id": ObjectId(booking["parking_id"]), "available_slots": {"$gt": 0}},
                        {"$inc": {"available_slots": -1}}
                    )
                    # Activate booking
                    await database.bookings.update_one(
                        {"_id": ObjectId(booking_id)},
                        {"$set": {"status": "active", "paid_at": datetime.now(timezone.utc)}}
                    )
            except Exception as err:
                print("Error processing webhook booking activation:", err)

    return {"status": "success"}