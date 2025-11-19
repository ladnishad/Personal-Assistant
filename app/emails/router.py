"""Email API routes."""

import time
from collections import defaultdict
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.dependencies import get_current_active_user
from app.auth.models import User
from app.emails.classifier import classify_email
from app.emails.models import Email, EmailLabel
from app.emails.schemas import (
    EmailClassifyAllResponse,
    EmailClassifyResponse,
    EmailListResponse,
    EmailResponse,
    EmailSyncResponse,
)
from app.emails.service import EmailService

router = APIRouter()


@router.post("/sync", response_model=EmailSyncResponse)
async def sync_emails(current_user: User = Depends(get_current_active_user)):
    """Sync emails from all connected integrations."""
    result = await EmailService.sync_emails(current_user.id)
    return EmailSyncResponse(**result)


@router.get("/", response_model=EmailListResponse)
async def list_emails(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    is_read: Optional[bool] = Query(None),
    is_starred: Optional[bool] = Query(None),
    labels: Optional[List[EmailLabel]] = Query(None),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
):
    """List user emails with filters."""
    skip = (page - 1) * page_size

    emails, total = await EmailService.get_user_emails(
        user_id=current_user.id,
        skip=skip,
        limit=page_size,
        is_read=is_read,
        is_starred=is_starred,
        labels=labels,
        search=search,
    )

    email_responses = [
        EmailResponse(
            id=str(e.id),
            user_id=str(e.user_id),
            message_id=e.message_id,
            from_email=e.from_email,
            from_name=e.from_name,
            to=e.to,
            cc=e.cc,
            subject=e.subject,
            snippet=e.snippet,
            body_text=e.body_text,
            has_attachments=e.has_attachments,
            attachments=e.attachments,
            labels=e.labels,
            is_read=e.is_read,
            is_starred=e.is_starred,
            received_at=e.received_at,
            extracted_entities=e.extracted_entities,
        )
        for e in emails
    ]

    return EmailListResponse(
        emails=email_responses, total=total, page=page, page_size=page_size
    )


@router.get("/{email_id}", response_model=EmailResponse)
async def get_email(
    email_id: str, current_user: User = Depends(get_current_active_user)
):
    """Get a specific email."""
    email = await Email.get(email_id)

    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Email not found"
        )

    if email.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this email",
        )

    return EmailResponse(
        id=str(email.id),
        user_id=str(email.user_id),
        message_id=email.message_id,
        from_email=email.from_email,
        from_name=email.from_name,
        to=email.to,
        cc=email.cc,
        subject=email.subject,
        snippet=email.snippet,
        body_text=email.body_text,
        has_attachments=email.has_attachments,
        attachments=email.attachments,
        labels=email.labels,
        is_read=email.is_read,
        is_starred=email.is_starred,
        received_at=email.received_at,
        extracted_entities=email.extracted_entities,
    )


@router.patch("/{email_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_email_read(
    email_id: str,
    is_read: bool = True,
    current_user: User = Depends(get_current_active_user),
):
    """Mark email as read or unread."""
    email = await Email.get(email_id)

    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Email not found"
        )

    if email.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this email",
        )

    email.is_read = is_read
    await email.save()

    return None


@router.patch("/{email_id}/star", status_code=status.HTTP_204_NO_CONTENT)
async def star_email(
    email_id: str,
    is_starred: bool = True,
    current_user: User = Depends(get_current_active_user),
):
    """Star or unstar email."""
    email = await Email.get(email_id)

    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Email not found"
        )

    if email.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this email",
        )

    email.is_starred = is_starred
    await email.save()

    return None


