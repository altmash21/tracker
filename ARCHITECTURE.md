# System Architecture - WhatsApp Expense Tracker

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│                         USER INTERACTIONS                           │
│                                                                     │
│  ┌──────────────────┐              ┌──────────────────┐            │
│  │   WhatsApp App   │              │   Web Browser    │            │
│  │                  │              │                  │            │
│  │  • Send messages │              │  • Dashboard     │            │
│  │  • Receive msgs  │              │  • Manage data   │            │
│  └────────┬─────────┘              └────────┬─────────┘            │
│           │                                 │                      │
└───────────┼─────────────────────────────────┼──────────────────────┘
            │                                 │
            │                                 │
            ▼                                 ▼
┌───────────────────────────────────────────────────────────────────┐
│                                                                   │
│                    WHATSAPP BUSINESS CLOUD API                    │
│                      (Meta Infrastructure)                        │
│                                                                   │
│  • Message routing                                                │
│  • Delivery confirmation                                          │
│  • Media handling                                                 │
│                                                                   │
└──────────────────────────┬────────────────────────────────────────┘
                           │
                           │ HTTPS Webhook
                           │
                           ▼
┌───────────────────────────────────────────────────────────────────┐
│                                                                   │
│                    DJANGO BACKEND APPLICATION                     │
│                     (expense_tracker project)                     │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                 WHATSAPP INTEGRATION APP                    │ │
│  │                                                             │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │ │
│  │  │   Webhook    │  │   Message    │  │   WhatsApp   │     │ │
│  │  │   Handler    │→ │   Parser     │→ │   Service    │     │ │
│  │  │              │  │              │  │              │     │ │
│  │  │ • Verify     │  │ • Expense    │  │ • Send msgs  │     │ │
│  │  │ • Route msgs │  │ • Commands   │  │ • Templates  │     │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘     │ │
│  │                                                             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                             │                                     │
│                             ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    BUSINESS LOGIC LAYER                     │ │
│  │                                                             │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │ │
│  │  │   Expense    │  │  Statement   │  │  Category    │     │ │
│  │  │   Parser     │  │  Generator   │  │  Manager     │     │ │
│  │  │              │  │              │  │              │     │ │
│  │  │ • Validate   │  │ • Daily      │  │ • Fuzzy      │     │ │
│  │  │ • Extract    │  │ • Weekly     │  │   match      │     │ │
│  │  │ • Match cat  │  │ • Monthly    │  │ • Aliases    │     │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘     │ │
│  │                                                             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                             │                                     │
│                             ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                      DASHBOARD APP                          │ │
│  │                                                             │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │ │
│  │  │     Auth     │  │  Analytics   │  │    CRUD      │     │ │
│  │  │    Views     │  │    Views     │  │   Views      │     │ │
│  │  │              │  │              │  │              │     │ │
│  │  │ • Login      │  │ • Dashboard  │  │ • Expenses   │     │ │
│  │  │ • Register   │  │ • Charts     │  │ • Categories │     │ │
│  │  │ • WhatsApp   │  │ • Reports    │  │ • Settings   │     │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘     │ │
│  │                                                             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                             │                                     │
│                             ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                      DATA MODELS LAYER                      │ │
│  │                                                             │ │
│  │  ┌─────────┐  ┌──────────────┐  ┌──────────┐  ┌─────────┐ │ │
│  │  │  User   │  │   WhatsApp   │  │ Category │  │ Expense │ │ │
│  │  │  Model  │  │   Mapping    │  │  Model   │  │  Model  │ │ │
│  │  │         │  │              │  │          │  │         │ │ │
│  │  │ • Auth  │  │ • Number→    │  │ • Name   │  │ • Amount│ │ │
│  │  │ • OTP   │  │   User map   │  │ • Icon   │  │ • Date  │ │ │
│  │  │ • Phone │  │ • Active     │  │ • Color  │  │ • Source│ │ │
│  │  └────┬────┘  └──────┬───────┘  └────┬─────┘  └────┬────┘ │ │
│  │       │              │                │             │      │ │
│  └───────┼──────────────┼────────────────┼─────────────┼──────┘ │
│          │              │                │             │        │
└──────────┼──────────────┼────────────────┼─────────────┼────────┘
           │              │                │             │
           ▼              ▼                ▼             ▼
