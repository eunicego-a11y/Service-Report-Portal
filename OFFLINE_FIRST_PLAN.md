# Offline-First Architecture Plan

## Current State (Server-First)

✗ Requires internet to submit forms  
✗ Signatures uploaded immediately to Monday.com  
✗ All data depends on API connectivity  
✗ No local storage of drafts

## Target State (Offline-First)

✓ Full functionality without internet  
✓ Signatures captured & stored locally  
✓ Form data persisted in browser  
✓ Automatic sync when internet returns  
✓ Conflict resolution for dual edits  
✓ Sync queue UI showing pending items

---

## Architecture Overview

### Local Storage Stack

```
Browser Storage Hierarchy:
├── IndexedDB (Structured data - forms, submissions)
│   ├── submissions (form data + metadata)
│   ├── pending_syncs (queued Monday.com operations)
│   └── sync_log (history of sync attempts)
├── Blob Storage (Signatures - canvas PNGs)
│   ├── sig_customer.png
│   ├── sig_tsp.png
│   └── sig_tsp_workwith.png
├── localStorage (Drafts + app state)
│   ├── "form_draft_*" (auto-saves while editing)
│   └── "app_settings" (user preferences)
└── Service Worker (Background sync)
    ├── Cache API (offline pages)
    └── Background Sync API (queue retry)
```

### Data Flow

**OFFLINE MODE:**

```
User fills form + captures signatures
        ↓
[Browser]
  ├→ IndexedDB: Save submission_id=UUID
  ├→ Blob Store: Save sig_customer.png, sig_tsp.png
  ├→ localStorage: Save form_draft
  └→ UI: "✓ Saved locally (pending sync)"
```

**ONLINE MODE (Automatic):**

```
Service Worker detects connectivity
        ↓
Fetch pending submissions from IndexedDB
        ↓
For each pending submission:
  1. Create item on Monday.com
  2. Upload signatures
  3. Mark as synced
  4. Show "✓ Synced" badge
        ↓
Clear old drafts (30+ days)
```

**USER MANUALLY SYNCS (Fallback):**

```
User clicks "Sync Now"
        ↓
Trigger background sync
        ↓
Show progress: "Syncing 3 items..."
        ↓
Mark completed ones ✓
        ↓
Show any errors (retry available)
```

---

## Implementation Phases

### Phase 1: IndexedDB + Local Signatures (Week 1)

**Goal:** Store everything locally, no sync yet

**Changes:**

1. **Create `frontend/src/db.js`** — IndexedDB wrapper

   ```javascript
   // Store submission with all fields + signatures
   await submitDb.add({
     id: crypto.getRandomUUID(),
     timestamp: Date.now(),
     formData: {...},
     signatures: {
       sig_customer: blob,
       sig_tsp: blob,
       sig_tsp_workwith: blob
     },
     status: "local", // "local" | "syncing" | "synced" | "error"
     error: null,
     syncAttempts: 0
   })
   ```

2. **Create `frontend/src/offline-sync.js`** — Sync manager

   ```javascript
   async function submitFormOffline(formData, signatures) {
     const submission = {
       id: generateUUID(),
       timestamp: Date.now(),
       offline: true,
       formData,
       signatures,
       status: "local",
     };
     await submitDb.add(submission);
     return { success: true, id: submission.id, offline: true };
   }
   ```

3. **Modify `main.js` submit handler:**
   - Check navigator.onLine
   - If offline → store locally + show "Stored locally"
   - If online → still store locally first, then sync immediately

4. **Add UI indicators:**
   - ✓ (green) = synced to Monday.com
   - ⏳ (yellow) = stored locally, waiting to sync
   - ✗ (red) = sync error, retry available

### Phase 2: Service Worker + Background Sync (Week 2)

**Goal:** Auto-sync when connectivity returns

**Changes:**

1. **Create `frontend/public/sw.js`** — Service Worker

   ```javascript
   // Listen for online event
   self.addEventListener("online", () => {
     console.log("[SW] Online - triggering sync");
     self.registration.sync.register("sync-submissions");
   });

   // Handle sync
   self.addEventListener("sync", (event) => {
     if (event.tag === "sync-submissions") {
       event.waitUntil(syncPendingSubmissions());
     }
   });
   ```

2. **Register SW in main.js:**

   ```javascript
   if ("serviceWorker" in navigator) {
     navigator.serviceWorker.register("/static/dist/sw.js");
   }
   ```

