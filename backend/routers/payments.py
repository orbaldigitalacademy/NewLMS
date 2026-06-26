# Payments router using Paystack.
import os
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from datetime import datetime
from auth import require_roles
from models import UserRole

from auth import get_current_user
from database import db
from models.course import Course
from models.payment import Payment, PaymentInitRequest, PaymentInitResponse, PaymentSubmitRequest, PaymentReviewRequest
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

@router.post("/submit")
async def submit_bank_payment(
    data: PaymentSubmitRequest,
    user: User = Depends(get_current_user),
):
    """
    Submit a bank transfer payment for manual review.
    """

    # Check that the course exists
    course_doc = await db.courses.find_one({"_id": data.course_id})

    if not course_doc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Course not found",
        )

    course = Course.from_mongo(course_doc)

    # Prevent duplicate enrolment
    existing_enrollment = await db.enrollments.find_one(
        {
            "user_id": user.id,
            "course_id": course.id,
        }
    )

    if existing_enrollment:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Already enrolled in this course",
        )

    # Prevent duplicate pending payment
    existing_payment = await db.payments.find_one(
        {
            "user_id": user.id,
            "course_id": course.id,
            "status": "pending",
        }
    )

    if existing_payment:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "A payment for this course is already awaiting review.",
        )

    reference = f"PAY-{uuid.uuid4().hex[:12].upper()}"
    payment = Payment(
        user_id=user.id,
        course_id=course.id,
        amount=course.price,
        email=user.email,
        payment_method="bank_transfer",
        reference=reference,
        status="pending",
    )

    await db.payments.insert_one(payment.to_mongo())

    return {
        "success": True,
        "message": (
            "Your payment proof has been submitted successfully. "
            "An administrator will review it shortly."
        ),
        "payment_id": payment.id,
    }

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

@router.get("/pending")
async def get_pending_payments(
    current_user: User = Depends(
        require_roles(UserRole.ADMIN)
    ),
):
    """
    List all pending bank transfer payments.
    """

    payments = []

    cursor = db.payments.find(
        {
            "payment_method": "bank_transfer",
            "status": "pending",
        }
    )

    async for payment in cursor:
        student = await db.users.find_one({"_id": payment["user_id"]})
        course = await db.courses.find_one({"_id": payment["course_id"]})

        payments.append(
            {
                "id": payment["_id"],
                "student_name": student.get("full_name") if student else "",
                "student_email": student.get("email") if student else "",
                "course_title": course.get("title") if course else "",
                "amount": payment["amount"],
                "payment_proof_url": payment.get("payment_proof_url"),
                "submitted_at": payment.get("created_at"),
            }
        )

    return payments

@router.put("/{payment_id}/approve")
async def approve_payment(
    payment_id: str,
    review: PaymentReviewRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    payment_doc = await db.payments.find_one({"_id": payment_id})

    if not payment_doc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Payment not found",
        )

    payment = Payment.from_mongo(payment_doc)

    if payment.status != "pending":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Payment has already been processed.",
        )

    user_doc = await db.users.find_one({"_id": payment.user_id})
    course_doc = await db.courses.find_one({"_id": payment.course_id})

    if not user_doc or not course_doc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "User or course not found.",
        )

    await db.payments.update_one(
        {"_id": payment.id},
        {
            "$set": {
                "status": "success",
                "reviewed_by": current_user.id,
                "reviewed_at": datetime.now().isoformat(),
                "remarks": review.remarks,
            }
        },
    )

    await _create_enrollment(
        User.from_mongo(user_doc),
        Course.from_mongo(course_doc),
    )

    return {
        "success": True,
        "message": "Payment approved successfully.",
    }

@router.put("/{payment_id}/reject")
async def reject_payment(
    payment_id: str,
    review: PaymentReviewRequest,
    current_user: User = Depends(
        require_roles(UserRole.ADMIN)
    ),
):
    payment_doc = await db.payments.find_one(
        {"_id": payment_id}
    )

    # Payment not found
    if not payment_doc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Payment not found",
        )

    # Convert Mongo document to Payment model
    payment = Payment.from_mongo(payment_doc)

    # Prevent rejecting an already processed payment
    if payment.status != "pending":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Payment has already been processed.",
        )

    # Update payment
    await db.payments.update_one(
        {"_id": payment.id},
        {
            "$set": {
                "status": "rejected",
                "reviewed_by": current_user.id,
                "reviewed_at": datetime.now().isoformat(),
                "remarks": review.remarks,
            }
        },
    )

    return {
        "success": True,
        "message": "Payment rejected.",
    }
@router.get("/me")
async def my_payments(
    current_user: User = Depends(get_current_user),
):
    payments = []

    cursor = db.payments.find(
        {
            "user_id": current_user.id
        }
    )

    async for payment in cursor:
        course = await db.courses.find_one(
            {"_id": payment["course_id"]}
        )

        payments.append(
            {
                "id": payment["_id"],
                "course_title": (
                    course["title"] if course else ""
                ),
                "amount": payment["amount"],
                "status": payment["status"],
                "payment_method": payment.get(
                    "payment_method"
                ),
                "submitted_at": payment.get(
                    "created_at"
                ),
                "remarks": payment.get(
                    "remarks"
                ),
            }
        )

    return payments

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

