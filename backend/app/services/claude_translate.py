from openai import OpenAI
from app.config import get_settings
from app.models.user import CommunicationStyle

# OpenRouter base URL (OpenAI-compatible)
OPENROUTER_BASE = "https://openrouter.ai/api/v1"
MODEL = "anthropic/claude-sonnet-4"

# Translation system prompts
PROMPTS = {
    (CommunicationStyle.neurotypical, CommunicationStyle.autistic): (
        "You are a helpful assistant that translates between neurotypical and autistic "
        "communication styles. Rephrase the user's message to be more direct, literal, "
        "and unambiguous for an autistic person. Only return the translated message."
    ),
    (CommunicationStyle.autistic, CommunicationStyle.neurotypical): (
        "You are a helpful assistant that translates between autistic and neurotypical "
        "communication styles. Rephrase the user's message to add social context, soften "
        "blunt statements, and explain literal meanings for a neurotypical person. "
        "Only return the translated message."
    ),
}

SAME_STYLE_PROMPT = (
    "You are a helpful communication assistant. Rephrase the user's message clearly. "
    "Only return the rephrased message."
)

# Templates for different translation contexts
TEMPLATES = {
    "casual": "This is a casual conversation between friends.",
    "professional": "This is a professional workplace conversation.",
    "emotional": "This message has emotional content that should be handled sensitively.",
    "technical": "This is a technical discussion about a specific topic.",
    "conflict": "This conversation involves a disagreement or conflict that needs de-escalation.",
}


def _get_client() -> OpenAI:
    return OpenAI(
        base_url=OPENROUTER_BASE,
        api_key=get_settings().openrouter_api_key,
    )


async def translate_text(
    text: str,
    sender_style: CommunicationStyle,
    recipient_style: CommunicationStyle,
    template: str | None = None,
    custom_prompt: str | None = None,
) -> str:
    """Translate text between communication styles via OpenRouter."""
    if not get_settings().openrouter_api_key:
        return f"[untranslated: {sender_style.value}→{recipient_style.value}] {text}"

    client = _get_client()

    system = PROMPTS.get((sender_style, recipient_style), SAME_STYLE_PROMPT)

    if custom_prompt:
        system = custom_prompt
    elif template and template in TEMPLATES:
        system = f"{system}\n\nContext: {TEMPLATES[template]}"

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": text},
        ],
    )

    return response.choices[0].message.content


async def extract_and_translate_image(
    image_bytes: bytes,
    media_type: str,
    sender_style: CommunicationStyle,
    recipient_style: CommunicationStyle,
    template: str | None = None,
) -> tuple[str, str]:
    """OCR an image using vision model, then translate the extracted text."""
    import base64

    client = _get_client()
    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    # Step 1: OCR with vision
    ocr_response = client.chat.completions.create(
        model=MODEL,
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{b64_image}",
                        },
                    },
                    {
                        "type": "text",
                        "text": "Extract all text from this image. Return only the extracted text, nothing else.",
                    },
                ],
            }
        ],
    )

    extracted_text = ocr_response.choices[0].message.content

    # Step 2: Translate
    translated_text = await translate_text(
        extracted_text, sender_style, recipient_style, template
    )

    return extracted_text, translated_text
