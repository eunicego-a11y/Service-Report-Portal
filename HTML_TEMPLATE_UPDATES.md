# HTML Template Updates for Draft & Submission Workflow

## Summary of Changes Needed

Replace the current form + button section with a tabbed interface:

- **Tab 1: Fill Report** — Form + Save Draft + Submit buttons
- **Tab 2: My Drafts** — List of drafted forms (Edit, Delete)
- **Tab 3: Pending Syncs** — List of submitted forms (Local, Syncing, Synced, Error)

---

## 1. Replace Form Section with Tabs

### Find This (Current Submit Button Area)

```html
<button
  id="submitBtn"
  type="submit"
  class="btn btn-success btn-lg"
  style="width: 100%"
>
  <i class="fas fa-paper-plane"></i> Submit to Monday.com
</button>
```

### Replace With This (Complete Tab Section)

```html
<!-- Tabs for Form / Drafts / Submissions -->
<ul class="nav nav-tabs mb-3" role="tablist">
  <li class="nav-item" role="presentation">
    <button
      class="nav-link active"
      id="tab-form"
      data-bs-toggle="tab"
      data-bs-target="#tabpane-form"
      type="button"
      role="tab"
      aria-controls="tabpane-form"
      aria-selected="true"
    >
      Fill Report
    </button>
  </li>
  <li class="nav-item" role="presentation">
    <button
      class="nav-link"
      id="tab-drafts"
      data-bs-toggle="tab"
      data-bs-target="#tabpane-drafts"
      type="button"
      role="tab"
      aria-controls="tabpane-drafts"
      aria-selected="false"
    >
      My Drafts
    </button>
  </li>
  <li class="nav-item" role="presentation">
    <button
      class="nav-link"
      id="tab-submissions"
      data-bs-toggle="tab"
      data-bs-target="#tabpane-submissions"
      type="button"
      role="tab"
      aria-controls="tabpane-submissions"
      aria-selected="false"
    >
      Pending Syncs
    </button>
  </li>
</ul>

<div class="tab-content">
  <!-- TAB 1: Fill Report -->
  <div
    class="tab-pane fade show active"
    id="tabpane-form"
    role="tabpanel"
    aria-labelledby="tab-form"
  >
    <!-- Form content stays here (no changes needed to existing form) -->
    <!-- Just add buttons below after form submission area -->

    <div class="d-grid gap-2 d-sm-flex">
      <button
        type="button"
        data-action="save-draft"
        class="btn btn-outline-secondary btn-lg"
      >
        <i class="fas fa-save"></i> Save Draft
      </button>
      <button id="submitBtn" type="submit" class="btn btn-success btn-lg">
        <i class="fas fa-paper-plane"></i> Submit
      </button>
    </div>

    <div
      id="uploadStatus"
      class="upload-status mt-3"
      style="display: none"
    ></div>
  </div>

  <!-- TAB 2: My Drafts -->
  <div
    class="tab-pane fade"
    id="tabpane-drafts"
    role="tabpanel"
    aria-labelledby="tab-drafts"
  >
    <div id="draftsList" class="list-group">
      <p class="text-muted">Loading drafts...</p>
    </div>
  </div>

  <!-- TAB 3: Pending Syncs -->
  <div
    class="tab-pane fade"
    id="tabpane-submissions"
    role="tabpanel"
    aria-labelledby="tab-submissions"
  >
    <div id="submissionsList" class="list-group">
      <p class="text-muted">Loading submissions...</p>
    </div>
  </div>
</div>
```

---

## 2. Import the Offline Handlers

Add this to your `app/templates/base.html` or main template (in the `<head>`):

```html
<!-- Before </head> or at end of <body> -->
<script type="module">
  import * as offlineHandlers from "/static/dist/offline-handlers.js";
  // Handlers are automatically attached
</script>
```

OR, if using Vite bundling in your main.js:

```javascript
// Add to frontend/src/main.js imports
import "./offline-handlers.js";
```

---

## 3. CSS (Optional - for better styling)

Add to your stylesheet if needed:

```css
/* Draft & Submission List Styling */
.list-group-item {
  padding: 1rem;
  border-left: 4px solid #e9ecef;
}

.list-group-item.draft {
  border-left-color: #0d6efd; /* Blue for drafts */
}

.list-group-item.submission {
  border-left-color: #198754; /* Green for submissions */
}

.list-group-item h6 {
  font-weight: 600;
  margin-bottom: 0.25rem;
}

/* Status badges */
.badge {
  font-size: 0.875rem;
  padding: 0.5rem 0.75rem;
}

/* Tab styling */
.nav-tabs .nav-link {
  border-bottom: 2px solid transparent;
  color: #6c757d;
}

.nav-tabs .nav-link.active {
  border-bottom-color: #0d6efd;
  color: #0d6efd;
}

/* Upload status messages */
.upload-status {
  padding: 1rem;
  border-radius: 0.375rem;
  margin-top: 1rem;
}

.upload-status small {
  display: block;
  margin-top: 0.5rem;
}
```

---

## 4. Complete Example (index.html section)

Here's the complete section that should replace the current submit button area:

```html
<!-- Form Card Container (keep existing) -->
<div class="form-card">
  <div class="form-card-header">
    <div class="section-icon" aria-hidden="true">10</div>
    <h6>Submit</h6>
  </div>
  <div class="form-card-body">
    <!-- Tabs for Form / Drafts / Submissions -->
    <ul class="nav nav-tabs mb-3" role="tablist">
      <li class="nav-item" role="presentation">
        <button
          class="nav-link active"
          id="tab-form"
          data-bs-toggle="tab"
          data-bs-target="#tabpane-form"
          type="button"
          role="tab"
          aria-controls="tabpane-form"
          aria-selected="true"
        >
          Fill Report
        </button>
      </li>
      <li class="nav-item" role="presentation">
        <button
          class="nav-link"
          id="tab-drafts"
          data-bs-toggle="tab"
          data-bs-target="#tabpane-drafts"
          type="button"
          role="tab"
          aria-controls="tabpane-drafts"
          aria-selected="false"
        >
          My Drafts
        </button>
      </li>
      <li class="nav-item" role="presentation">
        <button
          class="nav-link"
          id="tab-submissions"
          data-bs-toggle="tab"
          data-bs-target="#tabpane-submissions"
          type="button"
          role="tab"
          aria-controls="tabpane-submissions"
          aria-selected="false"
        >
          Pending Syncs
        </button>
      </li>
    </ul>

    <div class="tab-content">
      <!-- TAB 1: Fill Report -->
      <div
        class="tab-pane fade show active"
        id="tabpane-form"
        role="tabpanel"
        aria-labelledby="tab-form"
      >
        <p class="text-muted mb-3">
          <strong>Tip:</strong> You can save your work as a draft and come back
          to it later. Forms are saved offline and will sync to Monday.com when
          you're online.
        </p>

        <div class="d-grid gap-2 d-sm-flex">
          <button
            type="button"
            data-action="save-draft"
            class="btn btn-outline-secondary btn-lg"
          >
            <i class="fas fa-save"></i> Save Draft
          </button>
          <button id="submitBtn" type="submit" class="btn btn-success btn-lg">
            <i class="fas fa-paper-plane"></i> Submit
          </button>
        </div>

        <div
          id="uploadStatus"
          class="alert mt-3"
          role="status"
          style="display: none"
        ></div>
      </div>

      <!-- TAB 2: My Drafts -->
      <div
        class="tab-pane fade"
        id="tabpane-drafts"
        role="tabpanel"
        aria-labelledby="tab-drafts"
      >
        <p class="text-muted mb-3">
          <strong>Note:</strong> Drafts are saved in your browser. They are not
          yet submitted to Monday.com.
        </p>
        <div id="draftsList" class="list-group">
          <p class="text-muted">Loading drafts...</p>
        </div>
      </div>

      <!-- TAB 3: Pending Syncs -->
      <div
        class="tab-pane fade"
        id="tabpane-submissions"
        role="tabpanel"
        aria-labelledby="tab-submissions"
      >
        <p class="text-muted mb-3">
          <strong>Note:</strong> Submitted forms sync to Monday.com
          automatically when you're online.
        </p>
        <div id="submissionsList" class="list-group">
          <p class="text-muted">Loading submissions...</p>
        </div>
      </div>
    </div>
  </div>
</div>
```

---

## 5. JavaScript Integration

### In `frontend/src/main.js`, add imports:

```javascript
// Add to top of main.js (after existing imports)
import "./offline-handlers.js";
import { initDB } from "./db.js";

// Initialize offline DB on app start
document.addEventListener("DOMContentLoaded", async () => {
  await initDB();
  console.log("[APP] Offline database initialized");
  // ... rest of initialization
});
```

---

## 6. Update Vite Build

Make sure `frontend/src/main.js` includes:

```javascript
import "./offline-handlers.js";
```

Then rebuild:

```powershell
cd frontend
npm run build
```

---

## 7. Testing the UI

### Test Case 1: Save Draft

1. Fill partial form
2. Click [Save Draft]
3. ✓ See "✓ Draft saved" message
4. Click [My Drafts] tab
5. ✓ See draft listed with "Edit" and "Delete" buttons

### Test Case 2: Edit Draft

1. Click [My Drafts]
2. Click [Edit] on a draft
3. ✓ Form re-populates with saved data
4. Make changes
5. Click [Save Draft]
6. ✓ Changes saved

### Test Case 3: Submit Draft

1. Click [My Drafts]
2. Click [Edit]
3. Make changes
4. Click [Submit]
5. ✓ Form disappears from [My Drafts]
6. Click [Pending Syncs]
7. ✓ See submission with "💾 Local" badge

---

## Checklist

- [ ] Create `frontend/src/db.js` (database module)
- [ ] Create `frontend/src/offline-handlers.js` (handlers)
- [ ] Update `frontend/src/main.js` to import offline-handlers.js
- [ ] Update HTML template with tabs
- [ ] Rebuild Vite: `npm run build`
- [ ] Test save draft workflow
- [ ] Test edit draft workflow
- [ ] Test submit workflow
- [ ] Go offline and test all flows
- [ ] Go online and verify no errors
