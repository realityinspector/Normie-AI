"""
Discord integration router — Interactions endpoint for bot webhooks.

Discord delivers Interaction payloads (slash commands, message components,
modals) to a single Interactions Endpoint URL via HTTP POST.

## Webhook (Interactions Endpoint)
- **Endpoint:** POST /integrations/discord/webhook
- **Docs:** https://discord.com/developers/docs/interactions/overview
- **Expected payload:**
    ```json
    {
        "id": "interaction_id",
        "application_id": "app_id",
        "type": 1,
        "data": {
            "id": "command_id",
            "name": "translate",
            "options": [
                {"name": "text", "value": "Hello world"}
            ]
        },
        "guild_id": "guild_id",
        "channel_id": "channel_id",
        "member": {
            "user": {"id": "user_id", "username": "someone"}
        },
        "token": "interaction_token"
    }
    ```
- **Verification:** Discord uses Ed25519 signature verification.
  Headers: `X-Signature-Ed25519` and `X-Signature-Timestamp`.
  The signed payload is `{timestamp}{raw_body}`.
  https://discord.com/developers/docs/interactions/overview#setting-up-an-endpoint
- **Ping:** Discord sends a type=1 PING interaction during endpoint
  registration that must be answered with `{"type": 1}`.

## Interaction Types
- Type 1: PING (endpoint verification)
- Type 2: APPLICATION_COMMAND (slash commands)
- Type 3: MESSAGE_COMPONENT (buttons, selects)
- Type 5: MODAL_SUBMIT
"""

from fastapi import APIRouter, Request

from .base import raise_not_implemented

router = APIRouter(prefix="/discord", tags=["integrations-discord"])


@router.post("/webhook")
async def discord_webhook(request: Request):
    """Receive Discord Interactions (slash commands, components, modals).

    TODO:
    - Verify Ed25519 signature (X-Signature-Ed25519 + X-Signature-Timestamp)
    - Handle type=1 PING with {"type": 1} response
    - Route APPLICATION_COMMAND interactions to handlers
    - Implement /translate slash command
    - Return interaction responses within 3 seconds
    - Use deferred responses + followup for longer operations
    """
    raise_not_implemented("Discord")
