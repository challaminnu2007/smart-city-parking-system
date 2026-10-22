# Smart Parking Management System (SmartPark)
### Advanced Full-Stack IoT-Ready Smart Urban Parking Platform

A professional, fully functional, production-ready **Smart Parking Management System** engineered for college project demonstrations and urban parking operations. Built with a modular Python Flask backend, SQLite database layer (ready for PostgreSQL deployment), responsive modern HTML5/CSS3/JavaScript frontend, secure session authentication, cryptographic QR parking pass engine, Razorpay payment gateway integration with local test simulator, and Twilio SMS notification dispatch.

---

## 1. System Overview & Key Capabilities

- **Real-Time Bay Availability**: Dynamic bay states (`AVAILABLE`, `RESERVED`, `OCCUPIED`, `MAINTENANCE`) calculated strictly from database records with zero hardcoded metrics.
- **Transparent ₹30/Hour Billing**: Automated billable duration computation with a 1-hour minimum charge and ceiling rounding on partial hours.
- **Concurrency & Overlap Prevention**: Transactional conflict detection prevents double-booking of any slot across overlapping arrival windows.
- **Cryptographic QR Parking Passes**: High-resolution server-generated QR codes equipped with HMAC-SHA256 digital signatures to prevent pass counterfeiting.
- **Payment Gateway with Local Simulator**: Complete integration with Razorpay (Cards, UPI, Netbanking) alongside a clearly-labelled **Local Development Payment Simulator** for immediate offline grading and testing without external API keys.
- **SMS Confirmation Service**: Dispatch of booking receipts via Twilio with fallback local audit logging and retry queues.
- **Role-Based Access Control (RBAC)**: Secure separation between customer accounts (`USER`) and administrative consoles (`ADMIN`) enforced by backend decorators.
- **Administrator Operations Console**: Full CRUD parking bay manager, user account activation controls, gate check-in/check-out clearance, Chart.js visual analytics, and CSV financial report exports.
- **Dual Perspective Navigation**: Administrators can toggle directly into the customer experience via the **"User View"** link without role degradation.

---

## 2. Technology Stack

- **Backend Framework**: Python 3.10+ / 3.14 with Flask (Modular Blueprints architecture)
- **Database & ORM**: SQLite (`instance/smart_parking.db`) with SQLAlchemy / Flask-SQLAlchemy (deployment-ready for PostgreSQL)
- **Security & Hashing**: Werkzeug cryptographic password hashing, HMAC SHA-256 tokens, session protection
- **QR Code Generation**: Python `qrcode` with Pillow (`PIL`) image engine
- **Payment Processing**: Razorpay Python SDK with backend signature verification and Local Dev Simulator
- **SMS Notifications**: Twilio Python SDK with local notification database logging
- **Frontend Technologies**: Semantic HTML5, Custom CSS3 (Modern Smart City theme), Vanilla JavaScript ES6+
- **Data Visualization**: Chart.js 4.4
- **Testing Suite**: Pytest 8.0+

---

## 3. Project Directory Structure

