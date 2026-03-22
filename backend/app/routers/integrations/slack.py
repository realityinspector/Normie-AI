"""
Slack integration router — webhook and slash command endpoints.

Slack sends events and commands to your app via HTTP POST requests.
Before processing, each request must be verified using HMAC-SHA256
with your app's Signing Secret.

## Webhook (Events API)
- **Endpoint:** POST /integrations/slack/webhook
- **Docs:** https://api.slack.com/apis/events-api
- **Expected payload:**
    ```json
    {
        "token": "...",
        "team_id": "T0001",
        "event": {
            "type": "message",
            "channel": "C2147483705",
            "user": "U2147483697",
            "text": "Hello world",
            "ts": "1355517523.000005"
        },
        "type": "event_callback",
        "event_id": "Ev0001",
        "event_time": 1355517523
    }
    ```
- **Verification:** Slack sends `X-Slack-Signature` and `X-Slack-Request-Timestamp`
  headers. Compute HMAC-SHA256 over `v0:{timestamp}:{raw_body}` with your
  Signing Secret and compare.
  https://api.slack.com/authentication/verifying-requests-from-slack
- **Challenge:** On initial setup Slack sends a `url_verification` event
  with a `challenge` field that must be echoed back.

## Slash Commands
- **Endpoint:** POST /integrations/slack/command
- **Docs:** https://api.slack.com/interactivity/slash-commands
- **Expected payload (form-encoded):**
    ```
    token=...&team_id=T0001&channel_id=C2147483705
    &user_id=U2147483697&command=/translate&text=hello world
    &response_url=https://hooks.slack.com/commands/...
    ```
- **Verification:** Same HMAC-SHA256 mechanism as webhooks.
"""

from fastapi import APIRouter, HTTPException, Request, status

router = APIRouter(prefix="/slack", tags=["integrations-slack"])


@router.post("/webhook")
async def slack_webhook(request: Request):
    """Receive Slack Events API callbacks.

    TODO:
    - Verify request signature (X-Slack-Signature + X-Slack-Request-Timestamp)
    - Handle url_verification challenge handshake
    - Route event types (message, app_mention, etc.) to handlers
    - Process message events for translation
    - Respond within 3 seconds (defer heavy work to background task)
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Slack integration not yet implemented. See /developers for API access.",
    )


@router.post("/command")
async def slack_command(request: Request):
    """Receive Slack slash command invocations.

    TODO:
    - Verify request signature
    - Parse form-encoded body (token, team_id, channel_id, user_id, command, text)
    - Implement /translate command to translate text inline
    - Return immediate response (ephemeral or in-channel)
    - Use response_url for deferred responses if needed
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Slack integration not yet implemented. See /developers for API access.",
    )
