# ParkMe Backend API 🚗💨

FastAPI & Motor (Async MongoDB) high-performance backend powering the ParkMe Smart City Parking Platform.

---

## 🛠️ Tech Stack & Architecture

- **Framework:** FastAPI (Python 3.14 / 3.12 compatible)
- **Database:** MongoDB Atlas with async Motor driver & 2dsphere Geospatial indexing
- **Security:** JWT authentication, bcrypt password hashing, dynamic origin regex CORS
- **Payments:** Stripe Checkout & server-side asynchronous webhook verification
- **File Storage:** Local secure uploads with MIME type and 5MB size enforcement

---

## 📂 Folder Structure

```
Backend/
├── models/                     # Pydantic validation models
│   ├── booking_model.py
│   ├── parking_model.py
│   └── user_model.py
├── routes/                     # REST API route handlers
│   ├── admin_routes.py         # Executive analytics & management
│   ├── booking_routes.py       # User booking lifecycle
│   ├── parking_routes.py       # Geospatial search, add & book slots
│   ├── profile_routes.py       # User profile & avatar uploads
│   ├── stripe_routes.py        # Stripe sessions & webhooks
│   └── user_routes.py          # Auth (login/signup/reviews)
├── static/                     # User profile photos
├── uploads/                    # Parking space photos
├── utils/                      # Helper libraries
│   ├── auth.py                 # JWT token creation & role verification
│   └── booking_utils.py        # Auto-expiry & slot replenishment
├── .env                        # Active environment secrets
├── .env.example                # Template configuration
├── database.py                 # Motor MongoDB connection pool
├── main.py                     # FastAPI app factory & lifespan
└── requirements.txt            # Python dependencies
```

---

## ⚡ Quickstart

### 1. Configure Environment
Copy `.env.example` to `.env` and provide your secrets:
```bash
cp .env.example .env
```

### 2. Run API Server
Using the project's virtual environment:
```powershell
d:\ParkMe\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000 --host 127.0.0.1
```

Interactive API documentation will be available at:
- Swagger UI: **`http://127.0.0.1:8000/docs`**
- ReDoc: **`http://127.0.0.1:8000/redoc`**

---

## 🔑 Key API Endpoints

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/signup` | Register new driver account | No |
| `POST` | `/login` | Authenticate & obtain JWT | No |
| `GET` | `/parkings` | Retrieve all active parking spaces | No |
| `GET` | `/nearby` | Geospatial 2dsphere radius query | No |
| `POST` | `/book-slot` | Reserve parking slot (pending) | Yes (Bearer) |
| `PUT` | `/complete-booking/{id}` | Atomically lock slot & activate pass | Yes (Bearer) |
| `PUT` | `/cancel-booking/{id}` | Cancel reservation & replenish slot | Yes (Bearer) |
| `GET` | `/user-booking-dashboard` | Driver active passes & history | Yes (Bearer) |
| `GET` | `/my-dashboard` | Host managed spaces & earnings | Yes (Bearer) |
| `POST` | `/add-parking` | Host lists new parking space | Yes (Bearer) |
| `GET` | `/admin-dashboard` | Platform metrics & occupancy rate | Yes (Owner) |
| `POST` | `/create-checkout-session`| Create Stripe payment session | No |
| `POST` | `/stripe-webhook` | Async Stripe event processing | No |
