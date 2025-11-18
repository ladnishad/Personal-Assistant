"""Package tracking Pydantic schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.packages.models import CourierService, PackageStatus, TrackingEvent


class PackageBase(BaseModel):
    """Base package schema."""

    tracking_number: str = Field(..., description="Package tracking number")
    courier_service: CourierService = Field(..., description="Courier service")
    product_name: Optional[str] = Field(None, description="Product name")
    product_description: Optional[str] = Field(None, description="Product description")
    merchant: Optional[str] = Field(None, description="Merchant/seller")
    order_number: Optional[str] = Field(None, description="Order number")


class PackageCreate(PackageBase):
    """Schema for creating a new package."""

    email_id: Optional[str] = Field(None, description="Source email ID")
    status: PackageStatus = Field(
        default=PackageStatus.ORDERED, description="Initial package status"
    )
    estimated_delivery: Optional[datetime] = Field(
        None, description="Estimated delivery date"
    )
    detection_confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Detection confidence score"
    )
    detection_source: str = Field(
        default="email", description="How package was detected"
    )


class PackageUpdate(BaseModel):
    """Schema for updating a package."""

    status: Optional[PackageStatus] = None
    product_name: Optional[str] = None
    product_description: Optional[str] = None
    merchant: Optional[str] = None
    current_location: Optional[str] = None
    origin_location: Optional[str] = None
    destination_location: Optional[str] = None
    estimated_delivery: Optional[datetime] = None
    actual_delivery: Optional[datetime] = None
    recipient_name: Optional[str] = None
    delivery_instructions: Optional[str] = None
    is_active: Optional[bool] = None
    user_notified_delivered: Optional[bool] = None
    user_notified_exception: Optional[bool] = None


class TrackingEventResponse(BaseModel):
    """Schema for tracking event response."""

    timestamp: datetime
    status: str
    location: Optional[str] = None
    description: str
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None

    class Config:
        from_attributes = True


class PackageResponse(BaseModel):
    """Schema for package response."""

    id: str
    user_id: str
    tracking_number: str
    courier_service: CourierService
    status: PackageStatus
    product_name: Optional[str] = None
    product_description: Optional[str] = None
    merchant: Optional[str] = None
    order_number: Optional[str] = None
    current_location: Optional[str] = None
    estimated_delivery: Optional[datetime] = None
    actual_delivery: Optional[datetime] = None
    events: List[TrackingEventResponse] = []
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PackageListResponse(BaseModel):
    """Schema for package list response."""

    packages: List[PackageResponse]
    total: int
    skip: int
    limit: int


class TrackingDetectionResult(BaseModel):
    """Schema for tracking detection result from email."""

    is_tracking_email: bool
    confidence: float = Field(ge=0.0, le=1.0)
    tracking_number: Optional[str] = None
    courier_service: Optional[CourierService] = None
    product_name: Optional[str] = None
    merchant: Optional[str] = None
    order_number: Optional[str] = None
    estimated_delivery: Optional[datetime] = None


class CourierTrackingResponse(BaseModel):
    """Schema for courier API tracking response."""

    tracking_number: str
    courier_service: CourierService
    status: PackageStatus
    current_location: Optional[str] = None
    estimated_delivery: Optional[datetime] = None
    actual_delivery: Optional[datetime] = None
    events: List[TrackingEvent] = []
    raw_data: Optional[dict] = None  # Raw API response for debugging
