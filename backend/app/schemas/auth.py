from pydantic import BaseModel, Field


class AppleSignInRequest(BaseModel):
    identity_token: str
    authorization_code: str
    full_name: str | None = None


class SignupRequest(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=255)
    communication_style: str = "neurotypical"


class LoginRequest(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str


class GoogleSignInRequest(BaseModel):
    credential: str  # Google ID token from Sign-In button


class ForgotPasswordRequest(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
