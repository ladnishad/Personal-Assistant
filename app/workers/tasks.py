"""Background job tasks."""

import logging
from datetime import datetime, timedelta

from app.emails.classifier import EmailCategory, classify_email
from app.emails.entity_extractor import EmailEntityExtractor
from app.emails.models import Email
from app.emails.relationships import EmailRelationship, EmailRelationshipDetector
from app.emails.service import EmailService
from app.integrations.google_service import GoogleService
from app.integrations.microsoft_service import MicrosoftService
from app.integrations.models import Integration, IntegrationType
from app.packages.courier_detector import CourierDetector
from app.packages.models import CourierService, Package
from app.packages.schemas import PackageCreate
from app.packages.service import PackageService
from app.packages.thread_aware_builder import ThreadAwarePackageBuilder
from app.tasks.models import Task

logger = logging.getLogger(__name__)


async def sync_emails_job():
    """Background job to sync emails for all users."""
    logger.info("Starting email sync job")

    try:
        # Get all active integrations
        integrations = await Integration.find(Integration.is_active == True).to_list()

        synced_count = 0
        for integration in integrations:
            try:
                # Sync emails for this integration's user
                result = await EmailService.sync_emails(integration.user_id)
                synced_count += result["synced_count"]
                logger.debug(
                    f"Synced {result['synced_count']} emails for user {integration.user_id}"
                )
            except Exception as e:
                logger.error(
                    f"Error syncing emails for integration {integration.id}: {e}"
                )
                continue

        logger.info(f"Email sync job completed. Total synced: {synced_count}")

    except Exception as e:
        logger.error(f"Error in email sync job: {e}")


async def sync_calendar_job():
    """Background job to sync calendar events for all users."""
    logger.info("Starting calendar sync job")

    try:
        # Placeholder for calendar sync implementation
        # Similar to email sync
        logger.info("Calendar sync job completed")

    except Exception as e:
        logger.error(f"Error in calendar sync job: {e}")


async def check_reminders_job():
    """Background job to check and send reminders."""
    logger.info("Starting reminder check job")

    try:
        # Find tasks with reminders that are due
        now = datetime.utcnow()
        tasks_with_reminders = await Task.find(
            Task.reminder_at <= now,
            Task.reminder_sent == False,
            Task.status != "done",
        ).to_list()

        logger.info(f"Found {len(tasks_with_reminders)} reminders to send")

        for task in tasks_with_reminders:
            try:
                # TODO: Implement actual reminder sending (email, push notification, etc.)
                logger.info(f"Would send reminder for task: {task.title}")

                # Mark reminder as sent
                task.reminder_sent = True
                await task.save()

            except Exception as e:
                logger.error(f"Error sending reminder for task {task.id}: {e}")
                continue

        logger.info("Reminder check job completed")

    except Exception as e:
        logger.error(f"Error in reminder check job: {e}")


async def refresh_tokens_job():
    """Background job to refresh OAuth tokens."""
    logger.info("Starting token refresh job")

    try:
        # Find integrations with tokens expiring in next 24 hours
        expiry_threshold = datetime.utcnow() + timedelta(hours=24)

        integrations = await Integration.find(
            Integration.is_active == True,
            Integration.token_expiry <= expiry_threshold,
        ).to_list()

        logger.info(f"Found {len(integrations)} tokens to refresh")

        refreshed_count = 0
        for integration in integrations:
            try:
                if integration.integration_type == IntegrationType.GOOGLE:
                    await GoogleService.refresh_access_token(integration)
                    refreshed_count += 1
                elif integration.integration_type == IntegrationType.MICROSOFT:
                    await MicrosoftService.refresh_access_token(integration)
                    refreshed_count += 1

                logger.debug(f"Refreshed token for integration {integration.id}")

            except Exception as e:
                logger.error(
                    f"Error refreshing token for integration {integration.id}: {e}"
                )
                # Mark integration as inactive if refresh fails
                integration.is_active = False
                await integration.save()
                continue

        logger.info(f"Token refresh job completed. Refreshed: {refreshed_count}")

    except Exception as e:
        logger.error(f"Error in token refresh job: {e}")