┌───────────────────────────────────────────────────────────────────┐
│                                                                   │
│                        DATABASE LAYER                             │
│                      (SQLite / PostgreSQL)                        │
│                                                                   │
│  Tables: users, whatsapp_mappings, categories, expenses           │
│  Indexes: whatsapp_number, user+date, user+category              │
│  Relations: Foreign Keys with CASCADE/PROTECT                     │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagrams

### Flow 1: WhatsApp Expense Entry

```
User sends WhatsApp message
         │
         ▼
WhatsApp Cloud API receives message
         │
         ▼
POST to /whatsapp/webhook/
         │
         ▼
Webhook Handler verifies and parses
         │
         ▼
Look up user by WhatsApp number (WhatsAppMapping)
         │
         ├──► Not found: Send "Not registered" message
         │
         ▼
Parse message (ExpenseParser)
         │
         ├──► Invalid format: Send help message
         ├──► Unknown category: Send available categories
         │
         ▼
Create Expense record in database
         │
         ▼
Generate confirmation message
         │
         ▼
Send via WhatsApp Service
         │
         ▼
User receives confirmation
```

### Flow 2: Statement Generation

```
User sends command (e.g., "today")
         │
         ▼
Webhook receives and routes to command handler
         │
         ▼
StatementGenerator.generate_today()
         │
         ▼
Query expenses from database
         │
         ├──► Filter by user
         ├──► Filter by date
         └──► Join with categories
         │
         ▼
Aggregate by category
         │
         ▼
Format message with emojis and totals
         │
         ▼
Send formatted statement via WhatsApp
         │
         ▼
User receives statement
```

### Flow 3: Web Dashboard Access

```
User visits /dashboard/
         │
         ▼
@login_required decorator checks authentication
         │
         ├──► Not authenticated: Redirect to /login/
         │
         ▼
Query expenses and categories for user
         │
         ├──► Today's total
         ├──► Week's total
         ├──► Month's total
         ├──► Category breakdown
         └──► Recent expenses
         │
         ▼
Render dashboard.html with context
         │
         ▼
User sees analytics and charts
```

### Flow 4: User Registration & WhatsApp Linking

```
User fills registration form
         │
         ▼
POST to /register/
         │
         ▼
Validate inputs (password match, unique username/email)
         │
         ▼
Create User record with hashed password
         │
         ▼
Create default categories (Food, Travel, etc.)
         │
         ▼
Redirect to /login/
         │
         ▼
User logs in
         │
         ▼
Clicks "Link WhatsApp"
         │
         ▼
POST WhatsApp number
         │
         ▼
Generate 6-digit OTP
         │
         ▼
Send OTP via WhatsApp Service
         │
         ▼
User receives OTP on WhatsApp
         │
         ▼
User enters OTP in web form
         │
         ▼
Verify OTP (check expiry < 10 mins)
         │
         ├──► Invalid/Expired: Show error
         │
         ▼
Create WhatsAppMapping record
         │
         ▼
Set whatsapp_verified = True
         │
         ▼
User can now use WhatsApp to add expenses
```

---

## Component Interaction Matrix

```
┌────────────────┬──────────┬──────────┬──────────┬──────────┐
│  Component     │  User    │ WhatsApp │ Category │ Expense  │
├────────────────┼──────────┼──────────┼──────────┼──────────┤
│ Webhook        │   Read   │   Read   │   Read   │  Create  │
│ Dashboard      │   Read   │   Read   │   CRUD   │  CRUD    │
│ Parser         │   Read   │    -     │   Read   │  Create  │
│ Generator      │   Read   │    -     │   Read   │   Read   │
│ Auth Views     │  Create  │  Update  │  Create  │    -     │
└────────────────┴──────────┴──────────┴──────────┴──────────┘
```

---

## Security Layers

