"""Email database models."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from beanie import Document, Indexed
from beanie import PydanticObjectId
from pydantic import Field
from pymongo import IndexModel


class EmailLabel(str, Enum):
    """Email label enumeration."""

    INBOX = "inbox"
    SENT = "sent"
    DRAFT = "draft"
    SPAM = "spam"
    TRASH = "trash"
    IMPORTANT = "important"


class EmailAttachment(Document):
    """Email attachment subdocument."""

    filename: str
    mime_type: str
    size: int  # bytes
    attachment_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "filename": "document.pdf",
                "mime_type": "application/pdf",
                "size": 1024000,
                "attachment_id": "att_123",
            }
        }


class Email(Document):
    """Email document model."""

    user_id: Indexed(PydanticObjectId)
    integration_id: Indexed(PydanticObjectId)

    # Email identifiers
    message_id: str  # Unique index defined in Settings.indexes
    thread_id: Optional[str] = None

    # Email metadata
    from_email: str
    from_name: Optional[str] = None
    to: List[str] = Field(default_factory=list)
    cc: List[str] = Field(default_factory=list)
    bcc: List[str] = Field(default_factory=list)
    subject: Optional[str] = None

    # Content
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    snippet: Optional[str] = None

    # Attachments
    has_attachments: bool = Field(default=False)
    attachments: List[dict] = Field(default_factory=list)

    # Metadata
    labels: List[EmailLabel] = Field(default_factory=list)
    is_read: bool = Field(default=False)
    is_starred: bool = Field(default=False)
    received_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Email classification (LLM-based)
    email_category: Optional[str] = None  # EmailCategory value
    category_confidence: Optional[float] = None
    category_reasoning: Optional[str] = None
    classified_at: Optional[datetime] = None

    # Entity extraction results (structured)
    extracted_entities: Optional[Dict] = None  # EmailEntity as dict
    entities_extracted_at: Optional[datetime] = None

    # Email relationships
    related_email_ids: List[PydanticObjectId] = Field(default_factory=list)
    # TODO: Reserved for future use - will store relationship type for each related email
    # Format: {email_id: "same_order", email_id: "same_tracking", ...}
    # Currently relationship types are stored in EmailRelationship collection
    relationship_types: Dict[str, str] = Field(
        default_factory=dict
    )  # {email_id: "same_order", ...}

    # Embeddings for semantic search
    embedding: Optional[List[float]] = None
    embedded_at: Optional[datetime] = None

    class Settings:
        name = "emails"
        indexes = [
            [("user_id", 1), ("received_at", -1)],
            [("user_id", 1), ("is_read", 1)],
            [("email_category", 1), ("received_at", -1)],  # Query by category
            [("classified_at", 1)],  # Find unclassified emails
            IndexModel([("message_id", 1)], name="email_message_id_unique_idx", unique=True),
        ]

    class Config:
        json_schema_extra = {
            "example": {
                "from_email": "sender@example.com",
                "from_name": "John Doe",
                "to": ["recipient@example.com"],
                "subject": "Meeting Tomorrow",
                "snippet": "Let's meet tomorrow at 3 PM...",
                "received_at": "2024-01-01T12:00:00",
                "is_read": False,
            }
        }
