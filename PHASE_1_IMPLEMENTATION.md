# Phase 1: Offline-First Implementation (Week 1)

## Goal

Users can fill forms + capture signatures **completely offline**, with "saved locally" indicator. No sync yet (Phase 2).

---

## Step 1: Create IndexedDB Wrapper

Create `frontend/src/db.js`:

```javascript
/**
 * IndexedDB wrapper for offline submissions.
 * Stores form data + signature blobs locally.
 */

const DB_NAME = "ServiceReportDB";
const DB_VERSION = 1;
const STORE_SUBMISSIONS = "submissions";

let dbInstance = null;

export async function initDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);

    req.onerror = () => reject(new Error("Failed to open IndexedDB"));
    req.onsuccess = () => {
      dbInstance = req.result;
      console.log("[DB] IndexedDB initialized");
      resolve(dbInstance);
    };

    req.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(STORE_SUBMISSIONS)) {
        const store = db.createObjectStore(STORE_SUBMISSIONS, {
          keyPath: "id",
        });
        store.createIndex("status", "status", { unique: false });
        store.createIndex("timestamp", "timestamp", { unique: false });
        console.log("[DB] Object store created");
      }
    };
  });
}

export async function saveSubmission(submission) {
  if (!dbInstance) await initDB();
  return new Promise((resolve, reject) => {
    const tx = dbInstance.transaction([STORE_SUBMISSIONS], "readwrite");
    const store = tx.objectStore(STORE_SUBMISSIONS);
    const req = store.add(submission);

    req.onerror = () => reject(new Error("Failed to save submission"));
    req.onsuccess = () => {
      console.log("[DB] Submission saved:", req.result);
      resolve(req.result);
    };
  });
}

export async function getSubmission(id) {
  if (!dbInstance) await initDB();
  return new Promise((resolve, reject) => {
    const tx = dbInstance.transaction([STORE_SUBMISSIONS], "readonly");
    const store = tx.objectStore(STORE_SUBMISSIONS);
    const req = store.get(id);

    req.onerror = () => reject(new Error("Failed to get submission"));
    req.onsuccess = () => resolve(req.result);
  });
}

export async function getSubmissionsByStatus(status) {
  if (!dbInstance) await initDB();
  return new Promise((resolve, reject) => {
    const tx = dbInstance.transaction([STORE_SUBMISSIONS], "readonly");
    const store = tx.objectStore(STORE_SUBMISSIONS);
    const index = store.index("status");
    const req = index.getAll(status);

    req.onerror = () => reject(new Error("Failed to query submissions"));
    req.onsuccess = () => resolve(req.result);
  });
}

export async function getAllSubmissions() {
  if (!dbInstance) await initDB();
  return new Promise((resolve, reject) => {
    const tx = dbInstance.transaction([STORE_SUBMISSIONS], "readonly");
    const store = tx.objectStore(STORE_SUBMISSIONS);
    const req = store.getAll();

    req.onerror = () => reject(new Error("Failed to get submissions"));
    req.onsuccess = () => resolve(req.result);
  });
}

export async function updateSubmission(id, updates) {
  if (!dbInstance) await initDB();
  const existing = await getSubmission(id);
  if (!existing) throw new Error("Submission not found");

  const updated = { ...existing, ...updates };
  return new Promise((resolve, reject) => {
    const tx = dbInstance.transaction([STORE_SUBMISSIONS], "readwrite");
    const store = tx.objectStore(STORE_SUBMISSIONS);
    const req = store.put(updated);

    req.onerror = () => reject(new Error("Failed to update submission"));
    req.onsuccess = () => resolve(req.result);
  });
}

export async function deleteSubmission(id) {
  if (!dbInstance) await initDB();
  return new Promise((resolve, reject) => {
    const tx = dbInstance.transaction([STORE_SUBMISSIONS], "readwrite");
    const store = tx.objectStore(STORE_SUBMISSIONS);
    const req = store.delete(id);

    req.onerror = () => reject(new Error("Failed to delete submission"));
    req.onsuccess = () => resolve(true);
  });
}
```

---

## Step 2: Create Offline-First Submit Handler

Modify `frontend/src/main.js` `handleSubmit()` function:

```javascript
async function handleSubmit(e) {
  e.preventDefault();

  const form = document.getElementById("mainForm");
  const btn = document.getElementById("submitBtn");
  const statusDiv = document.getElementById("uploadStatus");

  btn.disabled = true;
  btn.textContent = "Saving…";
  statusDiv.style.display = "block";
  statusDiv.className = "upload-status bg-info-subtle text-info";
  statusDiv.textContent = "Saving form locally…";

  try {
    // Initialize IndexedDB
    await initDB();

    // Auto-capture any unsaved signature drawings
    for (const cfg of SIG_PADS) {
      const pad = pads[cfg.key];
      if (pad && !pad.isEmpty() && !sigBlobs[cfg.key]) {
        const canvas = document.getElementById(`canvas-${cfg.key}`);
        const blob = await new Promise((resolve) =>
          canvas.toBlob(resolve, "image/png"),
        );
        if (blob) sigBlobs[cfg.key] = blob;
      }
    }

    // Collect form data
    const form = document.getElementById("mainForm");
    const formData = new FormData(form);

    // Sync Select2 values (for people picker)
    if (window.$ && window.$.fn.select2) {
      const peopleEl = window.$("#field-workwith");
      if (peopleEl.length) {
        formData.delete("tsp_workwith");
        const selected = peopleEl.select2("data") || [];
        for (const item of selected) {
          if (item.id) formData.append("tsp_workwith", item.id);
        }
      }
    }

    // Build submission object
    const submissionId = crypto.randomUUID();
    const submission = {
      id: submissionId,
      timestamp: Date.now(),
      status: "local", // Will be "local", "syncing", "synced", or "error"
      offline: true,
      formData: Object.fromEntries(formData),
      signatures: {
        sig_customer: sigBlobs.sig_customer || null,
        sig_tsp: sigBlobs.sig_tsp || null,
        sig_tsp_workwith: sigBlobs.sig_tsp_workwith || null,
      },
      monday_item_id: null,
      sync_attempts: 0,
      last_sync_error: null,
      synced_at: null,
    };

    // Save to IndexedDB
    await saveSubmission(submission);

    // Show success with "pending sync" status
    statusDiv.className = "upload-status bg-success-subtle text-success";
    statusDiv.innerHTML = `
      <div>
        ✓ <strong>Saved locally</strong>
        <br/>
        <small>This will sync to Monday.com when internet is available.</small>
        <br/>
        <small style="color: #666;">ID: ${submissionId}</small>
      </div>
    `;

    // Clear form
    form.reset();
    sigBlobs = {
      sig_customer: null,
      sig_tsp: null,
      sig_tsp_workwith: null,
    };
    for (const cfg of SIG_PADS) {
      if (pads[cfg.key]) pads[cfg.key].clear();
    }

    // Reset button
    btn.disabled = false;
    btn.textContent = "Submit";

    // Hide status after 5 seconds
    setTimeout(() => {
      statusDiv.style.display = "none";
    }, 5000);
  } catch (error) {
    console.error("[SUBMIT] Error:", error);
    statusDiv.className = "upload-status bg-danger-subtle text-danger";
    statusDiv.textContent = `Error: ${error.message}`;
    btn.disabled = false;
    btn.textContent = "Submit";
  }
}
```

**Update imports in `main.js`:**

```javascript
import { initDB, saveSubmission, getSubmissionsByStatus } from "./db.js";
```

---

## Step 3: Add DB Initialization on Page Load

In `main.js` initialization (run on page load):

```javascript
// Initialize IndexedDB when page loads
document.addEventListener("DOMContentLoaded", async () => {
  try {
    await initDB();
    console.log("[APP] Offline storage ready");
  } catch (err) {
    console.error("[APP] failed to init offline DB:", err);
  }

  // Rest of initialization...
  // initSelect2();
  // buildSignaturePads();
  // loadDraft();
});
```

---

## Step 4: Update Submission Display

Add a "My Submissions" section to show locally-stored items.

Modify `app/templates/index.html`:

Add this HTML after the form section:

```html
<!-- 8 · Submissions -->
<div class="form-card">
  <div class="form-card-header">
    <div class="section-icon" aria-hidden="true">8</div>
    <h6>My Submissions</h6>
  </div>
  <div class="form-card-body">
    <div id="submissionsList" style="max-height: 400px; overflow-y: auto;">
      <p class="text-muted">No submissions yet.</p>
    </div>
  </div>
</div>
```

