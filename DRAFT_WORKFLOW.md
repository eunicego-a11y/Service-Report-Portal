# Draft & Submission Workflow (Clarified)

## Data Model

```
DRAFT (In Progress - Not Yet Submitted)
├─ id: UUID
├─ status: "draft"
├─ formData: {name: "", email: "", ...}
├─ signatures: {sig_customer: null, sig_tsp: null, ...}
├─ created_at: timestamp
├─ updated_at: timestamp
└─ actions: [Edit] [Submit] [Delete]

            ↓ (User clicks "Submit")

SUBMISSION (Waiting to Sync to Monday.com)
├─ id: UUID
├─ status: "local" (waiting)
├─ formData: {name: "...", email: "...", ...}
├─ signatures: {sig_customer: blob, sig_tsp: blob, ...}
├─ submitted_at: timestamp
├─ monday_item_id: null (until synced)
└─ actions: [Retry] [Delete]

            ↓ (When online - Phase 2)

SYNCED (To Monday.com)
├─ monday_item_id: "2650xxxxxx"
├─ synced_at: timestamp
└─ actions: [View on Monday] [Delete Local]
```

---

## Workflow (Offline-First)

### Scenario 1: TSP in Hospital (No Internet)

```
1. TSP opens app (offline)
   └─ All data already cached locally

2. TSP sees form
   └─ "My Drafts" tab shows: 0 drafts

3. TSP fills form partially
   ├─ Captures customer signature
   └─ Needs to step out (patient emergency)

4. TSP clicks [Save Draft]
   ├─ Data stored in browser IndexedDB
   ├─ Shows: "✓ Draft saved (SR-04603)"
   └─ TSP leaves

5. TSP returns later, clicks [My Drafts]
   ├─ Sees: "SR-04603 - Draft (saved 2 hours ago)"
   └─ Clicks [Edit]

6. Form re-populates, TSP continues filling
   ├─ Captures TSP signature
   ├─ Fills "Problems" field
   └─ Clicks [Submit]

7. Form moved from "Draft" → "Submission"
   ├─ Shows: "✓ Saved locally (pending sync)"
   └─ "My Drafts" tab now shows: 0 drafts
   └─ New "Pending Syncs" shows: 1 item

8. TSP goes to parking lot, gets WiFi signal
   └─ Auto-syncs to Monday.com (Phase 2)
   └─ Status changes to "✓ Synced"
```

### Scenario 2: TSP In Office (Online)

```
1. TSP fills form completely

2. TSP unsure if all data correct → clicks [Save Draft]
   ├─ Data saved locally
   ├─ Shows: "✓ Draft saved"
   └─ TSP can review with supervisor

3. Supervisor reviews on screen

4. TSP clicks [Delete Draft] if wrong
   OR clicks [Submit] if correct
```

---

## UI Mockup

### Main Form (Tab 1: "Fill Report")

```
┌─────────────────────────────┐
│ Service Status Form          │
├─────────────────────────────┤
│ 1. Service Request          │
│    [Select SR...]           │
│                             │
│ 2. Contact Info             │
│    [Email] [Customer Name]  │
│                             │
│ ... more fields ...         │
│                             │
│ [Save Draft] [Submit]       │
│                             │
│ Status: 🟢 ONLINE           │
└─────────────────────────────┘
```

### Drafts Tab (Tab 2: "My Drafts")

```
┌─────────────────────────────┐
│ My Drafts (3)               │
├─────────────────────────────┤
│ SR-04603                    │
│ Saved 2 hours ago           │
│ [Edit] [Delete]             │
├─────────────────────────────┤
│ SR-04602                    │
│ Saved yesterday             │
│ [Edit] [Delete]             │
├─────────────────────────────┤
│ SR-04601                    │
│ Saved 3 days ago            │
│ [Edit] [Delete]             │
└─────────────────────────────┘
```

### Submissions Tab (Tab 3: "Pending Syncs")

```
┌─────────────────────────────┐
│ Pending Syncs (2)           │
├─────────────────────────────┤
│ SR-04600                    │
│ ✓ Synced 1 hour ago         │
│ [View] [Delete]             │
├─────────────────────────────┤
│ SR-04599                    │
│ ⏳ Local (waiting to sync)   │
│ [Retry] [Delete]            │
├─────────────────────────────┤
│ SR-04598                    │
│ ✗ Error: Network            │
│ [Retry] [Details] [Delete]  │
└─────────────────────────────┘
```

---

## Implementation Checklist