```
smart_parking_system/
│
├── app.py                      # Flask Application Factory & Global Error Handlers
├── config.py                   # Configuration Class & Environment Settings
├── requirements.txt            # Python Dependencies
├── .env.example                # Template Environment Variables
├── .env                        # Local Environment Configuration
├── .gitignore                  # Git Ignore Specifications
├── README.md                   # Full Technical Documentation & User Guide
│
├── database/                   # Database Layer
│   ├── __init__.py
│   ├── db.py                   # SQLAlchemy Database Instance
│   └── init_db.py              # Automated Table Creation & Safe Admin/Slot Seeding
│
├── models/                     # SQLAlchemy Relational Models
│   ├── __init__.py
│   ├── user.py                 # User Model (Motorists & Admins)
│   ├── parking_slot.py         # Parking Bay Model
│   ├── booking.py              # Reservation Model & Concurrency
│   ├── payment.py              # Payment Audit Records
│   ├── notification.py         # SMS Notification Log Model
│   └── audit_log.py            # Administrative Action Audit Trail
│
├── routes/                     # Modular Flask Blueprints
│   ├── __init__.py
│   ├── auth_routes.py          # Registration, Login, Profile & RBAC Decorators
│   ├── user_routes.py          # User Dashboard & Customer Metrics
│   ├── admin_routes.py         # Admin Dashboard, Bay CRUD & CSV Export
│   ├── parking_routes.py       # Slot Discovery & Availability Queries
│   ├── booking_routes.py       # Reservation Creation & Cancellation
│   ├── payment_routes.py       # Order Creation & Signature Verification
│   └── qr_routes.py            # QR Pass Generation & Gate Check-in/Out
│
├── services/                   # Core Business Logic Layer
│   ├── __init__.py
│   ├── booking_service.py      # Pricing Formula (₹30/hr) & Overlap Detection
│   ├── payment_service.py      # Razorpay Gateway & Local Dev Simulator
│   ├── qr_service.py           # HMAC Token Generator & QR Image Builder
│   └── sms_service.py          # Twilio SMS Engine & Notification Logger
│
├── templates/                  # Jinja2 HTML5 Templates
│   ├── base.html               # Master Layout (Navbar, Toast Container, Footer)
│   ├── index.html              # High-Impact Modern Landing Page
│   ├── login.html              # Login Page with Demo Credential Helper
│   ├── register.html           # Driver Registration Form with Validations
│   ├── user_dashboard.html     # User Dashboard with Live Slot Availability
│   ├── parking_slots.html      # Bay Discovery with Multi-Filter Toolbar
│   ├── booking.html            # Booking Form & Real-Time Price Calculation
│   ├── payment.html            # Checkout (Razorpay + Local Dev Simulator)
│   ├── booking_confirmation.html # Confirmation Page with Digital QR Pass
│   ├── pass_print.html         # High-Contrast Print-Friendly Entry Ticket
│   ├── my_bookings.html        # Tabbed View of Active, Pending & Past Passes
│   ├── parking_history.html    # Historical Parking Session Records
│   ├── profile.html            # Profile Settings & Secure Password Changer
│   ├── admin_dashboard.html    # Admin Operations Console & QR Gate Validator
│   ├── admin_slots.html        # Admin Bay Management Interface
│   ├── admin_users.html        # Admin Motorist Directory & Account Toggles
│   ├── admin_bookings.html     # Admin Bookings Oversight & Gate Clearances
│   ├── admin_payments.html     # Admin Payment Audit & CSV Export
│   ├── admin_analytics.html    # Chart.js Visual Utilization Analytics
│   ├── 403.html                # Forbidden Access Page
│   ├── 404.html                # Page Not Found Error Page
│   └── 500.html                # Internal Server Error Page
│
├── static/                     # Static Assets
│   ├── css/
│   │   └── style.css           # Master Stylesheet (Dark Navy/Cyan Smart Theme)
│   ├── js/
│   │   ├── main.js             # Mobile Menu, Toast Engine & Modal Controls
│   │   ├── dashboard.js        # User Dashboard Real-Time Statistics
│   │   ├── parking.js          # Live Bay Filtering & Search
│   │   ├── booking.js          # Booking Validation & Price Recalculation
│   │   └── payment.js          # Razorpay & Simulator Checkout Logic
│   └── images/                 # Image Directory
│
├── tests/                      # Automated Pytest Suite
│   ├── test_auth.py            # Authentication & Registration Tests
│   ├── test_parking.py         # Slot Filtering & Availability Tests
│   ├── test_booking.py         # ₹30/hr Formula & Overlap Conflict Tests
│   ├── test_permissions.py     # Role-Based Access Control (RBAC) Tests
│   └── test_payments.py        # Order Creation, QR Issuance & Verification Tests
│
└── instance/
    ├── .gitkeep
    └── smart_parking.db        # SQLite Database (Automatically Initialized)
```