3. **Create sync endpoint** (`app/blueprints/api.py`):
   ```python
   @api_bp.route("/api/sync", methods=["POST"])
   def sync_submission():
       """Sync a locally-stored submission to Monday.com"""
       submission_id = request.json.get("id")
       form_data = request.json.get("form_data")
       signature_urls = request.json.get("signatures")

       # Create Monday item
       item_id = create_monday_item(form_data)

       # Upload signatures for that item
       for sig_name, url in signature_urls.items():
           download_and_upload_signature(sig_name, url, item_id)

       return { "success": true, "item_id": item_id }
   ```

### Phase 3: Sync Queue UI (Week 3)

**Goal:** Show pending syncs, manual retry, conflict resolution

**Changes:**

1. **Add Sync Dashboard tab:**

   ```
   ┌─────────────────────────────────────┐
   │ Pending Syncs                       │
   ├─────────────────────────────────────┤
   │ ⏳ SR-04603 (3 hours ago)          │ [Retry] [Delete]
   │ ✓ SR-04602 (synced 2 hours ago)    │
   │ ✗ SR-04601 (error: network)        │ [Retry] [Details]
   ├─────────────────────────────────────┤
   │ [Sync All] [Clear Old] [Settings] │
   └─────────────────────────────────────┘
   ```

2. **Create `frontend/src/sync-ui.js`:**

   ```javascript
   async function renderSyncQueue() {
     const pending = await submitDb
       .where("status")
       .anyOf(["local", "syncing", "error"])
       .toArray();

     pending.forEach((sub) => {
       addSyncQueueRow(sub);
     });
   }

   async function syncAll() {
     const items = await submitDb.where("status").equals("local").toArray();
     for (const item of items) {
       await syncSubmission(item.id);
     }
   }
   ```

3. **Add new template `templates/sync-status.html`:**
   - Shows pending items
   - Retry buttons
   - Delete local copies
   - Manual sync trigger

---

## Storage Limits & Cleanup

| Storage                  | Limit    | Cleanup Strategy                   |
| ------------------------ | -------- | ---------------------------------- |
| **IndexedDB**            | 50-250MB | Keep 30 days of history            |
| **Blob (Signatures)**    | 10-50MB  | Reference-count, cleanup on delete |
| **localStorage**         | 5-10MB   | Auto-expire drafts after 7 days    |
| **Service Worker Cache** | 50MB     | HTML, CSS, JS only (no data)       |

**Cleanup Cron (daily):**

- Delete synced submissions > 30 days old
- Delete failed syncs > 7 days old (ask user first)
- Clear old signature blobs

---

## Data Format (JSON)

### Submission Object (IndexedDB)

```javascript
{
  "id": "550e8400-e29b-41d4-a716-446655440000",  // UUID
  "timestamp": 1712346600000,
  "status": "local",  // "local" | "syncing" | "synced" | "error"
  "offline": true,

  // Form data mirror
  "formData": {
    "name": "SR-04603",
    "linked_item_id": "2032305313",
    "email": "tech@example.com",
    "service_start": "2026-04-05T08:00",
    "problems": "Unit not powering on",
    "status": "5",
    "machine_system": "1",
    // ... all columns
  },

  // Signature references (at IndexedDB refs)
  "signatures": {
    "sig_customer": "data:image/png;base64,...",  // or blob URL
    "sig_tsp": "data:image/png;base64,...",
    "sig_tsp_workwith": "data:image/png;base64,..."
  },

  // Sync metadata
  "monday_item_id": null,       // Set after sync
  "sync_attempts": 0,
  "last_sync_error": null,      // "network" | "401" | "invalid_data" | null
  "synced_at": null,

  // Conflict detection
  "local_version": 1,           // Increment on local edit
  "remote_version": 0
}
```

### Pending Sync Operation

```javascript
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "submission_id": "550e8400-e29b-41d4-a716-446655440000",
  "operation": "create_item",
  "payload": { /* formData */ },
  "status": "pending",  // "pending" | "in_progress" | "success" | "failed"
  "retry_count": 0,
  "max_retries": 3,
  "created_at": 1712346600000,
  "last_retry_at": null,
  "error": null
}
```

---

## API Changes

### New Endpoints Needed

**POST `/api/sync-submit` (NEW)**

```json
// Request
{
  "id": "uuid",
  "form_data": {...},
  "signatures": {
    "sig_customer": "data:image/png;base64,...",
    "sig_tsp": "data:image/png;base64,..."
  }
}

// Response
{
  "success": true,
  "item_id": "2650xxxxxx",
  "synced_at": "2026-04-05T10:30:00Z"
}
```

