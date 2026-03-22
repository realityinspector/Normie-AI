# NORMALAIZER

AI-powered real-time communication bridge between neurotypical and neurodivergent people.

## What it does

NORMALAIZER translates messages between communication styles using Claude AI. Send a message in your natural style, and recipients see it translated to theirs — in real-time via WebSocket chat.

## Tech Stack

- **Backend:** FastAPI (Python 3.12+), async
- **Database:** PostgreSQL via SQLAlchemy + asyncpg
- **Frontend:** Jinja2 templates + Tailwind CSS CDN + Alpine.js
- **AI:** Claude via OpenRouter
- **Payments:** Stripe
- **Auth:** Email/password, Google OAuth, Apple Sign-In
- **Deployment:** Railway (Docker)

## Setup

```bash
cd backend
pip install -e .
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| DATABASE_URL | Yes | PostgreSQL connection string |
| OPENROUTER_API_KEY | Yes | OpenRouter API key for Claude |
| JWT_SECRET | Yes | Secret for signing JWT tokens |
| BASE_URL | Yes | Public URL (e.g. https://your-app.railway.app) |
| GOOGLE_CLIENT_ID | No | Google OAuth client ID |
| STRIPE_SECRET_KEY | No | Stripe secret key |
| STRIPE_PUBLISHABLE_KEY | No | Stripe publishable key |
| STRIPE_WEBHOOK_SECRET | No | Stripe webhook signing secret |
| STRIPE_MONTHLY_PRICE_ID | No | Stripe price ID for monthly plan |
| STRIPE_YEARLY_PRICE_ID | No | Stripe price ID for yearly plan |
| CORS_ORIGINS | No | Comma-separated allowed origins |
| DEV_AUTH_ENABLED | No | Set to "true" for test auth endpoint |

### Run locally

```bash
cd backend
uvicorn app.main:app --reload
```

### Deploy to Railway

```bash
cd backend
railway up
```

## API

- Interactive docs: `/docs`
- Developer API: `/developers` (requires auth)
- Health check: `/health`

## iOS App

The iOS app is in `/ios/NORMALIZER/`. It connects to the same backend via REST + WebSocket.
