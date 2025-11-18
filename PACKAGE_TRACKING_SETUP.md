# Package Tracking Feature - Setup Guide

## ✅ Implementation Complete (AfterShip Integration)

The package tracking feature has been fully implemented with automatic email detection, AfterShip API integration (1,100+ carriers), and a specialized AI agent.

---

## 🏗️ Architecture Overview

### Components Built

1. **Database Layer** (`app/packages/`)
   - `models.py` - Package, TrackingEvent, CourierService, PackageStatus models
   - `schemas.py` - Pydantic schemas for API requests/responses
   - `service.py` - PackageService for CRUD operations

2. **Courier Detection** (`app/packages/courier_detector.py`)
   - Email domain pattern matching
   - Tracking number pattern recognition (USPS, FedEx, UPS, Amazon, DHL, OnTrac, LaserShip)
   - Merchant extraction
   - Order number extraction
   - Confidence scoring

3. **Courier API Client** (`app/packages/courier_apis/`)
   - `base_courier.py` - Abstract base class
   - `aftership_client.py` - AfterShip SDK integration
   - **Supports 1,100+ carriers** through single API (USPS, FedEx, UPS, Amazon, DHL, etc.)
   - **Ready to use** with free API key (100 shipments/month)

4. **AI Agent Tools** (`app/agent/package_tools.py`)
   - `detect_tracking_email()` - Analyze emails for tracking info
   - `create_package_from_email()` - Create package records
   - `get_user_packages()` - List user's packages
   - `track_package_status()` - Get real-time status from courier APIs

5. **Package Tracking Agent** (`app/agent/package_agent.py`)
   - Specialized agent for package-related queries
   - Integrated via **handoff pattern** from main LifeOS Assistant
   - Conversational package tracking with emojis and natural language

6. **Background Jobs** (`app/workers/tasks.py`)
   - `process_package_emails_job()` - Scans new emails for tracking info (every 15 min)
   - `update_package_status_job()` - Updates package status from courier APIs (every 2 hours)

7. **Main Agent Integration** (`app/agent/service.py`)
   - Package Tracking Agent added as handoff
   - Updated system prompt with package tracking capability
   - Automatic user context injection

---

## 🔄 How It Works

### Automatic Package Detection Flow

```
1. Email arrives → Email Sync Job (every 15 min)
2. Package Email Processing Job (every 15 min)
   ↓
3. CourierDetector analyzes email
   - Checks email domain (amazon.com, fedex.com, etc.)
   - Extracts tracking numbers via regex patterns
   - Detects courier service
   - Calculates confidence score
   ↓
4. If confidence >= 0.7 → Create Package record in MongoDB
   ↓
5. Package Status Update Job (every 2 hours)
   - Polls courier APIs for updates
   - Updates package status and events
   ↓
6. User asks "Where's my package?"
   - Main agent hands off to Package Tracking Agent
   - Agent queries packages and provides status
```

### User Interaction Flow

**User**: "Where are my packages?"

**LifeOS Assistant** → Handoff → **Package Tracking Agent**

**Package Tracking Agent**:
- Calls `get_user_packages()`
- Returns: "You have 2 packages! 📦 Amazon order arriving tomorrow, 🚚 FedEx in transit"

---

## ⚙️ Configuration

### 1. Install Python SDK

```bash
pip install aftership-tracking-sdk
```

The SDK is already added to `requirements.txt`.

### 2. Get Free AfterShip API Key

1. Sign up at: https://www.aftership.com/
2. Navigate to **API** section in dashboard
3. Copy your API key
4. **Free tier**: 100 shipments/month (perfect for personal use)

### 3. Environment Variables

Add to your `.env` file:

```bash
# Package Tracking Jobs
PACKAGE_EMAIL_CHECK_INTERVAL_MINUTES=15      # How often to scan emails
PACKAGE_STATUS_UPDATE_INTERVAL_MINUTES=120  # How often to update status (2 hours)

# AfterShip API (REQUIRED for real tracking)
AFTERSHIP_API_KEY=your_aftership_api_key_here
```

That's it! **One API key** for all 1,100+ carriers.

---

## 📁 File Structure

```
app/
├── packages/
│   ├── __init__.py
│   ├── models.py                    # Database models
│   ├── schemas.py                   # Pydantic schemas
│   ├── service.py                   # Business logic
│   ├── courier_detector.py          # Email/tracking detection
│   └── courier_apis/
│       ├── __init__.py
│       ├── base_courier.py          # Abstract base class
│       └── aftership_client.py      # AfterShip SDK client (1,100+ carriers)
├── agent/
│   ├── package_agent.py             # Specialized package agent
│   ├── package_tools.py             # Agent tools for packages
│   └── service.py                   # Updated with handoff
├── workers/
│   ├── tasks.py                     # Background jobs
│   └── scheduler.py                 # Job scheduler
├── database.py                      # Added Package model
└── config.py                        # Added package settings
```

