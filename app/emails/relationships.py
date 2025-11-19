"""Email relationship detection and management."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

from beanie import Document, Indexed
from beanie import PydanticObjectId
from pydantic import Field
from pymongo import IndexModel

from app.emails.entity_extractor import EmailEntity, EmailEntityExtractor
from app.emails.models import Email


class RelationshipType(str, Enum):
    """Types of relationships between emails."""

    SAME_THREAD = "same_thread"
    SAME_ORDER = "same_order"
    SAME_TRACKING = "same_tracking"
    SAME_MERCHANT = "same_merchant"
    TEMPORAL_PROXIMITY = "temporal_proximity"  # Within timeframe, similar topic
    SEMANTIC_SIMILARITY = "semantic_similarity"  # Similar content


class EmailRelationship(Document):
    """Represents a relationship between two emails."""

    user_id: Indexed(PydanticObjectId)

    # The two related emails
    email_1_id: Indexed(PydanticObjectId)
    email_2_id: Indexed(PydanticObjectId)

    # Relationship metadata
    relationship_type: RelationshipType
    confidence: float = Field(
        ge=0.0, le=1.0
    )  # How confident we are in this relationship

    # What connects them
    shared_entities: Dict[str, List[str]] = Field(
        default_factory=dict
    )  # {"tracking_numbers": [...], "order_numbers": [...]}

    # Timestamps
    detected_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "email_relationships"
        indexes = [
            [("user_id", 1), ("email_1_id", 1)],
            [("user_id", 1), ("email_2_id", 1)],
            [("relationship_type", 1)],
            IndexModel(
                [("email_1_id", 1), ("email_2_id", 1)],
                name="email_relationship_unique_idx",
                unique=True,
            ),
        ]

    class Config:
        json_schema_extra = {
            "example": {
                "relationship_type": "same_tracking",
                "confidence": 0.95,
                "shared_entities": {"tracking_numbers": ["1ZB9033F6762347268"]},
            }
        }


class EmailRelationshipDetector:
    """Detect relationships between emails."""

    @staticmethod
    async def find_related_emails(
        email: Email, user_id: PydanticObjectId, lookback_days: int = 30
    ) -> List[EmailRelationship]:
        """Find all emails related to the given email.

        Args:
            email: Target email to find relationships for
            user_id: User ID to scope search
            lookback_days: How many days back to search

        Returns:
            List of EmailRelationship objects
        """
        relationships = []

        # Extract entities from target email if not already done
        if not email.extracted_entities:
            entities = EmailEntityExtractor.extract_entities(email)
            # Convert to dict for storage
            email.extracted_entities = entities.model_dump()
            email.entities_extracted_at = datetime.utcnow()
            await email.save()

        # Load entities as EmailEntity object
        target_entities = EmailEntity(**email.extracted_entities)

        # Get candidate emails (within time window)
        cutoff_date = email.received_at - timedelta(days=lookback_days)
        candidate_emails = await Email.find(
            Email.user_id == user_id,
            Email.received_at >= cutoff_date,
            Email.id != email.id,
        ).to_list()

        for candidate in candidate_emails:
            # Extract entities if not already done
            if not candidate.extracted_entities:
                c_entities = EmailEntityExtractor.extract_entities(candidate)
                candidate.extracted_entities = c_entities.model_dump()
                candidate.entities_extracted_at = datetime.utcnow()
                await candidate.save()

            # Load candidate entities
            candidate_entities = EmailEntity(**candidate.extracted_entities)

            # Check for relationships
            relationship = EmailRelationshipDetector._detect_relationship(
                email, target_entities, candidate, candidate_entities
            )

            if relationship:
                relationships.append(relationship)

        return relationships

    @staticmethod
    def _detect_relationship(
        email1: Email,
        entities1: EmailEntity,
        email2: Email,
        entities2: EmailEntity,
    ) -> Optional[EmailRelationship]:
        """Detect if two emails are related.

        Args:
            email1: First email
            entities1: Extracted entities from email1
            email2: Second email
            entities2: Extracted entities from email2

        Returns:
            EmailRelationship if related, None otherwise
        """
        shared_entities = {}
        relationship_types = []
        confidence = 0.0

        # 1. Same thread (100% confident)
        if email1.thread_id and email1.thread_id == email2.thread_id:
            relationship_types.append(RelationshipType.SAME_THREAD)
            confidence = max(confidence, 1.0)

        # 2. Same tracking number (95% confident)
        shared_tracking = set(entities1.tracking_numbers) & set(
            entities2.tracking_numbers
        )
        if shared_tracking:
            relationship_types.append(RelationshipType.SAME_TRACKING)
            shared_entities["tracking_numbers"] = list(shared_tracking)
            confidence = max(confidence, 0.95)

        # 3. Same order number (90% confident)
        shared_orders = set(entities1.order_numbers) & set(entities2.order_numbers)
        if shared_orders:
            relationship_types.append(RelationshipType.SAME_ORDER)
            shared_entities["order_numbers"] = list(shared_orders)
            confidence = max(confidence, 0.90)

        # 4. Same merchant (60% confident if within 7 days)
        if (
            entities1.merchant_domain
            and entities1.merchant_domain == entities2.merchant_domain
        ):
            days_apart = abs((email1.received_at - email2.received_at).days)
            if days_apart <= 7:
                relationship_types.append(RelationshipType.SAME_MERCHANT)
                shared_entities["merchant"] = [entities1.merchant_domain]
                confidence = max(confidence, 0.60)

        # 5. Temporal proximity + semantic similarity
        days_apart = abs((email1.received_at - email2.received_at).days)
        if days_apart <= 3:
            # Check if both mention similar products
            shared_products = set(entities1.product_names) & set(
                entities2.product_names
            )
            if shared_products:
                relationship_types.append(RelationshipType.TEMPORAL_PROXIMITY)
                shared_entities["products"] = list(shared_products)
                confidence = max(confidence, 0.50)

        # Only create relationship if confidence >= 0.5
        if confidence >= 0.5 and relationship_types:
            return EmailRelationship(
                user_id=email1.user_id,
                email_1_id=email1.id,
                email_2_id=email2.id,
                relationship_type=relationship_types[0],  # Primary type
                confidence=confidence,
                shared_entities=shared_entities,
            )

        return None

    @staticmethod
    async def get_email_cluster(
        email_id: PydanticObjectId, user_id: PydanticObjectId
    ) -> List[Email]:
        """Get all emails in a relationship cluster.

        Performs a graph traversal to find all connected emails.

        Args:
            email_id: Starting email ID
            user_id: User ID

        Returns:
            List of related emails including the starting email
        """
        visited = set()
        to_visit = {email_id}
        cluster = []

        while to_visit:
            current_id = to_visit.pop()

            if current_id in visited:
                continue

            visited.add(current_id)

            # Get email
            email = await Email.get(current_id)
            if email and email.user_id == user_id:
                cluster.append(email)

                # Find relationships
                relationships = await EmailRelationship.find(
                    EmailRelationship.user_id == user_id,
                    {
                        "$or": [
                            {"email_1_id": current_id},
                            {"email_2_id": current_id},
                        ]
                    },
                ).to_list()

                # Add related emails to visit queue
                for rel in relationships:
                    other_id = (
                        rel.email_2_id
                        if rel.email_1_id == current_id
                        else rel.email_1_id
                    )
                    if other_id not in visited:
                        to_visit.add(other_id)

        return cluster
