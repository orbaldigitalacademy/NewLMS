"""Settings-related models (bank accounts, payment links, admin email)."""
import uuid
from typing import List

from pydantic import BaseModel, EmailStr, Field, HttpUrl


class BankAccount(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bank_name: str
    account_number: str
    account_name: str
    is_default: bool = False
    currency: str = ""
    ifsc_swift: str = ""
    branch: str = ""


class BankAccountInput(BaseModel):
    bank_name: str = Field(min_length=1)
    account_number: str = Field(min_length=1)
    account_name: str = Field(min_length=1)
    is_default: bool = False
    currency: str = ""
    ifsc_swift: str = ""
    branch: str = ""


class BankReorderInput(BaseModel):
    ordered_ids: List[str]


class PaymentLink(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str
    url: str
    is_test: bool = False


class PaymentLinkInput(BaseModel):
    label: str = Field(min_length=1)
    url: HttpUrl
    is_test: bool = False


class AdminEmailInput(BaseModel):
    admin_email: EmailStr


class SettingsResponse(BaseModel):
    banks: List[BankAccount] = []
    payment_links: List[PaymentLink] = []
    admin_email: str = ""
