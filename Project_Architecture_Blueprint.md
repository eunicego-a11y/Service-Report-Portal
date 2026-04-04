# Project Architecture Blueprint

**Service Report App — MC Biotechnical Solutions**
_Generated: April 4, 2026 | Blueprint Version: 1.0_

---

## Table of Contents

1. [Architectural Overview](#1-architectural-overview)
2. [Architecture Visualization](#2-architecture-visualization)
3. [Core Architectural Components](#3-core-architectural-components)
4. [Architectural Layers and Dependencies](#4-architectural-layers-and-dependencies)
5. [Data Architecture](#5-data-architecture)
6. [Cross-Cutting Concerns](#6-cross-cutting-concerns)
7. [Service Communication Patterns](#7-service-communication-patterns)
8. [Python/Flask-Specific Patterns](#8-pythonflask-specific-patterns)
9. [Implementation Patterns](#9-implementation-patterns)
10. [Testing Architecture](#10-testing-architecture)
11. [Deployment Architecture](#11-deployment-architecture)
12. [Extension and Evolution Patterns](#12-extension-and-evolution-patterns)
13. [Architectural Pattern Examples](#13-architectural-pattern-examples)
14. [Architectural Decision Records](#14-architectural-decision-records)
15. [Architecture Governance](#15-architecture-governance)
16. [Blueprint for New Development](#16-blueprint-for-new-development)

---

## 1. Architectural Overview

### Technology Stack

| Component      | Technology                                    |
| -------------- | --------------------------------------------- |
| Backend        | Python 3, Flask                               |
| Authentication | Flask-Login + Authlib (OAuth 2.0)             |
| External API   | Monday.com GraphQL API v2023-10               |
| User Store     | JSON flat-file (`users.json`)                 |
| Frontend       | Jinja2 templates, Bootstrap 5, jQuery         |
| Client Storage | IndexedDB (signatures), localStorage (drafts) |
| Signature Pads | `signature_pad@4.0.0` (canvas-based)          |
| Search Widget  | Select2 (AJAX-backed)                         |
| Config         | `python-dotenv` (`.env` file)                 |

### Architectural Pattern

The application follows a **flat monolithic MVC pattern** within a single `app.py` file:

- **Model**: No ORM — data is either stored on Monday.com boards (primary persistent store) or in `users.json` (flat-file user registry). Monday.com acts as the external database.
- **View**: Jinja2 HTML templates in `templates/`
- **Controller**: Flask route functions (`@app.route`) defined inline in `app.py`

### Guiding Architectural Principles

1. **Monday.com as primary database** — Service entries, linked records, and signatures are all stored on Monday.com boards, not locally.
2. **Environment-driven configuration** — All board IDs, column IDs, and secrets are resolved at startup via environment variables.
3. **Offline resilience on the client** — IndexedDB stores failed signature uploads with retry via "Sync Now", and localStorage persists form drafts.
4. **Dual authentication** — Supports both Monday.com OAuth 2.0 (primary) and a local username/password system (fallback/legacy admin).
5. **Column-type-aware data formatting** — A central `format_column_value()` function handles all Monday.com column type serialisation, keeping route handlers clean.

---

## 2. Architecture Visualization

### High-Level System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Browser (Client)                                │
│                                                                         │
│  ┌───────────────┐  ┌──────────────────┐  ┌──────────────────────────┐ │
│  │  Login/Signup │  │  Main Form (/)   │  │  Offline Layer           │ │
│  │  (HTML forms) │  │  Bootstrap 5 UI  │  │  IndexedDB (signatures)  │ │
│  │               │  │  SignaturePad    │  │  localStorage (drafts)   │ │
│  │               │  │  Select2 (AJAX)  │  │                          │ │
│  └───────┬───────┘  └────────┬─────────┘  └──────────────────────────┘ │
└──────────┼──────────────────┼────────────────────────────────────────────┘
           │  HTTP            │  AJAX (XHR / Fetch)
           ▼                  ▼
┌──────────────────────────────────────────────────────────────────┐
│                     Flask Application (app.py)                   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                  Request Pipeline                           │ │
│  │  python-dotenv → Flask App Init → OAuth Setup → LoginMgr   │ │
│  └──────────────────────────┬──────────────────────────────────┘ │
│                             │                                    │
│  ┌──────────────────────────▼──────────────────────────────────┐ │
│  │                    Route Handlers                           │ │
│  │  /login  /signup  /auth/monday  /auth/monday/callback       │ │
│  │  /  (index)  /submit  /api/upload_signature                 │ │
│  │  /search_linked_items  /logout                              │ │
│  └───────────────────────┬─────────────────────────────────────┘ │
│                          │                                       │
│  ┌───────────────────────▼─────────────────────────────────────┐ │
│  │                  Helper Functions                           │ │
│  │  format_column_value()  upload_file_to_monday_bytes()       │ │
│  │  _read_users()  _write_users()                              │ │
│  └───────────┬──────────────────────┬───────────────────────── ┘ │
│              │                      │                           │
└──────────────┼──────────────────────┼───────────────────────────┘
               │                      │
               ▼                      ▼
  ┌────────────────────┐    ┌───────────────────────────────────┐
  │   users.json       │    │       Monday.com Platform         │
  │   (local user      │    │                                   │
  │    registry)       │    │  ┌─────────────────────────────┐  │
  └────────────────────┘    │  │  GraphQL API (v2023-10)      │  │
                            │  │  https://api.monday.com/v2   │  │
                            │  │                              │  │
                            │  │  - Main Board (MAIN_BOARD_ID)│  │
                            │  │  - Linked Board (LINK_BOARD) │  │
                            │  │  - File Upload API (/v2/file)│  │
                            │  └─────────────────────────────┘  │
                            │  ┌─────────────────────────────┐  │
                            │  │  OAuth 2.0 Auth Endpoint     │  │
                            │  │  https://auth.monday.com/    │  │
                            │  └─────────────────────────────┘  │
                            └───────────────────────────────────┘
```

### Authentication Flow Diagram

```
User: "Sign in with Monday.com"
        │
        ▼
  GET /auth/monday
        │
        └──► Authlib redirect to:
             https://auth.monday.com/oauth2/authorize
                        │
                        │ (OAuth code in callback)
                        ▼
  GET /auth/monday/callback?code=...
        │
        ├──► POST https://auth.monday.com/oauth2/token
        │         (exchange code → JWT access_token)
        │
        ├──► Decode JWT payload (base64) → extract uid, actid
        │
        ├──► Upsert user in users.json
        │         provider: "monday"
        │         password: null
        │
        ├──► Store access_token in Flask session
        │
        └──► login_user(User(username, name))
             redirect(url_for('index'))
```

### Form Submission Flow Diagram

```
User fills form + draws signatures
        │
        ▼
  JS: handleSubmit(e)   [AJAX, prevents default]
        │
        ├──► Auto-capture any unconfirmed signature pads
        │
        ├──► POST /submit  (multipart form)
        │         Headers: X-Requested-With: XMLHttpRequest
        │         │
        │         └── Flask: create_item mutation (Monday GraphQL)
        │                    → returns {success, item_id}
        │
        ├──► For each sigBlob in sigBlobs{}:
        │         POST /api/upload_signature
        │               file: PNG blob
        │               item_id: <new_item_id>
        │               sig_key: sig_tsp | sig_customer | ...
        │                 │
        │                 └── Flask: add_file_to_column mutation
        │                            (multipart to /v2/file)
        │
        ├──► If signature upload fails:
        │         saveSignatureBlob(key, blob, itemId) → IndexedDB
        │         (status: 'pending', retry via "Sync Now")
        │
        └──► Reset form, clear pads, clear draft
```

---

## 3. Core Architectural Components

### 3.1 Flask Application Bootstrap (`app.py` — top-level)

**Purpose**: Initialises the application, loads environment config, sets up OAuth, LocalLogin, and declares all routes and helpers in a single module.

**Key initialisation sequence**:

1. `load_dotenv()` — populates environment from `.env`
2. `Flask(__name__)` — creates WSGI app
3. `app.secret_key` — from `SECRET_KEY` env var
4. `OAuth(app)` + `oauth.register('monday', ...)` — Monday.com OAuth client
5. `LoginManager()` + `login_manager.init_app(app)` — session-based login management
6. Global API constants (`API_KEY`, `MAIN_BOARD`, `LINK_BOARD`, `HEADERS`)

**Design decision**: All components are in one file for simplicity. This is appropriate for a utility tool of this size. No application factory pattern is used.

---

### 3.2 Authentication Component

**Responsibility**: Controls who can access the application. Supports two identity providers.

**Sub-components**:

| Component             | Class/Function                                     | Description                                  |
| --------------------- | -------------------------------------------------- | -------------------------------------------- |
| User model            | `class User(UserMixin)`                            | Minimal Flask-Login user: `id`, `name`       |
| User loader           | `load_user(user_id)`                               | Resolves session user from `users.json`      |
| Local auth route      | `login()` at `POST /login`                         | Password-hash check via Werkzeug             |
| Monday OAuth init     | `monday_login()` at `GET /auth/monday`             | Authlib redirect                             |
| Monday OAuth callback | `monday_callback()` at `GET /auth/monday/callback` | Code exchange + JWT decode + upsert          |
| Signup route          | `signup()` at `POST /signup`                       | Creates hashed-password user in `users.json` |
| Logout route          | `logout()` at `GET /logout`                        | Calls `logout_user()`, redirects to login    |

**Interaction pattern**:

- Flask-Login uses server-side sessions (`session` cookie) to track the current user
- Monday.com OAuth tokens are stored in `session['monday_token']` post-callback
- `@login_required` is applied to all protected routes

---

### 3.3 Monday.com API Integration Component

**Responsibility**: All communication with Monday.com. Provides both read (fetch board items) and write (create items, upload files) operations.

**Sub-components**:

| Component            | Location                                                 | Description                                              |
| -------------------- | -------------------------------------------------------- | -------------------------------------------------------- |
| API constants        | Module-level globals                                     | `URL`, `FILE_URL`, `HEADERS`, `MAIN_BOARD`, `LINK_BOARD` |
| Column formatter     | `format_column_value(col_id, value)`                     | Maps col IDs to correct Monday.com JSON shapes           |
| Item creator         | Inside `submit()` route                                  | GraphQL `create_item` mutation                           |
| File uploader        | `upload_file_to_monday_bytes()`                          | Multipart GraphQL to `/v2/file`                          |
| Linked items fetcher | `index()` route                                          | Fetches items from linked board for dropdown             |
| Recent logs fetcher  | `index()` route                                          | Fetches last 10 items from main board                    |
| Search endpoint      | `search_linked_items()` at `GET /search_linked_items`    | AJAX search with server-side filter                      |
| Signature API route  | `api_upload_signature()` at `POST /api/upload_signature` | Bridges browser uploads to Monday file API               |

**Column ID mapping pattern**: All Monday.com column IDs are stored in environment variables prefixed `COL_` (e.g. `COL_EMAIL`, `COL_STATUS`). The `format_column_value()` function uses the resolved column ID string to infer the Monday.com column type.

---

### 3.4 User Store Component

**Responsibility**: Persistent storage of application user identities (both local and OAuth users).

**Implementation**: Flat JSON file at `users.json`.

**Schema** (per user record):

```json
{
  "username": "string (primary key)",
  "password": "werkzeug_hash | null (null for OAuth users)",
  "name": "string (optional)",
  "email": "string (optional)",
  "monday_id": "number (OAuth users only)",
  "monday_account_id": "number (OAuth users only)",
  "provider": "string (OAuth users: 'monday')"
}
```

**Access functions**:

- `_read_users()` — reads and JSON-parses file, returns `[]` on missing/corrupt file
- `_write_users(users)` — serialises and overwrites file with `indent=4`

**Limitation**: No file locking. Concurrent writes could corrupt the file. Acceptable for a single-user/small-team utility.

---

### 3.5 Frontend Component (Jinja2 Templates)

**Responsibility**: Server-rendered HTML with client-side JavaScript for rich interactivity.

**Templates**:

| Template      | Route            | Description                                           |
| ------------- | ---------------- | ----------------------------------------------------- |
| `login.html`  | `/login`         | Dual login: Monday.com OAuth button + local form      |
| `signup.html` | `/signup`        | Local account creation form                           |
| `index.html`  | `/`              | Main service entry form + sidebar with recent/pending |
| `error.html`  | (error handlers) | Generic error display                                 |

**Client-side modules in `index.html`** (inline JavaScript):

| Module                   | Technology            | Purpose                                         |
| ------------------------ | --------------------- | ----------------------------------------------- |
| IndexedDB layer          | Native Web API        | Stores signature blobs + draft metadata offline |
| Signature pad management | `signature_pad@4.0.0` | Canvas drawing, capture, clear, preview         |
| Form submission          | Fetch API             | AJAX submit → signature upload pipeline         |
| Draft persistence        | `localStorage`        | Form field save/restore across sessions         |
| Linked item search       | Select2 + AJAX        | Real-time search of Monday.com linked board     |
| Pending sync             | IndexedDB query       | Retry failed signature uploads                  |

---

### 3.6 Signature Storage Component

**Responsibility**: Persists captured signatures both temporarily (in-browser) and permanently (Monday.com column).

**Storage hierarchy**:

```
Canvas Drawing
    │ canvas.toBlob() → Blob
    ▼
sigBlobs{} (in-memory JS object)
    │ On successful form submit: fetch /api/upload_signature
    │ On upload failure: saveSignatureBlob() → IndexedDB
    ▼
IndexedDB: ServiceReportDB
    ├── objectStore: 'signatures'  (pending blobs + itemId)
    └── objectStore: 'drafts'      (currently unused, reserved)
    │ On "Sync Now": syncPending() → retry upload
    ▼
Monday.com File Column
    (permanent storage via add_file_to_column mutation)
```

**Column mapping** (`SIG_COLUMN_MAP`):

```python
{
    'sig_tsp':          os.getenv("COL_TSP_SIGNATURE"),
    'sig_customer':     os.getenv("COL_CUSTOMER_SIGNATURE"),
    'sig_biomed':       os.getenv("COL_BIOMED_SIGNATURE"),
    'sig_tsp_workwith': os.getenv("COL_TSP_WORKWITH_SIGNATURE"),
}
```

---

## 4. Architectural Layers and Dependencies

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Presentation                                      │
│  ─────────────────────                                      │
│  templates/*.html (Jinja2)                                  │
│  static/css/style.css (minimal overrides)                   │
│  CDN: Bootstrap 5, jQuery, Select2, SignaturePad            │
│               │                                             │
│               │ HTTP request/response                       │
│               ▼                                             │
│  Layer 2: Application / Routing                             │
│  ──────────────────────────────                             │
│  Flask route handlers in app.py                             │
│  Flask-Login (@login_required, login_user, current_user)    │
│  Request/response processing (form parsing, flash msgs)     │
│               │                                             │
│               │ function calls                              │
│               ▼                                             │
│  Layer 3: Business Logic / Formatting                       │
│  ────────────────────────────────────                       │
│  format_column_value()    — column type mapping             │
│  upload_file_to_monday_bytes() — file upload abstraction    │
│  _read_users() / _write_users() — user persistence          │
│  JWT decode logic (inline in monday_callback)               │
│               │                                             │
│               │ network calls                               │
│               ▼                                             │
│  Layer 4: External Services                                 │
│  ──────────────────────────                                 │
│  Monday.com GraphQL API                                     │
│  Monday.com OAuth 2.0                                       │
│  users.json (local filesystem)                              │
└─────────────────────────────────────────────────────────────┘
```

**Dependency rules**:

- Presentation layer MUST NOT call external services directly (all goes through Flask routes)
- Route handlers MAY call helper functions
- Route handlers MUST NOT depend on each other (no cross-route function calls)
- Helper functions MUST NOT import Flask `request`/`session` (they receive data as arguments)
  - Exception: `format_column_value` and `upload_file_to_monday_bytes` are pure helpers
  - `_read_users` and `_write_users` access the filesystem directly

**Circular dependencies**: None. The flat single-module architecture prevents circular imports by definition.

---

## 5. Data Architecture

### 5.1 Domain Model

The application has two data domains:

**Local Domain (users.json)**:

- `User` — Flask-Login identity carrier. Attributes: `id` (username), `name`.
- User records in `users.json` carry auth credentials and optional OAuth metadata.

**External Domain (Monday.com Boards)**:

- **Main Board** (`MAIN_BOARD_ID`) — Service log entries. Each item represents one completed service report.
- **Linked Board** (`LINKED_BOARD_ID`) — Service Requests. Existing records that service reports connect to.

### 5.2 Monday.com Board Relationship

```
Linked Board (Service Requests)          Main Board (Service Logs)
───────────────────────────────          ─────────────────────────
[Item: Service Request #12345]  ◄──────  COL_SERVICE_REQUEST (board relation)
  - Customer Name (mirrored) ──────────► Mirror column
  - Customer Email (mirrored) ─────────► Mirror column
  - BIOMED info (mirrored) ────────────► Mirror column
  - Serial Number (mirrored) ──────────► Mirror column
                                          COL_EMAIL (TSP email)
                                          COL_STATUS
                                          COL_SERVICE_START / END
                                          COL_LOGIN_DATE / LOGOUT_DATE
                                          COL_PROBLEMS
                                          COL_JOB_DONE
                                          COL_PARTS_REPLACED
                                          COL_RECOMMENDATION
                                          COL_REMARKS
                                          COL_TSP_WORKWITH
                                          COL_CREATED_BY
                                          COL_TSP_SIGNATURE (file)
                                          COL_CUSTOMER_SIGNATURE (file)
                                          COL_BIOMED_SIGNATURE (file)
                                          COL_TSP_WORKWITH_SIGNATURE (file)
```

### 5.3 Column Type Mapping (`format_column_value`)

The `format_column_value(col_id, value)` function infers the Monday.com column type from the column ID string and formats the value accordingly:

| Column ID Pattern                      | Monday.com Type  | Output Format                         |
| -------------------------------------- | ---------------- | ------------------------------------- |
| contains `text`, starts with `text_`   | Text / Long Text | `{"text": "..."}`                     |
| contains `email`                       | Email            | `{"email": "...", "text": "..."}`     |
| contains `datetime`                    | DateTime         | `"YYYY-MM-DD HH:mm:ss"` (string)      |
| contains `date`                        | Date             | `"YYYY-MM-DD"` (string)               |
| contains `status`                      | Status           | `{"index": int}`                      |
| contains `color`                       | Color/Status     | `{"index": int}`                      |
| contains `single_select`               | Dropdown         | `{"index": int}` or `{"text": "..."}` |
| contains `relation`                    | Board Relation   | `{"item_ids": [int]}`                 |
| contains `multiple_person` or `person` | People           | `{"personsIds": [int]}`               |
| contains `file` or `signature`         | File             | `None` (uploaded separately)          |
| (default)                              | Text             | `{"text": "..."}`                     |

### 5.4 Data Validation

Validation occurs at the form level (HTML5 `required` attributes) and at the route level:

- `submit()` validates `item_name` and `linked_item_id` are present
- `api_upload_signature()` validates `item_id`, `sig_key`, `file` are present; checks `file_data` size ≥ 100 bytes
- Monday.com API errors are caught and surfaced via flash messages or JSON error responses

---

## 6. Cross-Cutting Concerns

### 6.1 Authentication & Authorization

**Security model**: Session-based. Flask-Login tracks the authenticated user in a signed server-side session cookie.

**Permission enforcement**: The `@login_required` decorator is applied to:

- `GET /` (`index`)
- `POST /submit`
- `POST /api/upload_signature`
- `GET /search_linked_items`

Unauthenticated requests to protected routes redirect to `/login` (configured via `login_manager.login_view = 'login'`).

**Two authentication paths**:

| Path             | Mechanism                                          | User in users.json                     |
| ---------------- | -------------------------------------------------- | -------------------------------------- |
| Local            | Username + `werkzeug.security.check_password_hash` | `password` field set                   |
| Monday.com OAuth | OAuth 2.0 Authorization Code + JWT decode          | `provider: "monday"`, `password: null` |

**Legacy admin path**: The `login()` route has a fallback that checks `ADMIN_PASSWORD` env var directly. This exists for bootstrapping before any users are registered. This is a known technical debt item.

**Token storage**: Monday.com access tokens are stored in the Flask session (`session['monday_token']`), not in the database. They are not used for subsequent API calls in the current implementation (the app uses the service-level `MONDAY_API_KEY` for all API calls after login).

### 6.2 Error Handling & Resilience

**Pattern**: Broad exception handling at route boundaries with user-facing flash messages.

```
Route handler
  └── try:
        ... business logic ...
      except ValueError as e:   → flash("Invalid data format: ...")
      except TypeError as e:    → flash("Type error: ...")
      except Exception as e:    → flash("Unexpected error: ...")
```

**API error handling**: Monday.com GraphQL errors are checked via `res.get('errors')` on every response before processing `data`. Both flash-based (page redirect) and JSON (AJAX) error returns are supported via `X-Requested-With: XMLHttpRequest` header detection.

**Client-side offline resilience**:

- Signature upload failures → saved to IndexedDB with `status: 'pending'`
- "Sync Now" button retries all pending uploads
- Form draft → `localStorage` save/restore

**HTTP error handlers**:

```python
@app.errorhandler(404) → error.html "Page not found"
@app.errorhandler(500) → error.html "Internal server error"
@app.errorhandler(403) → error.html "Access forbidden"
```

### 6.3 Logging & Monitoring

**Strategy**: Console logging only (`print()` statements). No structured logging framework.

**Log prefixes used**:
| Prefix | Subsystem |
|--------|-----------|
| `[OAUTH]` | Monday.com OAuth flow |
| `[SUBMIT]` | Form submission |
| `[FORMAT]` | Column value formatting |
| `[SIGNATURE]` | File upload to Monday.com |
| `[API SIG]` | Signature API endpoint |
| `[DEBUG]` | General debug output |
| `[ERROR]` | Error conditions |
| `[SUCCESS]` | Successful operations |
| `[WARN]` | Warnings |

**Limitation**: All log output goes to stdout. In production, this should be redirected to a logging service. `sys.stdout.flush()` is called in the signature upload function to ensure log visibility.

### 6.4 Validation

**Input validation layers**:

1. **HTML5** — `required` attributes on critical form fields, `type="email"` on email inputs
2. **Server-side routes** — Explicit checks on required parameters before processing
3. **Type safety** — `format_column_value()` catches `ValueError`/`TypeError` per field; the calling route catches these globally

**File upload validation**:

- Minimum file size check (100 bytes) to reject empty canvas captures
- `sig_key` validated against `SIG_COLUMN_MAP` before processing

### 6.5 Configuration Management

**Strategy**: All configuration via environment variables loaded from `.env` at startup.

**Required environment variables**:

| Variable                     | Purpose                  | Criticality                  |
| ---------------------------- | ------------------------ | ---------------------------- |
| `SECRET_KEY`                 | Flask session signing    | Critical (warns if missing)  |
| `MONDAY_API_KEY`             | Monday.com service API   | Critical (errors if missing) |
| `MAIN_BOARD_ID`              | Primary board ID         | Critical                     |
| `LINKED_BOARD_ID`            | Linked board ID          | Critical                     |
| `MONDAY_OAUTH_CLIENT_ID`     | OAuth app client ID      | Required for Monday login    |
| `MONDAY_OAUTH_CLIENT_SECRET` | OAuth app secret         | Required for Monday login    |
| `ADMIN_PASSWORD`             | Legacy admin fallback    | Optional                     |
| `COL_*` (13+ variables)      | Board column ID mappings | Required for submissions     |

**Startup validation**: The app prints warnings/errors at startup for missing critical vars but does not exit. This means misconfigured deployments will start but fail at runtime. A stricter approach would raise `ValueError` at startup.

**Secret management**: Secrets are in `.env` which must be excluded from version control via `.gitignore`.

---

## 7. Service Communication Patterns

### 7.1 Monday.com GraphQL API

**Protocol**: HTTP POST to `https://api.monday.com/v2`

**Authentication**: Bearer token in `Authorization` header (`HEADERS = {"Authorization": API_KEY, "API-Version": "2023-10"}`)

**Request pattern** (synchronous, `requests.post()`):

```python
res = requests.post(URL, json={'query': graphql_query, 'variables': vars}, headers=HEADERS).json()
```

**GraphQL operations used**:

| Operation                                                                       | Type     | Purpose                  |
| ------------------------------------------------------------------------------- | -------- | ------------------------ |
| `boards(ids: $boardId) { items_page { items { id name } } }`                    | Query    | Fetch linked board items |
| `boards(ids: $boardId) { items_page(limit: 10) { items { name created_at } } }` | Query    | Fetch recent logs        |
| `create_item(board_id, item_name, column_values)`                               | Mutation | Create service entry     |
| `add_file_to_column(item_id, column_id, file)`                                  | Mutation | Upload signature file    |

**File upload endpoint**: `https://api.monday.com/v2/file` — uses multipart/form-data with the GraphQL mutation as a JSON-encoded `query` part and the file as `variables[file]`.

### 7.2 Monday.com OAuth 2.0

**Protocol**: Standard OAuth 2.0 Authorization Code flow via Authlib.

**Endpoints**:

- Authorize: `https://auth.monday.com/oauth2/authorize`
- Token: `https://auth.monday.com/oauth2/token`

**Token exchange**: Done manually with `requests.post()` (not via Authlib's built-in token exchange) due to the `client_secret_post` auth method requirement.

**User identity extraction**: JWT payload decoded via base64 — no signature verification is performed (the token was just received directly from Monday.com's auth server, so forgery risk is nil in this context).

### 7.3 Synchronous vs. Asynchronous

All backend-to-Monday.com calls are **synchronous** using the `requests` library. There is no async/background job infrastructure.

All browser-to-server calls for form submission and signature upload are **asynchronous** (Fetch API / AJAX), allowing the UI to remain responsive and report per-signature upload progress.

### 7.4 API Versioning

The Monday.com API version is pinned via the `API-Version: 2023-10` header on all requests. This prevents unexpected breaking changes from Monday.com API updates.

---

## 8. Python/Flask-Specific Patterns

### Application Structure

```
app.py                    ← Single-module application (no package structure)
requirements.txt          ← Pinned (or un-pinned) dependencies
.env                      ← Environment configuration (not in VCS)
users.json                ← Runtime user data file
templates/                ← Jinja2 templates
  login.html
  signup.html
  index.html
  error.html
static/
  css/style.css           ← Minimal stylesheet (currently empty)
  uploads/                ← Currently unused upload directory
signatures/               ← Text-format signature references (legacy/testing)
  2644790273_signatures.txt
```

### Flask Patterns Used

**Route decoration**: Standard `@app.route('/path', methods=['GET', 'POST'])` decorator pattern. No Blueprints are used — all routes are on the default app.

**Flash messaging**: `flash(message, category)` + `get_flashed_messages(with_categories=true)` in templates for user feedback.

**AJAX detection**: `request.headers.get('X-Requested-With') == 'XMLHttpRequest'` to return JSON vs. redirect depending on caller.

**Session usage**: `session['monday_token']`, `session['monday_user_id']`, `session['monday_account_id']` for OAuth post-login state.

**Template rendering**: `render_template('template.html', var1=val1, ...)` with named keyword arguments.

### Dependency Management

```
flask              ← WSGI framework
python-dotenv      ← .env loading
requests           ← HTTP client for Monday.com API
flask-login        ← Session-based authentication
```

Additional dependencies used in code but NOT listed in `requirements.txt` (gap):

- `authlib` — used for `OAuth`, `oauth.register()`
- `werkzeug` — used for `generate_password_hash`, `check_password_hash` (installed as Flask dependency)

> ⚠️ **Known gap**: `authlib` is imported but not in `requirements.txt`. Deployments will fail unless `authlib` is installed separately. This should be added.

---

## 9. Implementation Patterns

### Route Handler Pattern

```python
@app.route('/route', methods=['GET', 'POST'])
@login_required                          # ← authorization guard
def handler_name():
    if request.method == 'POST':
        # 1. Extract form data
        field = request.form.get('field_name')

        # 2. Validate required fields
        if not field:
            flash('Field is required', 'error')
            return redirect(url_for('handler_name'))

        # 3. Business logic
        try:
            result = do_work(field)
            flash('Success!', 'success')
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')

        return redirect(url_for('index'))

    # GET
    return render_template('template.html', data=data)
```

### AJAX Route Handler Pattern

```python
@app.route('/api/resource', methods=['POST'])
@login_required
def api_handler():
    try:
        param = request.form.get('param')
        if not param:
            return jsonify({'success': False, 'error': 'Missing param'}), 400

        result = do_work(param)
        return jsonify({'success': True, 'result': result})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
```

### Dual Response Pattern (HTML + AJAX from same route)

```python
is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

if success:
    if is_ajax:
        return jsonify({'success': True, 'item_id': item_id})
    else:
        flash('Success!', 'success')
        return redirect(url_for('index'))
else:
    if is_ajax:
        return jsonify({'success': False, 'error': 'message'})
    flash('Error message', 'error')
    return redirect(url_for('index'))
```

### Column Value Formatter Pattern

```python
def format_column_value(col_id, value):
    if not value or value == '':
        return None                         # ← always skip empty
    col_id_lower = str(col_id).lower()

    if 'type_keyword' in col_id_lower:
        return {"key": value}              # ← type-specific shape
    # ...
    else:
        return {"text": str(value).strip()} # ← safe default
```

### File Upload to Monday.com Pattern

```python
def upload_file_to_monday_bytes(item_id, column_id, file_data, filename):
    # 1. Write to temp file (requests needs file object)
    tmp_path = os.path.join(tempfile.gettempdir(), f"{item_id}_{filename}")
    with open(tmp_path, 'wb') as f: f.write(file_data)

    # 2. Build multipart query
    mutation = 'mutation ($file: File!) { add_file_to_column(...) }'
    query_json = json.dumps({"query": mutation})

    # 3. POST multipart
    with open(tmp_path, 'rb') as f:
        res = requests.post(FILE_URL, headers=AUTH_HEADERS,
            files={
                'query': (None, query_json, 'application/json'),
                'variables[file]': (filename, f, 'image/png'),
            }, timeout=30)

    # 4. Cleanup temp file
    try: os.remove(tmp_path)
    except: pass

    # 5. Parse and return (bool, result_or_error)
    ...
    return True, file_id   # or return False, error_message
```

---

## 10. Testing Architecture

Currently, there are no automated tests in the repository. The `SIGNATURE_TESTING_GUIDE.md` file provides manual testing guidance for the signature upload feature.

**Recommended test structure** (for future implementation):

| Test Type         | Scope                                                      | Tools                                          |
| ----------------- | ---------------------------------------------------------- | ---------------------------------------------- |
| Unit tests        | `format_column_value()`, `_read_users()`, JWT decode logic | `pytest`                                       |
| Route tests       | All Flask routes with mocked Monday.com API                | `pytest`, `Flask test client`, `unittest.mock` |
| Integration tests | End-to-end OAuth flow, real API calls                      | `pytest`, staging environment                  |
| E2E tests         | Browser form submission, signature capture                 | Playwright or Selenium                         |

**Test boundary patterns**:

- Mock `requests.post()` to simulate Monday.com API responses without network calls
- Use `app.test_client()` for route-level testing
- Use `tempfile.mkdtemp()` for isolated `users.json` testing
- Signature blob tests can use small synthetic PNG bytes

---

## 11. Deployment Architecture

### Runtime Requirements

- Python 3.x with dependencies from `requirements.txt` (+ `authlib`)
- `.env` file with all required environment variables
- Write access to `users.json` path
- Write access to `tempfile.gettempdir()` (for signature temp files)
- Network access to `api.monday.com` and `auth.monday.com`

### Local Development

```bash
# 1. Create virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate        # Unix

# 2. Install dependencies
pip install -r requirements.txt
pip install authlib              # Missing from requirements.txt

# 3. Configure .env
cp .env.example .env             # (create if not exists)
# Set: SECRET_KEY, MONDAY_API_KEY, MAIN_BOARD_ID, LINKED_BOARD_ID,
#      MONDAY_OAUTH_CLIENT_ID, MONDAY_OAUTH_CLIENT_SECRET,
#      COL_* column IDs

# 4. Run
flask run                        # or: python app.py
```

### Application Entry Point

The app is a standard WSGI app. The module-level `app` object is the WSGI callable. There is no `if __name__ == '__main__': app.run()` guard — Flask's default `flask run` command discovers the app via the `app` variable name.

### Environment-Specific Configuration

All environment differences are managed purely through the `.env` file. The application has no explicit `FLASK_ENV` / staging / production mode switching beyond the `SECRET_KEY` warning.

**Production security checklist**:

- [ ] Set a strong, random `SECRET_KEY`
- [ ] Remove `ADMIN_PASSWORD` or set a strong value
- [ ] Ensure `.env` is not committed to version control
- [ ] Run behind a reverse proxy (nginx/Caddy) with TLS
- [ ] Consider replacing `users.json` with a proper database for concurrent access safety
- [ ] Consider adding rate limiting on `/login` and `/signup`

---

## 12. Extension and Evolution Patterns

### Adding a New Form Field

1. **Add HTML input** in `templates/index.html` with a `name` attribute (e.g., `name="new_field"`)
2. **Add environment variable** in `.env`: `COL_NEW_FIELD=<monday_column_id>`
3. **Add to `form_data` dict** in `submit()`:
   ```python
   "COL_NEW_FIELD": request.form.get('new_field'),
   ```
4. **No changes needed** to `format_column_value()` if the column ID contains a recognisable keyword; otherwise add a new branch
5. **Test** the column ID naming to confirm correct type inference

### Adding a New Signature Pad

1. **Add to `SIG_PADS` array** in `index.html`:
   ```javascript
   { key: 'sig_new_role', label: 'New Role', col: 'col-md-6 col-lg-4' }
   ```
2. **Add environment variable**: `COL_NEW_ROLE_SIGNATURE=<column_id>`
3. **Add to `SIG_COLUMN_MAP`** in `app.py`:
   ```python
   'sig_new_role': os.getenv("COL_NEW_ROLE_SIGNATURE"),
   ```

### Adding a New Protected Route

```python
@app.route('/new-route')
@login_required
def new_route():
    ...
    return render_template('new_template.html', ...)
```

### Integrating a New External Service

Follow the pattern established for Monday.com:

1. Add credentials to `.env`
2. Initialise client at module level (after `load_dotenv()`)
3. Add a dedicated helper function for the external call (mirroring `upload_file_to_monday_bytes`)
4. Use that helper from route handlers

### Migrating from JSON to a Database

1. Replace `_read_users()` and `_write_users()` with SQLAlchemy (Flask-SQLAlchemy) equivalents
2. `User` model already extends `UserMixin` — add `db.Model` to it
3. Update `load_user()` to query the database
4. No changes needed to routes or templates

### Migrating to Flask Blueprints (if app grows)

**Current state**: All routes in a single `app.py` module.

**Blueprint decomposition** (recommended split):

```
app/
  __init__.py          ← application factory: create_app()
  auth/
    __init__.py
    routes.py          ← /login, /signup, /logout, /auth/monday, /auth/monday/callback
  main/
    __init__.py
    routes.py          ← /, /submit, /search_linked_items
  api/
    __init__.py
    routes.py          ← /api/upload_signature
  monday/
    client.py          ← format_column_value, upload_file_to_monday_bytes
  models/
    user.py            ← User class, _read_users, _write_users
```

---

## 13. Architectural Pattern Examples

### Example 1: Column Type-Aware Serialisation

The `format_column_value()` function implements the **Strategy** pattern implicitly — the column ID drives the formatting strategy:

```python
# Email column: Monday.com requires BOTH fields
elif 'email' in col_id_lower:
    result = {"email": value_str, "text": value_str}
    return result

# Datetime: convert "YYYY-MM-DDTHH:mm" → "YYYY-MM-DD HH:mm:ss"
elif 'datetime' in col_id_lower:
    if 'T' in value_str:
        date_part, time_part = value_str.split('T')
        if time_part.count(':') == 1:
            time_part = f"{time_part}:00"
        value_str = f"{date_part} {time_part}"
    return value_str    # string, not dict — Monday handles datetime as raw string
```

**Pattern insight**: The column ID naming convention on Monday.com is used as the type discriminator. This couples the formatting logic to board naming conventions. If column IDs don't follow the expected naming, values will fall through to the text default.

### Example 2: OAuth JWT Identity Extraction

```python
# Decode JWT payload (base64 — no signature verification needed
# as token was received directly from Monday.com's auth server)
parts = access_token.split('.')
payload = parts[1]
padding = 4 - len(payload) % 4
if padding != 4:
    payload += '=' * padding
decoded = base64.urlsafe_b64decode(payload)
token_claims = json.loads(decoded)

monday_user_id = token_claims.get('uid')
monday_account_id = token_claims.get('actid')
username = f"monday_{monday_user_id}"
```

**Pattern insight**: User identity is derived from the JWT payload rather than making an additional API call. This avoids extra latency and scope requirements. The fallback path (querying `{ me { id } }`) exists if JWT decode fails.

### Example 3: Client-Side Offline Signature Queue

```javascript
// On upload failure: persist to IndexedDB
async function saveSignatureBlob(sigKey, blob, itemId) {
  const tx = db.transaction("signatures", "readwrite");
  tx.objectStore("signatures").add({
    sigKey,
    blob,
    itemId,
    status: "pending",
    createdAt: new Date().toISOString(),
  });
}

// Retry: iterate pending records
async function syncPending() {
  const pending = await getPendingSignatures();
  for (const rec of pending) {
    const result = await uploadSignature(rec.sigKey, rec.blob, rec.itemId);
    if (result.success) {
      await deleteSignatureRecord(rec.id);
    }
  }
}
```

**Pattern insight**: This implements a **client-side outbox pattern**, providing resilience against network failures without requiring server-side queuing infrastructure.

---

## 14. Architectural Decision Records

### ADR-001: Monday.com as Primary Data Store

**Context**: The application is an internal tool for a team already using Monday.com as their primary work management platform.

**Decision**: Use Monday.com boards as the sole persistent store for service records. No local database.

**Rationale**:

- Eliminates need to manage a database (no setup, backups, migrations)
- Service logs are immediately visible in Monday.com's native UI
- Monday.com provides built-in board relations, mirror columns, and automations

**Consequences (+)**: No database infrastructure, data immediately accessible to non-technical staff in Monday.com.

**Consequences (-)**: Application is tightly coupled to Monday.com availability and API. Rate limits apply. All queries are network calls.

---

### ADR-002: Flat Single-File Architecture (app.py)

**Context**: The application is a focused utility tool with ~10 routes and ~900 lines of Python.

**Decision**: Keep all Python code in a single `app.py` file. No Blueprints, no package structure.

**Rationale**: The application is small enough that a single-file approach is maintainable. Adding Blueprint structure would add indirection without proportionate benefit.

**Consequences (+)**: Simple to read and navigate. Easy to deploy.

**Consequences (-)**: Will become unwieldy if the application grows significantly. Should migrate to Blueprints if it exceeds ~1500 lines.

---

### ADR-003: JSON Flat-File User Store

**Context**: User authentication must persist across restarts. The user base is small (internal team).

**Decision**: Store user records in `users.json` rather than a database.

**Rationale**: No database setup required. Monday.com OAuth means most users never use local passwords. The user count is tiny.

**Consequences (+)**: Zero infrastructure requirements for user storage.

**Consequences (-)**: Not safe for concurrent writes. No query capabilities. File corruption risk. Should migrate to SQLite or similar if user base grows.

---

### ADR-004: Browser-Side Offline Signature Queue (IndexedDB)

**Context**: Signature uploads to Monday.com can fail (network issues, API timeouts). A failed upload would lose the signature permanently if not retried.

**Decision**: Use IndexedDB to store failed signature blobs client-side with a manual "Sync Now" retry mechanism.

**Rationale**: Provides resilience without server-side job queuing infrastructure. Blobs stay in the browser that captured them, which is appropriate since signatures are drawn on specific devices.

**Consequences (+)**: No lost signatures due to transient network failures.

**Consequences (-)**: Pending signatures are tied to the specific browser/device. If the user clears browser storage, pending signatures are lost.

---

### ADR-005: Column ID-Inferred Type Formatting

**Context**: Monday.com's GraphQL API requires different JSON shapes for different column types. Board column IDs are set by the organisation's Monday.com admin.

**Decision**: Infer the column type from the column ID string (contains `email`, `datetime`, etc.) rather than querying the board schema at runtime.

**Rationale**: Avoids an additional API call per submission to fetch column metadata. Simple to implement.

**Consequences (+)**: No schema introspection overhead.

**Consequences (-)**: Column IDs must follow naming conventions (contain type keywords). If an admin names a status column `col_service_progress` without `status`, it will fall through to the text default and fail.

---

## 15. Architecture Governance

### Maintaining Architectural Consistency

**Currently**: No automated enforcement. The single `app.py` structure makes violations visually obvious.

**Recommended practices**:

1. All new routes must use `@login_required` unless explicitly public (login/signup/OAuth pages)
2. All new Monday.com API calls should check `res.get('errors')` before accessing `data`
3. All new form fields that map to Monday.com columns must go through `format_column_value()`
4. All environment-dependent values must use `os.getenv()` — never hardcode IDs or secrets
5. Sensitive values must not be logged (partial masking already demonstrated in OAuth logging)

**Automated checks to add** (future):

- `bandit` — Python security linter (detects hardcoded secrets, insecure practices)
- `flake8` or `ruff` — Code style enforcement
- Pre-commit hooks for secret scanning (`detect-secrets`)

---

## 16. Blueprint for New Development

### Development Workflow

#### Starting a New Feature

1. **Identify the data scope**: Does this require new Monday.com columns, a new board, or just new form fields on the existing board?
2. **Environment first**: Add required `COL_*` or other env vars to `.env` and document them
3. **Backend route**: Add the route to `app.py` following the route handler pattern
4. **Column formatting**: If new Monday.com columns are involved, verify `format_column_value()` handles them, or add a new branch
5. **Template**: Add/modify HTML in the appropriate template
6. **Test manually**: Follow the SIGNATURE_TESTING_GUIDE.md approach for similar features

#### Component Creation Sequence

```
1. .env variable(s)         ← define before writing code
2. Helper function(s)       ← pure utility, no HTTP context
3. Route handler(s)         ← uses helpers, manages request/response
4. Template update           ← HTML + optional client JS
5. Manual test               ← form submit, check Monday.com board
```

### Common Pitfalls

| Pitfall                                    | Symptom                                               | Prevention                                                                         |
| ------------------------------------------ | ----------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Column ID without type keyword             | Values sent as `{"text": "..."}` for non-text columns | Name columns with type keywords, or add explicit branch in `format_column_value()` |
| Missing `authlib` in requirements          | `ImportError` on fresh install                        | Add `authlib` to `requirements.txt`                                                |
| Forgetting `@login_required`               | Route accessible without auth                         | Always add decorator; test unauthenticated access                                  |
| Not checking `res.get('errors')`           | Silent failures when Monday.com rejects mutations     | Always check errors before accessing `data`                                        |
| Storing secrets in code                    | Security risk                                         | Always use `os.getenv()`                                                           |
| Concurrent users / `users.json` corruption | `JSONDecodeError` at login                            | Add file locking or migrate to SQLite                                              |
| Empty signature blob upload                | Monday.com returns error for tiny files               | Size check already implemented (`< 100 bytes`) — maintain this                     |
| Monday.com column ID as string vs. int     | GraphQL type errors                                   | Board IDs in mutations should be strings (`MAIN_BOARD` is used as-is from env)     |

### Implementation Templates

#### New Form Field → Monday.com Column

**1. Add to `index.html`:**

```html
<div class="mb-3">
  <label class="form-label">Field Label</label>
  <input type="text" name="new_field_name" class="form-control" />
</div>
```

**2. Add to `.env`:**

```
COL_NEW_FIELD=your_monday_column_id
```

**3. Add to `form_data` dict in `submit()`:**

```python
"COL_NEW_FIELD": request.form.get('new_field_name'),
```

#### New AJAX API Endpoint

```python
@app.route('/api/new-action', methods=['POST'])
@login_required
def api_new_action():
    try:
        param = request.form.get('param')
        if not param:
            return jsonify({'success': False, 'error': 'Missing param'}), 400
        # ... logic ...
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        print(f"[API NEW_ACTION] ERROR: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
```

#### New Monday.com GraphQL Query Call

```python
query = f'{{ boards (ids: {BOARD_ID}) {{ items_page {{ items {{ id name }} }} }} }}'
res = requests.post(URL, json={'query': query}, headers=HEADERS).json()

if res.get('errors'):
    error_msg = res['errors'][0].get('message', 'Unknown error')
    flash(f"API Error: {error_msg}", 'error')
    return redirect(url_for('index'))

if res.get('data') and res['data'].get('boards'):
    items = res['data']['boards'][0].get('items_page', {}).get('items', [])
```

---

## Appendix: Route Map

| Method   | Path                    | Auth     | Handler                  | Response Type |
| -------- | ----------------------- | -------- | ------------------------ | ------------- |
| GET/POST | `/signup`               | Public   | `signup()`               | HTML          |
| GET/POST | `/login`                | Public   | `login()`                | HTML          |
| GET      | `/auth/monday`          | Public   | `monday_login()`         | Redirect      |
| GET      | `/auth/monday/callback` | Public   | `monday_callback()`      | Redirect      |
| GET      | `/`                     | Required | `index()`                | HTML          |
| POST     | `/submit`               | Required | `submit()`               | HTML or JSON  |
| POST     | `/api/upload_signature` | Required | `api_upload_signature()` | JSON          |
| GET      | `/search_linked_items`  | Required | `search_linked_items()`  | JSON          |
| GET      | `/logout`               | Public   | `logout()`               | Redirect      |
| —        | `404`                   | —        | `not_found()`            | HTML          |
| —        | `500`                   | —        | `internal_error()`       | HTML          |
| —        | `403`                   | —        | `forbidden()`            | HTML          |

---

## Appendix: Environment Variable Reference

| Variable                     | Required | Default                                 | Description                                   |
| ---------------------------- | -------- | --------------------------------------- | --------------------------------------------- |
| `SECRET_KEY`                 | Yes      | `"dev-secret-key-change-in-production"` | Flask session signing key                     |
| `MONDAY_API_KEY`             | Yes      | —                                       | Monday.com service account API key            |
| `MAIN_BOARD_ID`              | Yes      | —                                       | Monday.com main board ID (service logs)       |
| `LINKED_BOARD_ID`            | Yes      | —                                       | Monday.com linked board ID (service requests) |
| `MONDAY_OAUTH_CLIENT_ID`     | OAuth    | —                                       | Monday.com app Client ID                      |
| `MONDAY_OAUTH_CLIENT_SECRET` | OAuth    | —                                       | Monday.com app Client Secret                  |
| `ADMIN_PASSWORD`             | Legacy   | —                                       | Legacy admin password fallback                |
| `COL_SERVICE_REQUEST`        | Yes      | —                                       | Board relation column ID                      |
| `COL_EMAIL`                  | Yes      | —                                       | TSP email column ID                           |
| `COL_SERVICE_START`          | Yes      | —                                       | Service start datetime column ID              |
| `COL_SERVICE_END`            | Yes      | —                                       | Service end datetime column ID                |
| `COL_LOGIN_DATE`             | Yes      | —                                       | Login datetime column ID                      |
| `COL_LOGOUT_DATE`            | Yes      | —                                       | Logout datetime column ID                     |
| `COL_PROBLEMS`               | Yes      | —                                       | Problems/concerns column ID                   |
| `COL_JOB_DONE`               | Yes      | —                                       | Job done column ID                            |
| `COL_PARTS_REPLACED`         | Yes      | —                                       | Parts replaced column ID                      |
| `COL_RECOMMENDATION`         | Yes      | —                                       | Recommendation column ID                      |
| `COL_REMARKS`                | Yes      | —                                       | Remarks column ID                             |
| `COL_STATUS`                 | Yes      | —                                       | Status column ID                              |
| `COL_TSP_WORKWITH`           | Yes      | —                                       | TSP workwith (person) column ID               |
| `COL_CREATED_BY`             | Optional | —                                       | Created-by tracking column ID                 |
| `COL_TSP_SIGNATURE`          | Yes      | —                                       | TSP signature file column ID                  |
| `COL_CUSTOMER_SIGNATURE`     | Yes      | —                                       | Customer signature file column ID             |
| `COL_BIOMED_SIGNATURE`       | Yes      | —                                       | BIOMED signature file column ID               |
| `COL_TSP_WORKWITH_SIGNATURE` | Yes      | —                                       | TSP workwith signature file column ID         |

---

_This blueprint was generated on April 4, 2026 based on the actual codebase state. It should be updated whenever:_

- _New routes or helper functions are added_
- _Monday.com board structure is changed (new boards, columns, or column IDs renamed)_
- _Authentication mechanism changes_
- _The application is restructured (e.g., migrated to Blueprints)_
- _New dependencies are introduced_