**GET `/api/pending-syncs` (NEW)**

```json
// Response
{
  "pending": [
    {
      "id": "uuid",
      "status": "local",
      "timestamp": 1712346600000,
      "error": null
    }
  ]
}
```

**DELETE `/api/submission/{id}` (NEW - local deletion)**

```json
// Delete local copy (before/after sync)
{ "success": true, "deleted": "uuid" }
```

---

## UI Changes

### Before

```
□ Service Start     │ □ Status    │ □ Machine System
○ Form field        │ ○ Dropdown  │ ○ Dropdown
        ↓ Submit ↓
    [Submit to Monday.com]
    "Creating item on Monday.com..."
    → SUCCESS or ERROR (requires internet)
```

### After

```
□ Service Start     │ □ Status    │ □ Machine System
○ Form field        │ ○ Dropdown  │ ○ Dropdown
        ↓ Submit ↓
    [Submit]  [Sync Status ⏳ 2 pending]
    "✓ Saved locally (ready to sync)"
        ↓ (if online, auto-syncs) ↓
    "✓ Synced to Monday.com (ID: 265xxxx)"
```

### New Tab: "Sync Center"

```
Status: 🟢 ONLINE  [Manual Sync]  [Settings]

📋 Pending Submissions (2)
├─ SR-04603  ⏳ Local (3h ago)     [Retry] [Delete]
├─ SR-04602  ✓ Synced (2h ago)    [View]
├─ SR-04601  ✗ Error: Network     [Retry] [Delete]

[Load More] [Clear Synced] [Export]
```

---

## Browser Compatibility

| Feature             | IE11 | Edge 18 | Chrome | Firefox | Safari |
| ------------------- | ---- | ------- | ------ | ------- | ------ |
| IndexedDB           | ✓    | ✓       | ✓      | ✓       | ✓      |
| Service Worker      | ✗    | ✓       | ✓      | ✓       | ✓      |
| Background Sync     | ✗    | ?       | ✓      | ✗       | ✓      |
| Blob Storage        | ✓    | ✓       | ✓      | ✓       | ✓      |
| Canvas (signatures) | ✓    | ✓       | ✓      | ✓       | ✓      |

**Fallback for older browsers:** Auto-sync on online event (works in IE11)

---

## Security Considerations

1. **No secrets in IndexedDB** — API keys stay server-side
2. **Blob URLs are temporary** — Expire after session
3. **IndexedDB is per-origin** — Can't access data from other domains
4. **Signature blobs are user data** — Never transmitted until sync
5. **Sync validation** — Server validates form_data before creating item

---

## Implementation Checklist

- [ ] Phase 1: IndexedDB + Local Storage
  - [ ] Create `db.js` (IndexedDB wrapper)
  - [ ] Create `offline-sync.js` (submit local)
  - [ ] Modify `main.js` (offline-first flow)
  - [ ] Add UI indicators (✓ ⏳ ✗)
  - [ ] Test offline form submission + signature capture

- [ ] Phase 2: Service Worker + Auto-Sync
  - [ ] Create `sw.js` (service worker)
  - [ ] Register SW in main.js
  - [ ] Create `/api/sync-submit` endpoint
  - [ ] Handle background sync retry

- [ ] Phase 3: Sync UI
  - [ ] Create sync status dashboard
  - [ ] Manual retry/delete controls
  - [ ] Export pending submissions
  - [ ] Cleanup old synced items

---

## Testing Strategy

### Offline Testing

1. Open DevTools → Network → Offline
2. Fill form, capture signatures
3. Submit → Should store locally
4. Check IndexedDB in DevTools → Storage
5. Go online → Auto-sync or click retry

### Conflict Testing

1. Edit form offline
2. Go online → Sync
3. Edit same item on Monday.com
4. Compare versions → Log conflict

### Data Persistence

1. Submit offline
2. Close browser
3. Reopen → Data still there
4. Go online → Sync should work

---

## Risks & Mitigations

| Risk                     | Impact                     | Mitigation                          |
| ------------------------ | -------------------------- | ----------------------------------- |
| IndexedDB quota exceeded | Can't save new submissions | Show warning at 80% quota           |
| Browser data cleared     | Lost offline data          | Recommend export before update      |
| Sync retry storms        | Battery drain              | Exponential backoff (5s→30s→5m)     |
| Monday API changes       | Sync breaks                | Pin API version, monitor errors     |
| Duplicate submissions    | Data inconsistency         | Check `monday_item_id` before retry |
