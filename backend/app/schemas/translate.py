import enum
from pydantic import BaseModel


class TranslationDirection(str, enum.Enum):
    autistic_to_neurotypical = "autistic_to_neurotypical"
    neurotypical_to_autistic = "neurotypical_to_autistic"


class TranslateTextRequest(BaseModel):
    text: str
    direction: TranslationDirection
    template: str | None = None
    custom_prompt: str | None = None


class TranslateTextResponse(BaseModel):
    original_text: str
    translated_text: str
    direction: TranslationDirection
    credits_remaining: int


class TranslateImageResponse(BaseModel):
    extracted_text: str
    translated_text: str
    direction: TranslationDirection
    credits_remaining: int