async def process_package_emails_job():
    """Background job to scan emails for package tracking information."""
    logger.info("Starting package email processing job")

    try:
        # Get all active integrations
        integrations = await Integration.find(Integration.is_active == True).to_list()

        packages_created = 0
        emails_processed = 0

        for integration in integrations:
            try:
                user_id = integration.user_id

                # Get recent emails (last sync window)
                # Query emails created in last 30 minutes (typical sync interval)
                cutoff_time = datetime.utcnow() - timedelta(minutes=30)

                recent_emails = await Email.find(
                    Email.user_id == user_id,
                    Email.created_at >= cutoff_time,
                ).to_list()

                logger.debug(
                    f"Processing {len(recent_emails)} recent emails for user {user_id}"
                )

                for email in recent_emails:
                    try:
                        emails_processed += 1

                        # Analyze email for tracking info
                        body = email.body_text or email.body_html or email.snippet or ""
                        analysis = CourierDetector.analyze_email(
                            from_email=email.from_email,
                            subject=email.subject or "",
                            body=body,
                        )

                        # Only create package if confidence is high enough
                        if analysis["is_tracking_email"] and analysis["confidence"] >= 0.7:
                            # Check if we have tracking numbers
                            if analysis["tracking_numbers"]:
                                for tracking_num, courier in analysis["tracking_numbers"]:
                                    # Check if package already exists
                                    existing = await PackageService.get_package_by_tracking(
                                        tracking_num, courier
                                    )

                                    if not existing:
                                        # Extract product name from subject
                                        product_name = None
                                        if email.subject and "order" in email.subject.lower():
                                            words = email.subject.split()
                                            if len(words) > 3:
                                                product_name = " ".join(words[:5])

                                        # Create package
                                        package_data = PackageCreate(
                                            tracking_number=tracking_num,
                                            courier_service=courier,
                                            email_id=str(email.id),
                                            product_name=product_name,
                                            merchant=analysis.get("merchant"),
                                            order_number=analysis.get("order_number"),
                                            detection_source="email_background_job",
                                            detection_confidence=analysis["confidence"],
                                        )

                                        try:
                                            package = await PackageService.create_package(
                                                user_id, package_data
                                            )
                                            packages_created += 1
                                            logger.info(
                                                f"Created package {package.id} from email {email.id}: {tracking_num}"
                                            )
                                        except ValueError as e:
                                            # Package already exists - skip
                                            logger.debug(f"Package already exists: {e}")
                                            continue

                    except Exception as e:
                        logger.error(f"Error processing email {email.id}: {e}")
                        continue

            except Exception as e:
                logger.error(
                    f"Error processing packages for integration {integration.id}: {e}"
                )
                continue

        logger.info(
            f"Package email processing completed. Processed: {emails_processed}, Created: {packages_created}"
        )

    except Exception as e:
        logger.error(f"Error in package email processing job: {e}")


async def update_package_status_job():
    """Background job to update package status from courier APIs via AfterShip."""
    logger.info("Starting package status update job")

    try:
        from app.config import settings
        from app.packages.courier_apis.aftership_client import AfterShipClient

        # Check if AfterShip API key is configured
        if not settings.aftership_api_key:
            logger.warning(
                "AfterShip API key not configured - skipping package status updates"
            )
            return

        # Get packages that need status update
        packages = await PackageService.get_packages_needing_update()

        logger.info(f"Found {len(packages)} packages needing status update")

        # Create single AfterShip client for all couriers
        client = AfterShipClient(api_key=settings.aftership_api_key)

        updated_count = 0

        for package in packages:
            try:
                # Track package via AfterShip (auto-detects courier)
                tracking_response = await client.track_package(package.tracking_number)

                # Update package in database
                await PackageService.update_package_status(
                    tracking_number=package.tracking_number,
                    courier_service=package.courier_service,
                    status=tracking_response.status,
                    events=tracking_response.events,
                    current_location=tracking_response.current_location,
                    estimated_delivery=tracking_response.estimated_delivery,
                )

                updated_count += 1
                logger.debug(
                    f"Updated package {package.id}: {tracking_response.status.value}"
                )

            except Exception as e:
                logger.error(
                    f"Error updating package {package.id} ({package.tracking_number}): {e}"
                )
                continue

        logger.info(f"Package status update completed. Updated: {updated_count}")

    except Exception as e:
        logger.error(f"Error in package status update job: {e}")


