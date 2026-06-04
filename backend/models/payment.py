from typing import Optional, Literal
from pydantic import BaseModel, EmailStr
from .base import BaseDocument


PaymentStatus = Literal["pending", "success", "failed", "abandoned"]


class Payment(BaseDocument):
    user_id: str
    course_id: str
    amount: float  # in NGN
    currency: str = "NGN"
    reference: str  # paystack reference
    status: PaymentStatus = "pending"
    email: EmailStr
    paystack_response: Optional[dict] = None


class PaymentInitRequest(BaseModel):
    course_id: str
    callback_url: str


class PaymentInitResponse(BaseModel):
    authorization_url: str
    reference: str
    access_code: Optional[str] = None


class Contact(BaseDocument):
    name: str
    email: EmailStr
    subject: Optional[str] = None
    message: str
    is_read: bool = False


class ContactCreate(BaseModel):
    name: str
    email: EmailStr
    subject: Optional[str] = None
    message: str
