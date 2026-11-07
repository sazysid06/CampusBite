# CampusBite

CampusBite is a campus food ordering and delivery application. It combines a React frontend, a FastAPI REST API, and a SQLite database to support customers, restaurant owners, and delivery partners.

## What’s implemented

- **Authentication and roles:** registration, JWT login, persisted frontend sessions, protected routes, and role-based pages for customers, restaurant owners, and delivery partners.
- **Restaurant discovery:** browse open restaurants, search the list, view restaurant details, and see available menu items.
- **Cart and checkout:** add menu items to a single-restaurant cart, adjust quantities, retain the cart in browser storage, and submit an order.
- **Order workflow:** customers can view their orders and cancel eligible orders; restaurant owners can advance orders through kitchen statuses; assigned delivery partners can update delivery status.
- **Owner workspace:** create a restaurant, add menu items, view incoming orders, and see backend-provided restaurant analytics.
- **Customer dashboard:** order history and spending insights, plus an AI advisor for questions about the signed-in customer’s own order history.
- **Private AI advisor:** order details are queried using the authenticated customer ID. The backend sends relevant order summaries and aggregates—not delivery addresses—to the AI provider. OpenAI is preferred when configured; Gemini is used as a fallback. The advisor is limited to 10 requests per customer per minute per backend process.
- **Responsive interface:** shared navigation, loading/error/empty states, and layouts for mobile and desktop.
- **Docker deployment:** Compose runs the backend and a production-built React frontend. Nginx serves the frontend, supports React Router deep links, and proxies API requests to the backend.

## Technology

| Area | Stack |
|---|---|
| Frontend | React, Vite, React Router, Axios |
| Backend | Python 3.12 container, FastAPI, Uvicorn, Pydantic |
| Data | SQLAlchemy async, SQLite, Alembic |
| Authentication | JWT bearer tokens, Argon2 password hashing |
| AI | OpenAI Chat Completions with Gemini fallback; Gemini menu recommendations |
| Tests | Pytest, pytest-asyncio, HTTPX |
| Containers | Docker, Docker Compose, Nginx |

## Repository layout

```text
CampusBite/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py                 # Authentication and role dependencies
│   │   │   └── v1/
│   │   │       ├── auth.py             # Registration, login, current profile
│   │   │       ├── orders.py           # Orders, workflow, analytics, AI advisor
│   │   │       ├── recommendations.py  # Gemini menu recommendations
│   │   │       └── restaurants.py      # Restaurants and menu API
│   │   ├── core/
│   │   │   ├── config.py               # Environment-backed settings
│   │   │   ├── database.py             # Async database engine and sessions
│   │   │   └── security.py             # Password hashing and JWT helpers
│   │   ├── models/                     # User, restaurant, menu, and order models
│   │   ├── schemas/                    # API request and response schemas
│   │   ├── services/ai/
│   │   │   ├── advisor.py              # Gemini menu advisor
│   │   │   └── order_history_advisor.py # OpenAI/Gemini order-history advisor
│   │   └── main.py                     # FastAPI app and health endpoint
│   └── scripts/seed.py                 # Optional demo data
├── frontend/
│   ├── src/
│   │   ├── components/                 # Shared UI and protected routing
│   │   ├── context/                    # Authentication and cart state
│   │   ├── pages/                      # Auth, customer, owner, and rider pages
│   │   └── services/                   # Axios API clients
│   ├── Dockerfile                      # Vite build + Nginx runtime image
│   └── nginx.conf                      # SPA fallback and backend API proxy
├── tests/                              # API workflow and advisor tests
├── Dockerfile                          # Backend image
├── docker-compose.yml                  # Backend and frontend services
├── requirements.txt
└── README.md
```

## Run with Docker Compose

Docker is the simplest way to run the full application.

1. Copy the example environment file at the repository root:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Edit `.env`. Replace the JWT secret with a strong random value. Add at least one AI key (`GEMINI_API_KEY` or `OPENAI_API_KEY`) to enable the order-history advisor. Keep secrets in the backend `.env`; do not put them in frontend variables.

   Compose uses the persistent SQLite volume with:

   ```env
   DATABASE_URL=sqlite+aiosqlite:////app/data/campusbite.db
   ```

3. Build and start both services:

   ```powershell
   docker compose up --build -d
   ```

