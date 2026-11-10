# CampusBite

CampusBite is a campus food ordering and delivery application. It combines a React frontend, a FastAPI REST API, and a SQLite database to support customers, restaurant owners, and delivery partners.

## What’s implemented

- **Authentication and roles:** registration, JWT login, persisted frontend sessions, protected routes, and role-based pages for customers, restaurant owners, and delivery partners.
- **Restaurant discovery:** browse open restaurants, search the list, view restaurant details, and see available menu items.
- **Cart and checkout:** add menu items to a single-restaurant cart, adjust quantities, retain the cart in browser storage, and submit an order.
- **Dummy payments and refunds:** orders create a `mock_paid` payment record without a real gateway. Customers can request one refund after delivery; restaurant owners can approve or reject it.
- **Order workflow:** customers can view their orders, cancel eligible orders, and confirm completed deliveries. When a restaurant accepts an order, the backend randomly assigns an available rider; rider availability and progress (to restaurant, at restaurant, picked up, and on route) are tracked until customer confirmation marks the delivery complete and makes the rider available again.
- **Owner workspace:** create a restaurant, add menu items, view incoming orders, resolve refund requests, and see backend-provided restaurant analytics.
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
│   │   │   ├── deps.py                       # Authentication, DB session, role dependencies
│   │   │   └── v1/
│   │   │       ├── __init__.py               # API v1 router composition
│   │   │       ├── auth.py                   # POST /auth/register, POST /auth/login, GET /auth/me
│   │   │       ├── orders.py                 # Order, rider, refund, review, analytics and advisor endpoints:
│   │   │       │                             # POST /orders/, GET /orders/me, GET /orders/{order_id}
│   │   │       │                             # PATCH /orders/{order_id}/status
│   │   │       │                             # PATCH /orders/{order_id}/delivery-status
│   │   │       │                             # GET|PATCH /orders/rider/availability
│   │   │       │                             # POST /orders/{order_id}/refund-request
│   │   │       │                             # POST /orders/{order_id}/refund-decision
│   │   │       │                             # POST /orders/{order_id}/review
│   │   │       │                             # GET /orders/insights/summary
│   │   │       │                             # GET /orders/restaurant/analytics
│   │   │       │                             # GET /orders/stale-reminders, POST /orders/advisor
│   │   │       ├── recommendations.py        # POST /recommendations/
│   │   │       └── restaurants.py            # POST /restaurants/, GET /restaurants/
│   │   │                                     # GET /restaurants/{restaurant_id}
│   │   │                                     # POST /restaurants/{restaurant_id}/items
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py                     # Environment-backed settings
│   │   │   ├── database.py                   # Async SQLAlchemy engine and sessions
│   │   │   └── security.py                   # Password hashing and JWT helpers
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── order.py                      # Orders, items, deliveries, payments, refunds, reviews
│   │   │   ├── restaurant.py                 # Restaurants and menu items
│   │   │   ├── rider.py                      # Rider availability state
│   │   │   └── user.py                       # User accounts and roles
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── order.py                      # Order, delivery, rider and lifecycle schemas
│   │   │   ├── restaurant.py                 # Restaurant and menu schemas
│   │   │   └── user.py                       # Registration, profile and token schemas
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   └── ai/
│   │   │       ├── __init__.py
│   │   │       ├── advisor.py                # Gemini menu recommendation service
│   │   │       └── order_history_advisor.py  # OpenAI/Gemini order-history advisor
│   │   └── main.py                           # FastAPI app, router setup and GET /health
│   └── scripts/
│       ├── __init__.py
│       └── seed.py                           # Optional demo accounts, restaurant and menu
├── frontend/
│   ├── src/
│   │   ├── assets/
│   │   │   ├── hero.png
│   │   │   ├── react.svg
│   │   │   └── vite.svg
│   │   ├── components/
│   │   │   ├── common/
│   │   │   │   ├── AppShell.jsx             # Shared app layout and navigation
│   │   │   │   ├── Feedback.jsx              # Loading, empty and error states
│   │   │   │   └── OrderCard.jsx             # Shared order summary
│   │   │   └── routing/
│   │   │       ├── ProtectedRoute.jsx        # Role-protected routes
│   │   │       └── Unauthorized.jsx           # Unauthorized access page
│   │   ├── context/
│   │   │   ├── AuthContext.jsx                # Authentication provider and session restore
│   │   │   ├── AuthStateContext.js            # Authentication context definition
│   │   │   ├── CartContext.jsx                # Cart provider and persistence
│   │   │   ├── CartStateContext.js            # Cart context definition
│   │   │   ├── useAuth.js                     # Authentication context hook
│   │   │   └── useCart.js                     # Cart context hook
│   │   ├── pages/
│   │   │   ├── auth/
│   │   │   │   ├── Login.jsx                  # Sign in
│   │   │   │   └── Register.jsx               # Account registration
│   │   │   ├── customer/
│   │   │   │   ├── Cart.jsx                   # Checkout and delivery details
│   │   │   │   ├── CustomerDashboard.jsx      # Orders, delivery confirmation and insights
│   │   │   │   ├── RestaurantDetail.jsx      # Restaurant menu and item selection
│   │   │   │   └── RestaurantList.jsx         # Restaurant discovery
│   │   │   ├── owner/
│   │   │   │   └── OwnerDashboard.jsx         # Restaurant, menu and order management
│   │   │   └── rider/
│   │   │       └── DeliveryDashboard.jsx      # Availability and delivery progress tracker
│   │   ├── services/
│   │   │   ├── api.js                         # Axios client, auth headers and error handling
│   │   │   ├── authService.js                 # Authentication API calls
│   │   │   ├── orderService.js                # Order, rider, refund and advisor API calls
│   │   │   └── restaurantService.js           # Restaurant and menu API calls
│   │   ├── utils/
│   │   │   ├── constants.js                   # Shared frontend constants
│   │   │   └── formatters.js                  # Currency, status and error formatting
│   │   ├── App.css
│   │   ├── App.jsx                            # Frontend routes and role-based page mapping
│   │   ├── index.css
│   │   └── main.jsx                           # React entry point
│   ├── public/
│   │   ├── favicon.svg
│   │   └── icons.svg
│   ├── Dockerfile                             # Vite build and Nginx runtime image
│   ├── eslint.config.js
│   ├── index.html
│   ├── nginx.conf                             # SPA fallback and backend API proxy
│   ├── package-lock.json
│   ├── package.json
│   └── vite.config.js
├── tests/
│   ├── __init__.py
│   ├── conftest.py                            # Temporary SQLite test database and API client
│   ├── test_lifecycle.py                      # Order lifecycle and rider assignment tests
│   ├── test_operations.py                     # Reviews, refunds and analytics tests
│   ├── test_order_history_advisor.py          # Order advisor behavior tests
│   └── test_smoke.py                          # Health, restaurant and rider tracker smoke test
├── .github/
│   └── workflows/
│       └── ci.yml                             # Backend tests and frontend checks on push/PR
├── .dockerignore
├── .env.example
├── .gitignore
├── Dockerfile                                 # Backend image; runs smoke test during build
├── docker-compose.yml                         # Backend and frontend services
├── pytest.ini
├── README.md
└── requirements.txt
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
| `/dashboard` | Customer | Order history, delivered-order refund requests, insights, and order-history AI advisor |
| `/owner/dashboard` | Restaurant owner | Set up restaurant, add menu items, manage orders and refunds, view analytics |
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
| `POST` | `/orders/{order_id}/refund-request` | Request a refund after delivery (customer; one request per order, reason required) |
| `POST` | `/orders/{order_id}/refund-decision` | Approve or reject a pending refund (restaurant owner) |
| `POST` | `/orders/{order_id}/review` | Review a delivered order (customer) |
| `POST` | `/recommendations/` | Get Gemini recommendations from available menu items |
| `GET` | `/health` | Health check (outside `/api/v1`) |

