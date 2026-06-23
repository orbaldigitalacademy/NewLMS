from typing import Optional, Literal
from pydantic import BaseModel, EmailStr
from .base import BaseDocument


PaymentStatus = Literal["pending", "success", "failed", "abandoned", "rejected",]

PaymentMethod = Literal["paystack","bank_transfer",]

class Payment(BaseDocument):
    user_id: str
    course_id: str
    amount: float
    currency: str = "NGN"
    email: EmailStr
    payment_method: PaymentMethod = "paystack"
    # Paystack reference
    reference: Optional[str] = None
    # Cloudinary URL of uploaded receipt (bank transfer only)
    payment_proof_url: Optional[str] = None
    status: PaymentStatus = "pending"
    paystack_response: Optional[dict] = None
    # Manual review information
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    remarks: Optional[str] = None

class PaymentInitRequest(BaseModel):
    course_id: str
    callback_url: str

class PaymentInitResponse(BaseModel):
    authorization_url: str
    reference: str
    access_code: Optional[str] = None

class PaymentSubmitRequest(BaseModel):
    course_id: str
    payment_proof_url: str

class PaymentReviewRequest(BaseModel):
    remarks: Optional[str] = None
    
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