@router.post("/classify-all", response_model=EmailClassifyAllResponse)
async def classify_all_emails(
    force_reclassify: bool = Query(
        False, description="Force re-classification of already classified emails"
    ),
    current_user: User = Depends(get_current_active_user),
):
    """🧪 EXPERIMENTAL: Trigger LLM classification for all user emails.

    This endpoint forces classification of all emails in the database for the current user.
    Useful for:
    - Initial setup after deploying the classification system
    - Testing classification accuracy
    - Re-classifying emails after prompt improvements

    Args:
        force_reclassify: If True, re-classify emails that are already classified
        current_user: Current authenticated user

    Returns:
        Classification statistics and results
    """
    import logging

    logger = logging.getLogger(__name__)

    start_time = time.time()
    classified_count = 0
    skipped_count = 0
    error_count = 0
    category_counts = defaultdict(int)

    # Get all emails for current user
    query = {"user_id": current_user.id}

    # If not forcing reclassify, only get unclassified emails
    if not force_reclassify:
        query["classified_at"] = None

    emails = await Email.find(query).to_list()
    total_emails = len(emails)

    logger.info(
        f"🧪 Starting experimental classification for {total_emails} emails "
        f"(user: {current_user.id}, force_reclassify: {force_reclassify})"
    )

    # Classify each email
    for email in emails:
        try:
            # Skip if already classified (unless force_reclassify)
            if not force_reclassify and email.classified_at:
                skipped_count += 1
                continue

            # Classify email
            classification = await classify_email(email)

            # Save classification to database
            email.email_category = classification.category.value
            email.category_confidence = classification.confidence
            email.category_reasoning = classification.reasoning
            email.classified_at = datetime.utcnow()
            await email.save()

            # Update stats
            classified_count += 1
            category_counts[classification.category.value] += 1

            logger.debug(
                f"Classified email {email.id} as {classification.category.value} "
                f"(confidence: {classification.confidence:.2f})"
            )

        except Exception as e:
            error_count += 1
            logger.error(f"Error classifying email {email.id}: {e}", exc_info=True)
            continue

    duration = time.time() - start_time

    logger.info(
        f"🧪 Classification complete: {classified_count} classified, "
        f"{skipped_count} skipped, {error_count} errors in {duration:.2f}s"
    )

    return EmailClassifyAllResponse(
        total_emails=total_emails,
        classified_count=classified_count,
        skipped_count=skipped_count,
        error_count=error_count,
        categories=dict(category_counts),
        duration_seconds=round(duration, 2),
    )


@router.post("/{email_id}/classify", response_model=EmailClassifyResponse)
async def classify_single_email(
    email_id: str,
    force_reclassify: bool = Query(
        False, description="Force re-classification even if already classified"
    ),
    current_user: User = Depends(get_current_active_user),
):
    """🧪 EXPERIMENTAL: Classify a single email using LLM.

    This endpoint allows you to classify a specific email, useful for:
    - Testing classification on individual emails
    - Re-classifying emails after prompt improvements
    - Manual classification triggers

    Args:
        email_id: The email ID to classify
        force_reclassify: If True, re-classify even if already classified
        current_user: Current authenticated user

    Returns:
        Classification result for the email
    """
    import logging

    logger = logging.getLogger(__name__)

    # Get the email
    email = await Email.get(email_id)

    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Email not found"
        )

    # Check ownership
    if email.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to classify this email",
        )

    # Check if already classified
    if email.classified_at and not force_reclassify:
        logger.info(
            f"Email {email_id} already classified as {email.email_category}, skipping"
        )
        return EmailClassifyResponse(
            email_id=str(email.id),
            category=email.email_category or "unknown",
            confidence=email.category_confidence or 0.0,
            reasoning=email.category_reasoning or "Previously classified",
            indicators=[],
            classified_at=email.classified_at or datetime.utcnow(),
        )

    # Classify the email
    try:
        classification = await classify_email(email)

        # Save classification to database
        email.email_category = classification.category.value
        email.category_confidence = classification.confidence
        email.category_reasoning = classification.reasoning
        email.classified_at = datetime.utcnow()
        await email.save()

        logger.info(
            f"Classified email {email_id} as {classification.category.value} "
            f"(confidence: {classification.confidence:.2f})"
        )

        return EmailClassifyResponse(
            email_id=str(email.id),
            category=classification.category.value,
            confidence=classification.confidence,
            reasoning=classification.reasoning,
            indicators=classification.indicators,
            classified_at=email.classified_at,
        )

    except Exception as e:
        logger.error(f"Error classifying email {email_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to classify email: {str(e)}",
        )