```
┌─────────────────────────────────────────────────────────┐
│  LAYER 1: TRANSPORT SECURITY                            │
│  • HTTPS/TLS encryption                                 │
│  • SSL certificate validation                           │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│  LAYER 2: AUTHENTICATION                                │
│  • Django session-based auth                            │
│  • Password hashing (PBKDF2)                            │
│  • WhatsApp OTP verification                            │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│  LAYER 3: AUTHORIZATION                                 │
│  • @login_required decorators                           │
│  • User-specific data filtering                         │
│  • Permission checks                                    │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│  LAYER 4: DATA VALIDATION                               │
│  • Input sanitization                                   │
│  • CSRF protection                                      │
│  • Webhook signature verification (ready)               │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│  LAYER 5: DATA PROTECTION                               │
│  • Encrypted passwords                                  │
│  • Environment variables for secrets                    │
│  • Soft deletes (data recovery)                         │
└─────────────────────────────────────────────────────────┘
```

---

## Scalability Architecture

```
                    ┌──────────────────┐
                    │   Load Balancer  │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
         ┌────▼────┐    ┌────▼────┐   ┌────▼────┐
         │ Django  │    │ Django  │   │ Django  │
         │ Server 1│    │ Server 2│   │ Server 3│
         └────┬────┘    └────┬────┘   └────┬────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                    ┌────────▼─────────┐
                    │  Redis Cache     │
                    │  (Session Store) │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │   PostgreSQL     │
                    │   (Primary DB)   │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  PostgreSQL      │
                    │  (Read Replica)  │
                    └──────────────────┘
```

---

## Deployment Architecture (Production)

```
┌─────────────────────────────────────────────────────────────┐
│                        CLOUD PROVIDER                       │
│                  (DigitalOcean/AWS/Render)                  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                    CDN / CloudFlare                   │ │
│  │  • SSL/TLS termination                                │ │
│  │  • DDoS protection                                    │ │
│  │  • Static file caching                                │ │
│  └─────────────────────┬─────────────────────────────────┘ │
│                        │                                    │
│  ┌─────────────────────▼─────────────────────────────────┐ │
│  │              Application Server (Gunicorn)            │ │
│  │  • Django WSGI application                            │ │
│  │  • Multiple worker processes                          │ │
│  │  • Request handling                                   │ │
│  └─────────────────────┬─────────────────────────────────┘ │
│                        │                                    │
│  ┌─────────────────────▼─────────────────────────────────┐ │
│  │           Managed PostgreSQL Database                 │ │
│  │  • Automated backups                                  │ │
│  │  • High availability                                  │ │
│  │  • Connection pooling                                 │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │              Static Files Storage (S3/CDN)            │ │
│  │  • CSS, JavaScript, Images                            │ │
│  │  • Globally distributed                               │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │            Monitoring & Logging (Optional)            │ │
│  │  • Sentry (Error tracking)                            │ │
│  │  • CloudWatch/Datadog (Metrics)                       │ │
│  │  • LogDNA (Centralized logs)                          │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Technology Stack Summary

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND LAYER                          │
│  • HTML5, CSS3 (Custom)                                     │
│  • Minimal JavaScript                                       │
│  • Responsive design                                        │
└─────────────────────────────────────────────────────────────┘
                             │
┌─────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                        │
│  • Django 5.2.9                                             │
│  • Django REST Framework 3.16.1                             │
│  • Python 3.10+                                             │
└─────────────────────────────────────────────────────────────┘
                             │
┌─────────────────────────────────────────────────────────────┐
│                     INTEGRATION LAYER                       │
│  • WhatsApp Business Cloud API                              │
│  • Requests library (HTTP client)                           │
│  • JSON message formatting                                  │
└─────────────────────────────────────────────────────────────┘
                             │
┌─────────────────────────────────────────────────────────────┐
│                      DATABASE LAYER                         │
│  • SQLite (Development)                                     │
│  • PostgreSQL (Production)                                  │
│  • Django ORM                                               │
└─────────────────────────────────────────────────────────────┘
                             │
┌─────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT LAYER                         │
│  • Gunicorn (WSGI Server)                                   │
│  • Nginx (Reverse Proxy)                                    │
│  • Docker (Containerization - optional)                     │
└─────────────────────────────────────────────────────────────┘
```

---

This architecture ensures:
✅ Separation of concerns
✅ Scalability
✅ Security
✅ Maintainability
✅ Easy deployment
✅ Real-time message handling
✅ Data integrity