async def process_email_relationships_job():
    """Background job to analyze emails and build relationship graph.

    This job:
    0. Classifies emails using LLM (NEW)
    1. Extracts entities from relevant emails (tracking numbers, order numbers, etc.)
    2. Detects relationships between emails
    3. Builds email relationship graph for thread-aware package creation
    """
    logger.info("Starting email relationship processing job")

    try:
        # Get unclassified emails (within last 24 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        emails = await Email.find(
            Email.classified_at == None, Email.created_at >= cutoff_time
        ).to_list()

        logger.info(f"Found {len(emails)} emails to classify and process")

        emails_classified = 0
        emails_skipped = 0
        entities_extracted = 0
        relationships_created = 0

        for email in emails:
            try:
                # STEP 1: Classify email with LLM (ALWAYS)
                logger.debug(f"Classifying email {email.id}: {email.subject[:50]}...")

                classification = await classify_email(email)

                # Save classification
                email.email_category = classification.category.value
                email.category_confidence = classification.confidence
                email.category_reasoning = classification.reasoning
                email.classified_at = datetime.utcnow()
                await email.save()
                emails_classified += 1

                logger.info(
                    f"Classified as {classification.category.value} "
                    f"(confidence: {classification.confidence:.2f})"
                )

                # STEP 2: Conditional deep processing based on category
                if not classification.should_process:
                    logger.debug(
                        f"Skipping entity extraction for {classification.category.value} email"
                    )
                    emails_skipped += 1
                    continue

                # STEP 3: Extract entities (only for relevant categories)
                email.extracted_entities = EmailEntityExtractor.extract_entities(
                    email
                ).model_dump()
                email.entities_extracted_at = datetime.utcnow()
                await email.save()
                entities_extracted += 1

                logger.debug(f"Extracted entities from email {email.id}")

                # STEP 4: Find related emails (only for categories that need relationships)
                relationships = []
                if classification.category in [
                    EmailCategory.PACKAGE_SHIPPING,
                    EmailCategory.ECOMMERCE_ORDER,
                    EmailCategory.TRAVEL,
                ]:
                    relationships = await EmailRelationshipDetector.find_related_emails(
                        email, email.user_id, lookback_days=30
                    )

                    # 5. Save relationships
                    for rel in relationships:
                        # Check if relationship already exists (both directions to avoid duplicates)
                        existing = await EmailRelationship.find_one(
                            {
                                "$or": [
                                    {
                                        "email_1_id": rel.email_1_id,
                                        "email_2_id": rel.email_2_id,
                                    },
                                    {
                                        "email_1_id": rel.email_2_id,
                                        "email_2_id": rel.email_1_id,
                                    },
                                ]
                            }
                        )
                        if not existing:
                            await rel.insert()
                            relationships_created += 1

                            logger.debug(
                                f"Created relationship: {rel.relationship_type.value} (confidence: {rel.confidence})"
                            )

                    # 6. Update email's related_email_ids (if any relationships found)
                    if relationships:
                        # Handle both directions: current email can be email_1 or email_2
                        email.related_email_ids = [
                            rel.email_2_id if rel.email_1_id == email.id else rel.email_1_id
                            for rel in relationships
                        ]
                        await email.save()

            except Exception as e:
                logger.error(f"Error processing email {email.id}: {e}", exc_info=True)
                continue

        logger.info(
            f"Email processing completed. "
            f"Classified: {emails_classified}, Skipped: {emails_skipped}, "
            f"Entities extracted: {entities_extracted}, Relationships: {relationships_created}"
        )

    except Exception as e:
        logger.error(f"Error in email relationship processing job: {e}", exc_info=True)


async def build_packages_from_threads_job():
    """Background job to build packages from email threads.

    This job:
    1. Finds emails with tracking numbers that don't have packages yet
    2. Gets all related emails (thread members)
    3. Builds comprehensive packages from email clusters
    """
    logger.info("Starting thread-aware package building job")

    try:
        # Get emails with tracking numbers (limit to last 30 days for performance)
        cutoff_time = datetime.utcnow() - timedelta(days=30)
        all_emails = await Email.find(
            Email.entities_extracted_at != None, Email.received_at >= cutoff_time
        ).to_list()

        logger.info(f"Processing {len(all_emails)} emails from last 30 days")

        packages_created = 0
        packages_enriched = 0

        processed_tracking_numbers = set()

        for email in all_emails:
            try:
                if not email.extracted_entities:
                    continue

                # Check if email has tracking numbers
                tracking_numbers = email.extracted_entities.get("tracking_numbers", [])

                if not tracking_numbers:
                    continue

                # Process each tracking number
                for tracking_number in tracking_numbers:
                    # Skip if already processed in this run
                    if tracking_number in processed_tracking_numbers:
                        continue

                    processed_tracking_numbers.add(tracking_number)

                    # Check if package already exists
                    existing_package = await Package.find_one(
                        Package.tracking_number == tracking_number
                    )

                    # Get email cluster (all related emails)
                    email_cluster = await EmailRelationshipDetector.get_email_cluster(
                        email.id, email.user_id
                    )

                    logger.debug(
                        f"Found {len(email_cluster)} related emails for tracking {tracking_number}"
                    )

                    if not existing_package:
                        # Create new package from thread
                        package = await ThreadAwarePackageBuilder.build_package_from_emails(
                            email.user_id, email_cluster
                        )

                        if package:
                            await package.insert()
                            packages_created += 1
                            logger.info(
                                f"Created package {package.tracking_number} from {len(email_cluster)} emails"
                            )
                    else:
                        # Enrich existing package with new related emails
                        if len(email_cluster) > len(existing_package.related_email_ids):
                            enriched = await ThreadAwarePackageBuilder.enrich_existing_package(
                                existing_package, email_cluster
                            )
                            await enriched.save()
                            packages_enriched += 1
                            logger.info(
                                f"Enriched package {enriched.tracking_number} with {len(email_cluster)} emails"
                            )

            except Exception as e:
                logger.error(f"Error processing email {email.id}: {e}", exc_info=True)
                continue

        logger.info(
            f"Thread-aware package building completed. "
            f"Created: {packages_created}, Enriched: {packages_enriched}"
        )

    except Exception as e:
        logger.error(
            f"Error in thread-aware package building job: {e}", exc_info=True
        )