---

## 4. Default Administrator Account

The system automatically initializes the default administrator on the first run using credentials configured in `.env`.

- **Admin Full Name**: Pournami
- **Admin Mobile Number**: 8106479530
- **Admin Email**: `admin@smartparking.com`
- **Initial Password**: `Admin@12345`
- **Role**: `ADMIN`

> **Security Guarantee**: The initialization script inspects whether an administrator account already exists. It **never** overwrites an updated password or resets existing admin accounts upon server restarts.

---

## 5. Quick-Start Guide (Windows & VS Code)

Follow these exact terminal commands in your Visual Studio Code PowerShell terminal:

### Step 1: Open Terminal in Project Directory
```powershell
cd "c:\Users\Merugu Pournami\OneDrive\Desktop\ai lab project\smart_parking_system"
```

### Step 2: Create Python Virtual Environment
```powershell
python -m venv venv
```

### Step 3: Activate Virtual Environment
```powershell
.\venv\Scripts\Activate.ps1
```
*(If PowerShell displays an execution policy error, run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` and retry activation).*

### Step 4: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 5: Verify Environment Configuration
A ready-to-run `.env` file is already created. You can inspect or modify it as needed:
```powershell
Get-Content .env
```

### Step 6: Initialize Database (Automatic on Startup)
Tables and sample bays are created automatically when starting the server. If you want to initialize or reset manually:
```powershell
python database\init_db.py
```

### Step 7: Run the Application
```powershell
python app.py
```
*(Or run `python run.py` from the root workspace directory).*

Open your browser and navigate to:
**`http://127.0.0.1:5000`**

---

## 6. External Service Configurations (Razorpay & Twilio)

### A. Razorpay Payment Gateway (Cards, UPI, Netbanking)
- If you have Razorpay Test API keys, add them to your `.env` file:
  ```env
  RAZORPAY_KEY_ID=rzp_test_YourKeyHere
  RAZORPAY_KEY_SECRET=YourSecretHere
  ```
- **Local Development Payment Simulator**: If keys are left blank, the application automatically activates the clearly-labelled **Local Development Payment Simulator**. This allows faculty demonstration and complete end-to-end checkout with genuine cryptographic QR pass generation without spending real money or needing external bank accounts.

### B. Twilio SMS Notifications
- If you have Twilio credentials, configure them in `.env`:
  ```env
  TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  TWILIO_AUTH_TOKEN=your_auth_token_here
  TWILIO_PHONE_NUMBER=+1234567890
  ```
- **Local SMS Notification Log**: If credentials are empty, messages are logged directly to the database `notifications` table, marked with `status='DEV_SIMULATED'`, and viewable in the confirmation screen and admin logs.

---

## 7. Faculty Demonstration Walkthrough

Follow this 5-minute presentation script for your faculty or college viva:

1. **Landing Page (`/`)**:
   - Showcase the modern smart-city interface, live facility monitor teaser, and ₹30/hour pricing banner.
2. **Administrator Sign-In (`/login`)**:
   - Use the demo quick-fill helper or enter `admin@smartparking.com` / `Admin@12345`.
   - Arrive at the **Admin Console (`/admin`)**.
   - Review live KPI cards (Total Bays, Available, Occupied, Verified Revenue).
3. **Bay & Rate Management (`/admin/slots`)**:
   - Demonstrate adding a new parking slot (e.g. `VIP-01`, Zone: Level 1, Rate: ₹30).
   - Show how slots can be marked for maintenance or edited.
4. **Switch to Customer Perspective (`/dashboard`)**:
   - Click **"User View"** in the top navigation bar.
   - Show how administrators can test user experiences without compromising security.
5. **Slot Discovery & Overlap Prevention (`/slots`)**:
   - Browse bays by Zone (Ground, Level 1, EV Plaza) and Vehicle Type (Standard, SUV, EV).
   - Select an available bay and click **"Book This Slot"**.
6. **Booking & Pricing Preview (`/book/<slot_id>`)**:
   - Notice the pre-filled vehicle plate.
   - Adjust duration from 1 to 3 hours: observe the real-time calculation update from ₹30 to ₹90.
   - Click **"Proceed to Secure Payment"**.
7. **Payment & QR Generation (`/payment/<booking_id>`)**:
   - Select payment channel (Razorpay or Local Dev Simulator).
   - Click **Complete Simulated Payment**.
   - Notice the instant redirect to the **Booking Confirmation (`/confirmation/<booking_id>`)**.
8. **Digital QR Pass & Print Ticket (`/pass/<booking_id>/print`)**:
   - Inspect the generated QR code embedded with an HMAC-SHA256 signature.
   - Click **"Print Friendly Pass"** to display the clean printable parking pass.
9. **Gate Scanner Verification (`/admin`)**:
   - Return to Admin Console -> Click **"Gate QR Validator"**.
   - Paste the booking reference (e.g. `BK-...`).
   - Click **"Validate Cryptographic Pass"**: verify green "PASS VERIFIED" banner.
   - Click **"Check In Vehicle Now"**: notice the bay status instantly changes to `OCCUPIED`.
   - Click **"Check Out Vehicle"**: notice the bay status returns to `AVAILABLE`.
10. **Financial & Visual Analytics (`/admin/analytics`)**:
    - Show Chart.js visualizations: Zone occupancy, peak arrival hours, and revenue trends.
    - Click **"Export Payments CSV Report"** to download the accounting spreadsheet.

---

## 8. Running the Automated Test Suite

Run all automated unit and integration tests using pytest:

```powershell
python -m pytest smart_parking_system\tests -v
```

Expected output:
```
smart_parking_system/tests/test_auth.py::test_user_registration_success PASSED
smart_parking_system/tests/test_auth.py::test_user_registration_duplicate_username PASSED
smart_parking_system/tests/test_auth.py::test_user_login_and_logout PASSED
smart_parking_system/tests/test_auth.py::test_default_admin_login PASSED
smart_parking_system/tests/test_booking.py::test_hourly_price_calculation PASSED
smart_parking_system/tests/test_booking.py::test_create_booking_and_overlap_rejection PASSED
smart_parking_system/tests/test_booking.py::test_reject_past_booking_time PASSED
smart_parking_system/tests/test_parking.py::test_get_parking_slots PASSED
smart_parking_system/tests/test_parking.py::test_slot_filters PASSED
smart_parking_system/tests/test_parking.py::test_parking_availability_metrics PASSED
smart_parking_system/tests/test_payments.py::test_full_payment_and_qr_issuance_workflow PASSED
smart_parking_system/tests/test_permissions.py::test_unauthenticated_access_protection PASSED
smart_parking_system/tests/test_permissions.py::test_user_cannot_access_admin_portal PASSED
smart_parking_system/tests/test_permissions.py::test_admin_can_access_both_dashboards PASSED

======================= 14 passed in 4.08s =======================
```

---

## 9. Troubleshooting & FAQ

- **Q: How do I completely reset the database to sample state?**  
  Run `python database\init_db.py --reset` and type `y` to confirm.
- **Q: Can I deploy this application to PostgreSQL in production?**  
  Yes! Simply update `DATABASE_URL` in `.env` to:  
  `DATABASE_URL=postgresql://user:password@localhost:5432/smart_parking_db`  
  SQLAlchemy will automatically use PostgreSQL drivers without changing any application code.
- **Q: Where is the SQLite database stored?**  
  In `smart_parking_system/instance/smart_parking.db`. It is persisted across server restarts.

---

## 10. Authors & Academic Credits

- **Project Title**: Smart Parking Management System
- **Lead Administrator**: Pournami (+91 8106479530)
- **Architecture**: Full-Stack Flask, SQLite/PostgreSQL, REST APIs, Cryptographic QR Pass Engine.

