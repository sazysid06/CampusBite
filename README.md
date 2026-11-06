# 🍔 CampusBite — Smart Campus Food Ordering & Delivery Platform

CampusBite is a full-stack, enterprise-grade campus food delivery and dining service backend built with **FastAPI**, **SQLAlchemy 2.0 (Async)**, **SQLite**, and **Google Gemini AI**. Designed specifically for university ecosystems, it orchestrates multi-role access (Students, Restaurant Owners, Delivery Partners, Admins), enforces a strict 7-stage order lifecycle state machine, automates operational analytics, and delivers personalized meal recommendations via generative AI.

---

## 🚀 Key Features

### 1. Robust Authentication & RBAC
- JWT-based authentication (\python-jose\) with secure password hashing (\passlib[argon2]\).
- Fine-grained Role-Based Access Control (RBAC):
  - **Customer / Student:** Browse menus, place orders, track status, submit reviews, request refunds, view AI insights.
  - **Restaurant Owner:** Manage menus, update order statuses (\ccepted\ ➔ \preparing\ ➔ \eady\), assign riders, view revenue analytics, monitor stale orders.
  - **Delivery Partner / Rider:** Accept assignments, mark orders \out_for_delivery\ and \delivered\.
  - **Admin:** System-wide management and operational oversight.

### 2. Strict 7-Stage Order Lifecycle State Machine
Orders enforce atomic database transactions and strict state transitions:
\\\	ext
[placed] ➡️ [accepted] ➡️ [preparing] ➡️ [ready] ➡️ [assigned] ➡️ [out_for_delivery] ➡️ [delivered]
   │             │
   └─────────────┴──────────> [cancelled] (Customer can cancel only prior to preparation)
\\\
- **Guarded Transitions:** Unauthorized role transitions (e.g., owner attempting delivery status updates, customer cancelling mid-preparation) are rejected with clear HTTP 400/403 exceptions.
- **Delivery Integration:** Dynamic assignment of riders with automatic tracking of \pickup_time\ and \delivered_time\.
- **Mock Payment Engine:** Automatic generation of payment records and unique transaction references on order submission.

### 3. Post-Delivery Operations & Governance
- **Reviews & Ratings:** Customers can rate completed orders (1–5 scale with \CheckConstraint\ validation) with optional feedback.
- **Dispute & Refund Workflow:** Formal refund requests for fulfilled orders with owner review and decision tracking (\pproved\ / \ejected\).

### 4. Operations, Analytics & Stale Order Engine
- **Restaurant Performance Analytics:** Real-time computation of \	otal_orders\, \	otal_revenue\, \completed_orders\, \cancelled_orders\, and \efunded_orders\.
- **Timezone-Resilient Stale Order Reminders:** Active query engine that catches stagnant orders exceeding operational thresholds with UTC offset normalization.

### 5. Gemini AI Meal & Spending Advisor
- Integrated with Google Gemini models via \google-genai\.
- Analyzes past ordering patterns, spend velocity, and dietary preferences to deliver concise nutritional summaries and actionable dining suggestions.

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Framework** | FastAPI (Python 3.14+) |
| **Server** | Uvicorn (ASGI) |
| **ORM & Database** | SQLAlchemy 2.0 (Async), Alembic, SQLite |
| **Data Validation** | Pydantic V2 (\ConfigDict\, \model_config\) |
| **Security** | OAuth2 Password Bearer, JWT (\python-jose\), Argon2 (\passlib\) |
| **AI Integration** | Google Gemini AI (\google-genai\) |
| **Testing** | Pytest, Pytest-Asyncio, HTTPX (ASGITransport) |

---

## 📁 Project Architecture

\\\	ext
CampusBite/
├── backend/
│   └── app/
│       ├── api/
│       │   ├── deps.py              # Auth & database dependency injections
│       │   └── v1/
│       │       ├── auth.py          # Registration & JWT token issuance
│       │       ├── orders.py        # Lifecycle, analytics, reviews & AI routes
│       │       └── restaurant.py    # Restaurant & menu management
│       ├── core/
│       │   ├── config.py            # Pydantic settings & env configurations
│       │   ├── database.py          # Async engine & session setup
│       │   └── security.py          # Password hashing & JWT generation
│       ├── models/
│       │   ├── order.py             # Order, Delivery, Payment, Refund, Review models
│       │   ├── restaurant.py        # Restaurant & MenuItem models
│       │   └── user.py              # User & Role models
│       ├── schemas/
│       │   ├── order.py             # Pydantic V2 schemas for order operations
│       │   ├── restaurant.py        # Restaurant/menu request/response schemas
│       │   └── user.py              # User & Token schemas
│       ├── services/
│       │   └── ai_advisor.py        # Gemini AI meal analytics integration
│       └── main.py                  # FastAPI application entrypoint
├── tests/
│   ├── conftest.py                  # Test database fixtures, tokens & mocks
│   ├── test_lifecycle.py            # State machine & RBAC boundary tests
│   └── test_operations.py           # Reviews, refunds, analytics & AI test suite
├── pytest.ini                       # Pytest configuration
├── requirements.txt                 # Project dependencies
└── README.md                        # Documentation
\\\

---

## ⚙️ Installation & Setup

### 1. Prerequisites
- Python 3.10+ (Tested on Python 3.14)
- Git

### 2. Clone Repository & Setup Environment
\\\powershell
# Clone the repository
git clone https://github.com/sazysid06/CampusBite.git
cd CampusBite

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
\\\

### 3. Environment Variables
Create a \.env\ file in the project root:
\\\env
PROJECT_NAME="CampusBite"
SECRET_KEY="your-secure-secret-key"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=1440
DATABASE_URL="sqlite+aiosqlite:///./campusbite.db"
GEMINI_API_KEY="your-gemini-api-key"
\\\

---

## 🏃 Running the Application

Start the development server with live reload:
\\\powershell
uvicorn backend.app.main:app --reload
\\\
- **Interactive Swagger Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Alternative Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🧪 Running Automated Tests

Run the complete test suite covering the 7-stage lifecycle, role restrictions, reviews, refunds, and AI insights:
\\\powershell
pytest -v
\\\

---

## 📖 Primary API Endpoints

### 🔐 Authentication (\/api/v1/auth\)
- \POST /register\ — Register a customer, owner, or delivery partner
- \POST /login\ — Authenticate and receive a Bearer JWT token

### 📦 Orders & Delivery (\/api/v1/orders\)
- \POST /\ — Place a new order with atomic price computation and mock payment
- \GET /{order_id}\ — Retrieve order details including items, delivery status, and review
- \PATCH /{order_id}/status\ — Advance order state (\ccepted\, \preparing\, \eady\, \out_for_delivery\, \delivered\, \cancelled\)
- \POST /{order_id}/assign-rider\ — Assign an available delivery partner to an order
- \POST /{order_id}/review\ — Submit rating and feedback for delivered orders
- \POST /{order_id}/refund\ — Request an order refund
- \PATCH /{order_id}/refund-decision\ — Approve or reject pending refund requests (Owner/Admin)
- \GET /restaurant/analytics\ — Fetch revenue and order completion metrics
- \GET /stale-reminders\ — Identify active orders lagging past threshold durations
- \GET /insights/summary\ — Generate Gemini AI customer order analysis and meal recommendations

---

## 📜 License
This project is open-source and available under the [MIT License](LICENSE).
