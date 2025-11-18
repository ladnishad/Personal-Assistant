"""Email API routes."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.dependencies import get_current_active_user
from app.auth.models import User
from app.emails.models import Email, EmailLabel
from app.emails.schemas import EmailListResponse, EmailResponse, EmailSyncResponse
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
