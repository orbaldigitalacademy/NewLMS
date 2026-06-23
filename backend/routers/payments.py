# Payments router using Paystack.
import os
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status

from auth import get_current_user
from database import db
from models.course import Course
from models.payment import Payment, PaymentInitRequest, PaymentInitResponse
from models.user import User
from services.payment_service import (
    initialize_transaction,
    is_configured,
    verify_transaction,
    verify_webhook_signature,
)
from routers.enrollments import _create_enrollment

router = APIRouter(prefix="/payments", tags=["payments"])
logger = logging.getLogger(__name__)


@router.get("/config")
async def payment_config():
    return {
        "provider": "paystack",
        "configured": is_configured(),
        "public_key": os.environ.get("PAYSTACK_PUBLIC_KEY", ""),
    }


@router.post("/initialize", response_model=PaymentInitResponse)
async def initialize_payment(
    data: PaymentInitRequest, user: User = Depends(get_current_user)
):
    course_doc = await db.courses.find_one({"_id": data.course_id})
    if not course_doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")
    course = Course.from_mongo(course_doc)
    if course.price <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Course is free")

    existing = await db.enrollments.find_one(
        {"user_id": user.id, "course_id": course.id}
    )
    if existing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Already enrolled")

    if not is_configured():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Payments not configured. Set PAYSTACK_SECRET_KEY in backend env.",
        )

    reference = f"lms_{uuid.uuid4().hex[:16]}"
    payment = Payment(
        user_id=user.id,
        course_id=course.id,
        amount=course.price,
        reference=reference,
        email=user.email,
        status="pending",
    )
    await db.payments.insert_one(payment.to_mongo())

    paystack_res = await initialize_transaction(
        email=user.email,
        amount_naira=course.price,
        reference=reference,
        callback_url=data.callback_url,
        metadata={"course_id": course.id, "user_id": user.id},
    )
    if not paystack_res.get("status"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            paystack_res.get("message", "Failed to initialize transaction"),
        )
    paystack_data = paystack_res["data"]
    return PaymentInitResponse(
        authorization_url=paystack_data["authorization_url"],
        reference=paystack_data["reference"],
        access_code=paystack_data.get("access_code"),
    )


async def _finalize_payment(reference: str) -> dict:
    """Verify with Paystack and create enrollment if success."""
    payment_doc = await db.payments.find_one({"reference": reference})
    if not payment_doc:
        return {"status": "failed", "message": "Unknown reference"}
    payment = Payment.from_mongo(payment_doc)

    if payment.status == "success":
        return {"status": "success", "already": True, "course_id": payment.course_id}

    result = await verify_transaction(reference)
    if result.get("status") and result["data"].get("status") == "success":
        await db.payments.update_one(
            {"_id": payment.id},
            {
                "$set": {
                    "status": "success",
                    "paystack_response": result["data"],
                }
            },
        )
        # Enroll the user
        course_doc = await db.courses.find_one({"_id": payment.course_id})
        user_doc = await db.users.find_one({"_id": payment.user_id})
        if course_doc and user_doc:
            from models.course import Course as CourseModel
            from models.user import User as UserModel
            await _create_enrollment(
                UserModel.from_mongo(user_doc), CourseModel.from_mongo(course_doc)
            )
        return {"status": "success", "course_id": payment.course_id}
    else:
        await db.payments.update_one(
            {"_id": payment.id},
            {"$set": {"status": "failed", "paystack_response": result.get("data")}},
        )
        return {"status": "failed", "message": result.get("message")}


@router.get("/verify/{reference}")
async def verify_payment(reference: str, user: User = Depends(get_current_user)):
    return await _finalize_payment(reference)


@router.post("/webhook")
async def paystack_webhook(request: Request):
    signature = request.headers.get("x-paystack-signature", "")
    body = await request.body()
    if not verify_webhook_signature(body, signature):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid signature")
    event = await request.json()
    if event.get("event") == "charge.success":
        reference = event["data"]["reference"]
        await _finalize_payment(reference)
    return {"status": "ok"}
@router.post("/submit")
async def submit_bank_payment(
    course_id: str,
    payment_proof_url: str,
    current_user: User = Depends(get_current_user),
):
    course = await db.courses.find_one({"_id": course_id})

    if not course:
        raise HTTPException(404, "Course not found")

    payment = Payment(
        user_id=current_user.id,
        course_id=course_id,
        amount=course["price"],
        payment_method="bank_transfer",
        payment_proof=payment_proof_url,
        status="pending",
    )

    await db.payments.insert_one(payment.to_mongo())

    return {
        "success": True,
        "message": "Payment submitted for verification."
    }