4. Open:

   - Frontend: [http://localhost:3000](http://localhost:3000)
   - API health: [http://localhost:8000/health](http://localhost:8000/health)
   - Interactive API docs (when `DEBUG=True`): [http://localhost:8000/docs](http://localhost:8000/docs)

The frontend container builds the Vite app with Node and serves the static production files through Nginx. Requests to `/api/` are proxied to `backend:8000` on the Compose network. React Router routes such as `/restaurants` therefore work when opened directly.

Useful Compose commands:

```powershell
docker compose ps
docker compose logs -f backend
docker compose logs -f frontend
docker compose exec backend python -m backend.scripts.seed
docker compose exec backend pytest -v
docker compose down
```

The seed command inserts demo users, one restaurant, and menu items if the demo customer is not already present. The SQLite database is stored in the `sqlite_data` named volume and survives `docker compose down`. To remove that volume and its data, use `docker compose down -v`.

## Run locally without Docker

### Backend

Use Python 3.12 or newer supported by the project dependencies.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

For a local SQLite file rather than the Docker data path, set this in `.env`:

```env
DATABASE_URL=sqlite+aiosqlite:///./campusbite.db
```

Run the API from the repository root:

```powershell
uvicorn backend.app.main:app --reload
```

The backend listens on port `8000`.

### Frontend

In another terminal:

```powershell
Set-Location frontend
npm ci
```

Create `frontend/.env.local` with the local backend URL:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

Start the development server:

```powershell
npm run dev
```

Vite prints the frontend URL (normally [http://localhost:5173](http://localhost:5173)). Do not use the Docker-only relative `/api/v1` URL for the Vite dev server unless a Vite proxy is configured.

## Frontend pages

| Route | Role | Purpose |
|---|---|---|
| `/login` | Public | Sign in |
| `/register` | Public | Create an account and choose a role |
| `/restaurants` | Customer | Search and browse open restaurants |
| `/restaurants/:restaurantId` | Customer | Restaurant details and menu |
| `/cart` | Customer | Review cart and submit an order |
| `/dashboard` | Customer | Order history, insights, and order-history AI advisor |
| `/owner/dashboard` | Restaurant owner | Set up restaurant, add menu items, manage orders, view analytics |
| `/rider/dashboard` | Delivery partner | View assigned orders and update delivery status |

Routes are protected by authentication and role. JWTs are stored in browser `localStorage` and attached to API requests by the Axios interceptor.

## API overview

All API routes are under `/api/v1`.

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/auth/register` | Register a user |
| `POST` | `/auth/login` | Get a JWT using form-encoded credentials |
| `GET` | `/auth/me` | Get the authenticated user's profile |
| `GET` | `/restaurants/` | List restaurants |
| `POST` | `/restaurants/` | Create a restaurant (owner) |
| `GET` | `/restaurants/{restaurant_id}` | Get restaurant details and menu |
| `POST` | `/restaurants/{restaurant_id}/items` | Add a menu item (owner) |
| `POST` | `/orders/` | Place an order (customer) |
| `GET` | `/orders/me` | Get orders relevant to the authenticated role |
| `GET` | `/orders/{order_id}` | Get an authorized order |
| `PATCH` | `/orders/{order_id}/status` | Update order status according to role and workflow |
| `POST` | `/orders/{order_id}/assign-rider` | Assign a delivery partner (owner) |
| `GET` | `/orders/insights/summary` | Get customer order statistics and insights |
| `POST` | `/orders/advisor` | Ask a question grounded in the authenticated customer's order history |
| `GET` | `/orders/restaurant/analytics` | Get restaurant-owner analytics |
| `GET` | `/orders/stale-reminders` | Get stale-order reminders (owner) |
| `POST` | `/orders/{order_id}/refund-request` | Request a refund (customer) |
| `POST` | `/orders/{order_id}/refund-decision` | Resolve a refund request (owner) |
| `POST` | `/orders/{order_id}/review` | Review a delivered order (customer) |
| `POST` | `/recommendations/` | Get Gemini recommendations from available menu items |
| `GET` | `/health` | Health check (outside `/api/v1`) |

See `/docs` for request and response schemas when the backend is running with debug docs enabled.

## AI advisor configuration

The order-history advisor works without restaurant/menu inventory, but its history-based answers depend on the signed-in customer having orders. It sends a bounded set of recent orders and aggregate order statistics to the configured provider.

Configure provider keys in the **backend** `.env`:

```env
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-3.8-flash

# Optional; takes precedence over Gemini when configured
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o-mini
```

With Docker Compose, recreate the backend after changing environment variables:

```powershell
docker compose up -d --force-recreate backend
```

Without either key, the advisor returns a configuration error. Provider timeouts and rate limits are surfaced to the user. The advisor's per-customer request limiter is in-memory, so its counts reset when the backend restarts and are not shared across multiple backend replicas.

## Tests and frontend checks

Run the backend tests from the repository root:

```powershell
pytest -v
```

Run the frontend checks:

```powershell
Set-Location frontend
npm run lint
npm run build
```

## Current limitations

- Restaurants and menus must be created or seeded before customers can browse and order.
- The backend currently supports adding menu items, but does not expose menu-item editing/deletion or a delivery-partner directory for owner assignment.
- Payments are mock payments; no real payment gateway is connected.
- Reviews and refunds have backend endpoints, but dedicated frontend workflows are not currently exposed.
- The in-memory AI rate limiter is intended for a single backend process, not distributed deployments.

## Security notes

- Never commit `.env` or frontend environment files containing secrets.
- Keep AI provider keys on the backend; Vite variables are bundled into browser code.
- Use a unique, strong `JWT_SECRET_KEY` outside local development.

## License

See [LICENSE](LICENSE) if present in the repository.