---

## 🧪 Testing the Feature

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install `aftership-tracking-sdk` and all other dependencies.

### 2. Start the Application

```bash
# Ensure MongoDB is running
# Start the FastAPI server
uvicorn app.main:app --reload
```

### 2. Test Package Detection

Send yourself a test email with tracking info:

**Subject**: "Your Amazon order has shipped"
**Body**:
```
Your order #123-4567890-1234567 has shipped!

Tracking Number: TBA123456789012
Carrier: Amazon Logistics
```

Wait 15 minutes for the background job, or manually trigger detection via the agent.

### 3. Test Agent Interaction

**User Message**: "Check my packages"

**Expected Response** from Package Tracking Agent:
```
You have 1 package tracked! 📦

📦 Amazon package (TBA123456789012)
Status: In Transit 🚚
Estimated Delivery: Tomorrow
Last Update: Package departed facility
```

---

## 🚀 Next Steps

### Immediate Setup (5 minutes)

1. ✅ **Get AfterShip API key** (free): https://www.aftership.com/
2. ✅ **Add to `.env`**: `AFTERSHIP_API_KEY=your_key_here`
3. ✅ **Install SDK**: `pip install aftership-tracking-sdk`
4. ✅ **Start server**: Background jobs will automatically track packages!

### Already Supports

✅ **1,100+ Carriers** including:
   - USPS, FedEx, UPS
   - Amazon Logistics
   - DHL, OnTrac, LaserShip
   - International carriers
   - Regional carriers

✅ **No additional setup needed** - AfterShip auto-detects courier from tracking number

### Enhancements

1. **User Notifications**
   - Push notifications when package is delivered
   - Email alerts for delivery exceptions
   - SMS notifications

2. **iOS App Integration**
   - Show packages in iOS app
   - Package status widgets
   - Delivery notifications

3. **Advanced Features**
   - Package delivery photos
   - Signature required tracking
   - Multiple package consolidation
   - Package return tracking

---

## 🐛 Troubleshooting

### Packages Not Being Detected

1. Check background job logs:
   ```bash
   # Look for "Package email processing job" logs
   tail -f logs/app.log | grep package
   ```

2. Verify email sync is working:
   ```bash
   # Check email sync logs
   tail -f logs/app.log | grep "email sync"
   ```

3. Test courier detector manually:
   ```python
   from app.packages.courier_detector import CourierDetector

   result = CourierDetector.analyze_email(
       from_email="ship-confirm@amazon.com",
       subject="Your order has shipped",
       body="Tracking: TBA123456789012"
   )
   print(result)
   ```

### AfterShip API Errors

**Error: "AfterShip API key not configured"**
- Add `AFTERSHIP_API_KEY=your_key` to `.env` file
- Restart the server

**Error: "Rate limit exceeded"**
- Free tier: 10 requests/second, 100 shipments/month
- Background job runs every 2 hours (well within limits)
- Upgrade if tracking > 100 packages/month

**Error: "Invalid tracking number"**
- Ensure tracking number is correct
- AfterShip will auto-detect courier
- Check AfterShip dashboard for details

**Error: "Authentication failed"**
- Verify API key is correct
- Check AfterShip account is active
- Generate new API key if needed

---

## 📊 Database Schema

### Package Model

```python
{
    "user_id": ObjectId,
    "email_id": ObjectId,           # Source email
    "tracking_number": "1Z999AA10123456784",
    "courier_service": "ups",
    "status": "in_transit",
    "product_name": "MacBook Pro",
    "merchant": "Apple",
    "current_location": "Memphis, TN",
    "estimated_delivery": datetime,
    "events": [
        {
            "timestamp": datetime,
            "status": "in_transit",
            "location": "Memphis, TN",
            "description": "Package arrived at facility"
        }
    ],
    "is_active": true,
    "created_at": datetime,
    "updated_at": datetime
}
```

---

## 🎉 Summary

You now have a fully functional package tracking system that:

✅ **Automatically detects** tracking emails
✅ **Extracts** tracking numbers and courier info
✅ **Stores** package data in MongoDB
✅ **Updates** status via AfterShip API (background jobs every 2 hours)
✅ **Provides** conversational tracking via AI agent
✅ **Supports 1,100+ carriers** through single AfterShip API
✅ **Integrates** with your existing LifeOS Assistant

## 🔑 Just Add Your API Key!

1. Get free API key: https://www.aftership.com/
2. Add to `.env`: `AFTERSHIP_API_KEY=your_key_here`
3. Run: `pip install -r requirements.txt`
4. Start server - tracking works immediately!

**Free tier**: 100 shipments/month (perfect for personal use)
**Upgrade**: $9/month for 500 shipments if needed
