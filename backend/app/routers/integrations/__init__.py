"""
Bot integration routers for external platform webhooks.

This package provides webhook endpoints for third-party messaging platforms.
Each integration follows a common pattern:

1. **Receive** — Accept incoming webhook POST from the platform
2. **Verify** — Validate request authenticity using platform-specific signatures
3. **Route** — Dispatch to the appropriate handler based on event/command type
4. **Translate** — Use the NORMALIZER translation engine to process messages
5. **Respond** — Send the translated response back via the platform's API

Currently supported (as stubs):
- Slack (Events API + Slash Commands)
- Discord (Interactions Endpoint)
- Telegram (Bot API Webhooks)

All endpoints return 501 Not Implemented until the integrations are built out.
"""

from fastapi import APIRouter

from .discord import router as discord_router
from .slack import router as slack_router
from .telegram import router as telegram_router

router = APIRouter()
router.include_router(slack_router)
router.include_router(discord_router)
router.include_router(telegram_router)
