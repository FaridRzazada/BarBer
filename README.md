# Nearby — Barber & Salon Marketplace / Booking Platform

A production-oriented Django application for discovering, comparing and booking
barbers and salons. Customers find professionals on a real map, browse profiles,
portfolios and reviews, and book available time slots. Barbers and salons manage
their profile, services, working hours, team, products and appointments from a
dashboard.

Built with **Django 5.2 + Django REST Framework + PostgreSQL**, server-rendered
templates, a small **vanilla-JS** front-end (Fetch API), and **Leaflet +
OpenStreetMap** for maps. No Google Maps, no heavy JS framework.

---

## Features

- **Accounts & roles** — one custom `User` (email login). `role` is the *account*
  role (`customer` / `professional` / `admin`); the professional *type*
  (`barber` / `salon`) lives on `ProfessionalProfile`.
- **Profiles** — `CustomerProfile`, `ProfessionalProfile` → `BarberProfile` /
  `SalonProfile`, and `SalonMember` (a barber keeps their own account and can be
  added to a salon's team).
- **Services, working hours, breaks, days off** — fully editable per professional.
- **Availability engine** — generates real slots from working hours, breaks, days
  off, existing bookings and service duration; supports individual barbers,
  salon + specific barber, and salon + *any available barber*.
- **Bookings** — transactional creation with **double-booking protection** (row
  locking + server-side re-validation), status workflow
  (pending → confirmed → completed / cancelled / no-show).
- **Maps & GPS** — homepage and `/find/` show real professionals on a Leaflet
  map; "Use my location" uses the browser Geolocation API and a Haversine /
  bounding-box distance service (PostGIS-ready).
- **Search, filters & sorting** — backend-powered (name, service, city, type,
  rating, price, open-now; nearest / rating / price / newest).
- **Reviews & favorites** — reviews only for completed bookings (one per
  booking); favorite any professional.
- **Portfolio & gallery** — validated image uploads with lazy loading.
- **Products** — salon-only catalogue (display only; no cart/checkout).
- **Notifications** — in-app (navbar bell + page) and HTML email
  (`send_booking_*` templates).
- **Messaging** — customer ↔ professional conversations (AJAX polling; ready for
  WebSockets later).
- **Dashboards** — separate customer and professional dashboards; professional
  onboarding with a dynamic profile-completion meter.
- **Admin** — every model registered with list/filter/search/autocomplete and
  moderation actions (verify professional, resolve reports).
- **Responsive, accessible UI** — deliberate mobile layouts, semantic HTML, ARIA,
  keyboard focus, restrained "editorial" design system.
- **Tests** — 49+ tests focused on the booking engine and permissions.

---

## Architecture

```
config/                 # project package
  settings/             # base / development / production
  urls.py, api.py       # page routes + /api/ aggregation
apps/
  accounts/             # User, CustomerProfile, auth, registration
  professionals/        # ProfessionalProfile, Barber/Salon, SalonMember,
                        # WorkingHour, BreakTime, DayOff, Portfolio, Gallery,
                        # Favorite; nearby + search API; services.py
  services/             # ServiceCategory, Service
  bookings/             # Booking; services.py (availability engine); API
  reviews/              # Review; services.py (rules + rating summary)
  products/             # ProductCategory, Product, ProductImage
  notifications/        # Notification; services.py (in-app + email dispatch)
  messaging/            # Conversation, Message; services.py
  locations/            # City; services.py (Haversine / bounding box)
  core/                 # home/find/contact, ContactMessage, Report, errors,
                        # shared validators/uploads/mixins/API helpers
  dashboard/            # customer + professional dashboards (orchestration)
templates/  static/{css,js}/
```

Business logic lives in `services.py` modules, not views. See the model diagram
in the project brief (User → profiles → services/bookings/reviews/…).

---

## Getting started

### 1. Requirements
- Python 3.11+
- PostgreSQL 13+ (recommended). Without a `DATABASE_URL` the project falls back
  to SQLite so it runs out of the box for development.

### 2. Virtual environment & dependencies

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Environment

```bash
cp .env.example .env      # then edit values
```

Key variables (see `.env.example`): `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`,
`DATABASE_URL`, email (`EMAIL_*`, `DEFAULT_FROM_EMAIL`), map defaults
(`MAP_DEFAULT_LAT/LNG/ZOOM`, `NEARBY_DEFAULT_RADIUS_KM`).

### 4. PostgreSQL

Create a database and point `DATABASE_URL` at it:

```
DATABASE_URL=postgres://USER:PASSWORD@localhost:5432/DATABASE
```

If `DATABASE_URL` is omitted, a local `db.sqlite3` is used automatically.

### 5. Migrate, seed, run

```bash
python manage.py migrate
python manage.py seed_data          # optional demo data (dev only)
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/. Admin at http://127.0.0.1:8000/admin/.

**Demo accounts** (after `seed_data`, password `demo12345`):
`customer@nearby.local`, `barber1@nearby.local`, `salon@nearby.local`.

### 6. Tests

```bash
python manage.py test
```

---

## Emails

Development uses the console backend (emails print to the terminal). For real
SMTP, set `EMAIL_*` in `.env` and run with the production settings:

```bash
set DJANGO_SETTINGS_MODULE=config.settings.production   # Windows
export DJANGO_SETTINGS_MODULE=config.settings.production # macOS/Linux
```

---

## Production notes

- Use `config.settings.production` (HTTPS redirect, HSTS, secure cookies, SMTP,
  JSON-only API). Set `SECRET_KEY`, `ALLOWED_HOSTS`, `DATABASE_URL`,
  `CSRF_TRUSTED_ORIGINS`.
- `python manage.py collectstatic` and serve `STATIC_ROOT` / `MEDIA_ROOT` via
  your web server or object storage.
- The distance engine is written so it can be swapped for **PostGIS**
  (`ST_DWithin`) later without touching callers.
- Media is stored on the local filesystem by default; switch to a cloud storage
  backend for production.

---

## API (selection)

```
GET  /api/professionals/                 GET  /api/professionals/nearby/
GET  /api/professionals/<id>/            GET  /api/professionals/<id>/services/
GET  /api/bookings/available-slots/      POST /api/bookings/
GET  /api/bookings/  <id>/ (GET/PATCH/DELETE)
GET  /api/services/                      GET  /api/locations/cities/
GET  /api/notifications/  POST /api/notifications/<id>/read/
GET  /api/messages/  <id>/  POST /api/messages/
POST /api/favorites/  DELETE /api/favorites/<professional_id>/
POST /api/reviews/
```
