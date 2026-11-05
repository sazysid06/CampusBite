# CampusBite – Restaurant Ordering & Delivery Platform

CampusBite is an asynchronous RESTful API backend built for campus food ordering, order lifecycle tracking, and delivery synchronization. The service features role-based access control (RBAC), state-machine validated order flows, automated delivery assignment, and AI recommendations powered by Google Gemini.

---

## Tech Stack

- **Runtime & Framework:** Python 3.14+, FastAPI, Uvicorn (ASGI)
- **Database & ORM:** SQLite via SQLAlchemy 2.0 (`aiosqlite`)
- **Data Validation:** Pydantic v2
- **Auth & Security:** Argon2 password hashing (via Passlib), OAuth2 Bearer Tokens (PyJWT)
- **AI Integration:** Google Gemini API
- **Testing:** Pytest, pytest-asyncio, AnyIO

---

## Core Features

- **Role-Based Access Control (RBAC):** Distinct permissions for `customer`, `restaurant_owner`, `rider`, and `admin`.
- **Order Lifecycle Management:** State-machine enforced transitions: `PLACED` → `CONFIRMED` → `PREPARING` → `READY_FOR_PICKUP` → `OUT_FOR_DELIVERY` → `DELIVERED` (or `CANCELLED`).
- **Delivery Sync:** Decoupled fulfillment logic for rider assignment and transit tracking.
- **AI Food Advisor:** Context-aware meal recommendations using Gemini.

---

## Project Structure

```text
CampusBite/
├── backend/
│   ├── app/
│   │   ├── api/             # API route endpoints
│   │   ├── core/            # Config, security, and auth settings
│   │   ├── db/              # Database engine and sessions
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic models
│   │   └── services/        # Business logic, state machines, AI advisor
│   └── scripts/
│       └── seed.py          # Database seeding script
├── tests/
│   ├── conftest.py          # Pytest fixtures and client setup
│   └── test_lifecycle.py    # Order lifecycle and transition tests
├── .env.example             # Environment variable template
├── .gitignore
├── pytest.ini
├── README.md
└── requirements.txt

Getting Started
1. Clone the Repository
Bash
git clone [https://github.com/sazysid06/CampusBite.git](https://github.com/sazysid06/CampusBite.git)
cd CampusBite
2. Activate Virtual Environment
On Windows (PowerShell):

PowerShell
.\venv\Scripts\Activate.ps1
3. Install Dependencies
PowerShell
pip install -r requirements.txt
4. Configure Environment
Copy .env.example to .env:

PowerShell
Copy-Item .env.example .env
Fill in your credentials in .env:

Code snippet
PROJECT_NAME="CampusBite"
SECRET_KEY="your_secure_secret_key"
ACCESS_TOKEN_EXPIRE_MINUTES=60
DATABASE_URL="sqlite+aiosqlite:///./campusbite.db"
GEMINI_API_KEY="your_gemini_api_key"
GEMINI_MODEL="gemini-3.8-flash"
Running the Project
Seed Demo Data
PowerShell
python -m backend.scripts.seed
Start the Server
PowerShell
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
Interactive Docs (Swagger): http://127.0.0.1:8000/docs

Alternative Docs (ReDoc): http://127.0.0.1:8000/redoc

Running Tests
PowerShell
pytest -v