See `/docs` for request and response schemas when the backend is running with debug docs enabled.

### Dummy payments and refunds

Orders are placed without a real payment gateway. Each successful order creates a payment record with `mock_paid` status and a mock transaction reference. A customer can submit one refund request after delivery with a reason of 5–1000 characters. The owner of that order's restaurant can approve or reject the pending request. Approval changes the order and payment statuses to `refunded`; rejection records `rejected` on the refund request and leaves the delivered order's payment unchanged.

Customers can request refunds from delivered orders in the customer dashboard. Restaurant owners can review and resolve pending requests in the incoming-orders section of the owner dashboard.

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

## Tests, smoke test, and CI checks

Run the backend smoke test and full test suite from the repository root. The smoke test checks application health, restaurant discovery, rider login/profile, and the rider availability tracker. Test fixtures use a temporary SQLite database and test accounts; they do not use or alter the persistent application database:

```powershell
pytest -v
```

GitHub Actions runs the same backend suite on pushes and pull requests, then checks the frontend with `npm ci`, lint, and a production build. No API keys or production database are required by CI.

For Docker, rebuild the backend image when tests or backend code have changed, then run the suite:

```powershell
docker compose up -d --build backend
docker compose exec backend pytest -v
```

The test database is temporary in both environments. Seeded demo data in the persistent Docker volume is not used by the tests. The backend Docker image build also runs `tests/test_smoke.py`; a failing smoke test fails the build.

Run the frontend checks:

```powershell
Set-Location frontend
npm run lint
npm run build
```

## Current limitations

- Restaurants and menus must be created or seeded before customers can browse and order.
- The backend currently supports adding menu items, but does not expose menu-item editing/deletion.
- Payments are mock payments; no real payment gateway is connected.
- Reviews currently have a backend endpoint but no dedicated frontend workflow.
- The in-memory AI rate limiter is intended for a single backend process, not distributed deployments.

## Security notes

- Never commit `.env` or frontend environment files containing secrets.
- Keep AI provider keys on the backend; Vite variables are bundled into browser code.
- Use a unique, strong `JWT_SECRET_KEY` outside local development.

## License

See [LICENSE](LICENSE) if present in the repository.