Add to `frontend/src/main.js`:

```javascript
async function refreshSubmissionsList() {
  try {
    const submissions = await getAllSubmissions();
    const container = document.getElementById("submissionsList");

    if (submissions.length === 0) {
      container.innerHTML = '<p class="text-muted">No submissions yet.</p>';
      return;
    }

    let html = '<div class="list-group">';
    for (const sub of submissions.sort((a, b) => b.timestamp - a.timestamp)) {
      const date = new Date(sub.timestamp).toLocaleString();
      const itemName = sub.formData.name || `Item ${sub.id.slice(0, 8)}`;
      const statusBadge =
        sub.status === "synced"
          ? '<span class="badge bg-success">✓ Synced</span>'
          : sub.status === "syncing"
            ? '<span class="badge bg-warning">⏳ Syncing</span>'
            : sub.status === "error"
              ? '<span class="badge bg-danger">✗ Error</span>'
              : '<span class="badge bg-info">💾 Local</span>';

      html += `
        <div class="list-group-item">
          <div class="d-flex w-100 justify-content-between">
            <h6>${itemName}</h6>
            ${statusBadge}
          </div>
          <small class="text-muted">${date}</small>
          ${sub.monday_item_id ? `<br/><small>Monday ID: ${sub.monday_item_id}</small>` : ""}
          ${sub.last_sync_error ? `<br/><small class="text-danger">Error: ${sub.last_sync_error}</small>` : ""}
        </div>
      `;
    }
    html += "</div>";
    container.innerHTML = html;
  } catch (err) {
    console.error("[SUBMISSIONS] Error loading:", err);
  }
}

// Refresh on page load
document.addEventListener("DOMContentLoaded", () => {
  refreshSubmissionsList();
  setInterval(refreshSubmissionsList, 10000); // Refresh every 10s
});
```

---

## Step 5: Add Blob Storage for Signatures

Modify `frontend/src/signatures.js` to store blobs in IndexedDB alongside form data.

Currently, the `sigBlobs` object stores blobs in memory. They'll now be persisted with the submission in Step 2.

No changes needed here — the `saveSubmission()` call in `handleSubmit()` already stores the signature blobs.

---

## Step 6: Rebuild Frontend

```powershell
cd "C:\Users\MCBTSI\Documents\MONDAY.COM\Web\service_report_app\frontend"
npm run build
```

---

## Testing Phase 1

### Test 1: Offline Submit

1. Open DevTools → Network → Select "Offline"
2. Fill form, capture signatures
3. Click "Submit"
4. **Expected:** "✓ Saved locally" message
5. Open DevTools → Application → IndexedDB → ServiceReportDB → submissions
6. **Expected:** New row with your submission data

### Test 2: Persistence

1. With form saved locally
2. Close browser completely
3. Reopen tab
4. Open DevTools → Application → IndexedDB
5. **Expected:** Submission still there

### Test 3: Multiple Submissions

1. Submit 5 different forms offline
2. Check "My Submissions" tab
3. **Expected:** All 5 listed with "💾 Local" badge

### Test 4: Online (No Sync Yet)

1. Go back Online
2. Submissions should still show "💾 Local"
3. **Expected:** No auto-sync yet (that's Phase 2)

---

## What's NOT Done Yet (Phase 2+)

- ❌ Auto-sync when online
- ❌ Manual "Sync All" button
- ❌ Service Worker background sync
- ❌ Retry on network error
- ❌ Backup/export

---

## Code Files to Create/Modify

| File                       | Action              | Lines                  |
| -------------------------- | ------------------- | ---------------------- |
| `frontend/src/db.js`       | **CREATE**          | ~120                   |
| `frontend/src/main.js`     | **MODIFY**          | handleSubmit() + init  |
| `app/templates/index.html` | **ADD**             | My Submissions section |
| `Dockerfile`               | (unchanged for now) | -                      |

---

## Deployment Notes

Phase 1 is **production-ready as-is**. Users can use offline in areas with spotty connectivity, but sync to Monday.com will still require internet (manual for now in Phase 1).

For production deployment, users should see:

- "💾 Saved locally" messages when offline
- Data persists in browser storage
- No data loss on browser close/crash
- Ready for Phase 2 sync implementation
