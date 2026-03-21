from pydantic import BaseModel


class CreditBalanceRead(BaseModel):
    balance: int


class VerifyPurchaseRequest(BaseModel):
    jws_transaction: str
    product_id: str


class ReferralCodeRead(BaseModel):
    code: str


class RedeemReferralRequest(BaseModel):
    referral_code: str
