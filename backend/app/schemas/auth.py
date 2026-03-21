from pydantic import BaseModel


class AppleSignInRequest(BaseModel):
    identity_token: str
    authorization_code: str
    full_name: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