- [ ] **Database Schema** — Add "drafts" table to IndexedDB
- [ ] **[Save Draft]** button
- [ ] **[My Drafts]** tab with list
- [ ] **[Edit]** draft → re-populate form
- [ ] **[Delete]** draft
- [ ] **[Submit]** draft → move to submission
- [ ] **Auto-save** draft every 30s while editing (optional)
- [ ] **Draft cleanup** — Delete drafts > 30 days old

---

## Data Storage

### IndexedDB Structure

```javascript
// Database: "ServiceReportDB"
// Two object stores:

// 1. DRAFTS (Work in progress)
{
  keyPath: "id",
  indexes: ["status", "updated_at"]
}
Draft {
  id: UUID,
  status: "draft",
  item_name: "SR-04603",
  formData: {...},
  signatures: {
    sig_customer: blob,
    sig_tsp: blob,
    sig_tsp_workwith: blob
  },
  created_at: timestamp,
  updated_at: timestamp
}

// 2. SUBMISSIONS (Queued to sync)
{
  keyPath: "id",
  indexes: ["status", "submitted_at"]
}
Submission {
  id: UUID,
  status: "local", // "local" | "syncing" | "synced" | "error"
  item_name: "SR-04603",
  formData: {...},
  signatures: {...},
  submitted_at: timestamp,
  monday_item_id: null,
  sync_attempts: 0,
  last_sync_error: null,
  synced_at: null
}
```

---

## Code Changes Required

### 1. Update `frontend/src/db.js`

- Add `getDrafts()` method
- Add `saveDraft()` method
- Add `getDraft(id)` method
- Add `updateDraft(id, data)` method
- Add `deleteDraft(id)` method
- Add `draftToSubmission(draftId)` method (converts draft → submission)

### 2. Update `frontend/src/main.js`

- Add `[Save Draft]` button handler
- Add draft editor with "Continue Editing"
- Update submit to check if editing draft
- Add draft list refresh

### 3. Update `app/templates/index.html`

- Add tabs: "Fill Report" | "My Drafts" | "Pending Syncs"
- Move form to tab 1
- Add draft list to tab 2
- Add submission list to tab 3

### 4. Update form status display

- Show "[Save Draft]" + "[Submit]" buttons
- Auto-save indicator (optional)

---

## API (No Backend Changes Needed)

All draft storage is **client-side only** until user submits.
Once submitted, existing `/submit` endpoint handles it.

---

## Example Flow Code

```javascript
// Save as Draft
async function saveDraft(formData, signatures) {
  await saveDraft({
    id: crypto.randomUUID(),
    status: "draft",
    item_name: formData.name || "Untitled",
    formData,
    signatures,
    created_at: Date.now(),
    updated_at: Date.now(),
  });
  showAlert("✓ Draft saved");
}

// Edit Draft
async function editDraft(draftId) {
  const draft = await getDraft(draftId);
  populateForm(draft.formData);
  restoreSignatures(draft.signatures);
  setCurrentEditingDraft(draftId);
}

// Submit Draft (convert to Submission)
async function submitDraft(draftId) {
  const draft = await getDraft(draftId);

  // Create submission from draft
  const submission = {
    id: crypto.randomUUID(),
    status: "local",
    item_name: draft.item_name,
    formData: draft.formData,
    signatures: draft.signatures,
    submitted_at: Date.now(),
    monday_item_id: null,
  };

  // Save submission
  await saveSubmission(submission);

  // Delete draft
  await deleteDraft(draftId);

  showAlert("✓ Submitted (ready to sync when online)");
  refreshTabs();
}

// Delete Draft
async function deleteDraft(draftId) {
  await deleteFromDB("drafts", draftId);
  showAlert("✓ Draft deleted");
  refreshDraftList();
}
```

---

## Benefits

✅ **Offline-First:** TSP can work completely offline  
✅ **Save Progress:** Don't lose work if interrupted  
✅ **Review Before Submit:** Check data before syncing  
✅ **Flexible:** Submit now or later  
✅ **No Server Calls:** Drafts never leave the browser  
✅ **Works in Philippines:** Perfect for hospitals/labs with no WiFi

---

## Timeline

**To implement:**

- [ ] Database schema (30 min)
- [ ] Save/Load draft handlers (30 min)
- [ ] UI tabs + list (1 hour)
- [ ] Edit draft flow (30 min)
- [ ] Testing (1 hour)

**Total: ~3-4 hours** ← Much faster than full Phase 2 sync

**Ready for production?** Yes, this is pure client-side storage — zero risk.
