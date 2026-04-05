/**
 * main.js - Draft & Submit Handlers
 * Add these code snippets to your existing main.js
 */

// ─────────────────────────────────────────────────────────────────────────
// IMPORTS (Add to top of main.js)
// ─────────────────────────────────────────────────────────────────────────

import {
  initDB,
  saveDraft,
  getDraft,
  getAllDrafts,
  updateDraft,
  deleteDraft,
  saveSubmission,
  getAllSubmissions,
  getSubmissionsByStatus,
  convertDraftToSubmission,
} from "./db.js";

// ─────────────────────────────────────────────────────────────────────────
// GLOBAL STATE
// ─────────────────────────────────────────────────────────────────────────

let currentEditingDraftId = null; // Track if editing a draft
let sigBlobs = {
  sig_customer: null,
  sig_tsp: null,
  sig_tsp_workwith: null,
};

// ─────────────────────────────────────────────────────────────────────────
// INITIALIZATION
// ─────────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", async () => {
  try {
    await initDB();
    console.log("[APP] Offline storage initialized");

    // Refresh all tabs
    await refreshDraftsList();
    await refreshSubmissionsList();

    // Auto-refresh every 10 seconds
    setInterval(refreshDraftsList, 10000);
    setInterval(refreshSubmissionsList, 10000);
  } catch (err) {
    console.error("[APP] Failed to initialize offline storage:", err);
  }
});

// ─────────────────────────────────────────────────────────────────────────
// SAVE DRAFT HANDLER
// ─────────────────────────────────────────────────────────────────────────

async function handleSaveDraft(e) {
  e.preventDefault();

  const form = document.getElementById("mainForm");
  const btn = document.querySelector("[data-action='save-draft']");
  const statusDiv = document.getElementById("uploadStatus");

  btn.disabled = true;
  btn.textContent = "Saving…";
  statusDiv.style.display = "block";
  statusDiv.className = "upload-status bg-info-subtle text-info";
  statusDiv.textContent = "Saving draft locally…";

  try {
    // Capture unsaved signatures
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
    const formData = new FormData(form);
    const itemName = formData.get("name") || "Untitled";

    // Sync Select2 values
    if (window.$ && window.$.fn.select2) {
      const peopleEl = window.$("#field-workwith");
      if (peopleEl.length) {
        formData.delete("tsp_workwith");
        const selected = peopleEl.select2("data") || [];
        for (const item of selected) {
          if (item.id) formData.append("tsp_workwith", item.id);
        }
      }

      const assignedEl = window.$("#field-assigned");
      if (assignedEl.length) {
        formData.delete("tsp_assigned");
        const selectedAssigned = assignedEl.select2("data") || [];
        for (const item of selectedAssigned) {
          if (item.id) formData.append("tsp_assigned", item.id);
        }
      }
    }

    // Build draft object
    const draftData = {
      id: currentEditingDraftId || crypto.randomUUID(),
      status: "draft",
      item_name: itemName,
      formData: Object.fromEntries(formData),
      signatures: sigBlobs,
      created_at: currentEditingDraftId ? undefined : Date.now(),
      updated_at: Date.now(),
    };

    // Remove undefined to preserve created_at on update
    if (draftData.created_at === undefined) {
      delete draftData.created_at;
    }

    // Save draft
    if (currentEditingDraftId) {
      await updateDraft(currentEditingDraftId, {
        item_name: draftData.item_name,
        formData: draftData.formData,
        signatures: draftData.signatures,
        updated_at: Date.now(),
      });
      console.log("[DRAFT] Updated:", currentEditingDraftId);
    } else {
      draftData.created_at = Date.now();
      await saveDraft(draftData);
      console.log("[DRAFT] Saved:", draftData.id);
    }

    // Show success
    statusDiv.className = "upload-status bg-success-subtle text-success";
    statusDiv.innerHTML = `
      <div>
        ✓ <strong>Draft saved</strong>
        <br/>
        <small>You can continue editing or submit later.</small>
      </div>
    `;

    btn.disabled = false;
    btn.textContent = "Save Draft";

    setTimeout(() => {
      statusDiv.style.display = "none";
    }, 4000);

    // Refresh drafts list
    await refreshDraftsList();
  } catch (error) {
    console.error("[DRAFT] Error:", error);
    statusDiv.className = "upload-status bg-danger-subtle text-danger";
    statusDiv.textContent = `Error: ${error.message}`;
    btn.disabled = false;
    btn.textContent = "Save Draft";
  }
}

// ─────────────────────────────────────────────────────────────────────────
// SUBMIT HANDLER (Updated for drafts)
// ─────────────────────────────────────────────────────────────────────────

async function handleSubmit(e) {
  e.preventDefault();

  const form = document.getElementById("mainForm");
  const btn = document.getElementById("submitBtn");
  const statusDiv = document.getElementById("uploadStatus");

  btn.disabled = true;
  btn.textContent = "Submitting…";
  statusDiv.style.display = "block";
  statusDiv.className = "upload-status bg-info-subtle text-info";
  statusDiv.textContent = "Submitting form…";

  try {
    // Capture unsaved signatures
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
    const formData = new FormData(form);
    const itemName = formData.get("name") || "Untitled";

    // Sync Select2 values
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

    // Build submission
    const submission = {
      id: currentEditingDraftId ? crypto.randomUUID() : crypto.randomUUID(),
      status: "local",
      item_name: itemName,
      formData: Object.fromEntries(formData),
      signatures: sigBlobs,
      submitted_at: Date.now(),
      monday_item_id: null,
      sync_attempts: 0,
      last_sync_error: null,
      synced_at: null,
    };

    // Save submission
    await saveSubmission(submission);

    // If editing a draft, delete it
    if (currentEditingDraftId) {
      await deleteDraft(currentEditingDraftId);
      currentEditingDraftId = null;
    }

    // Show success
    statusDiv.className = "upload-status bg-success-subtle text-success";
    statusDiv.innerHTML = `
      <div>
        ✓ <strong>Submitted (saved locally)</strong>
        <br/>
        <small>This will sync to Monday.com when internet is available.</small>
        <br/>
        <small style="color: #666;">ID: ${submission.id.slice(0, 8)}</small>
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

    btn.disabled = false;
    btn.textContent = "Submit";

    setTimeout(() => {
      statusDiv.style.display = "none";
    }, 5000);

    // Refresh both lists
    await refreshDraftsList();
    await refreshSubmissionsList();
  } catch (error) {
    console.error("[SUBMIT] Error:", error);
    statusDiv.className = "upload-status bg-danger-subtle text-danger";
    statusDiv.textContent = `Error: ${error.message}`;
    btn.disabled = false;
    btn.textContent = "Submit";
  }
}

// ─────────────────────────────────────────────────────────────────────────
// DRAFT EDITING
// ─────────────────────────────────────────────────────────────────────────

async function editDraft(draftId) {
  try {
    const draft = await getDraft(draftId);
    if (!draft) {
      alert("Draft not found");
      return;
    }

    // Populate form
    const form = document.getElementById("mainForm");
    for (const [key, value] of Object.entries(draft.formData)) {
      const field = form.elements[key];
      if (field) {
        field.value = value;
        // Trigger change events for Select2
        if (window.$ && window.$(field).data("select2")) {
          window.$(field).trigger("change");
        }
      }
    }

    // Restore signatures
    sigBlobs = { ...draft.signatures };
    for (const [key, blob] of Object.entries(sigBlobs)) {
      if (blob && pads[key]) {
        // Canvas already has content from previous session - show it
        console.log(`[DRAFT] Restored signature: ${key}`);
      }
    }

    // Mark as editing
    currentEditingDraftId = draftId;

    // Scroll to form
    document.getElementById("mainForm").scrollIntoView({ behavior: "smooth" });

    // Show info
    const statusDiv = document.getElementById("uploadStatus");
    statusDiv.style.display = "block";
    statusDiv.className = "upload-status bg-info-subtle text-info";
    statusDiv.textContent = "✏️ Editing draft (changes saved automatically)";
    setTimeout(() => {
      statusDiv.style.display = "none";
    }, 3000);
  } catch (err) {
    console.error("[EDIT] Error:", err);
    alert(`Error: ${err.message}`);
  }
}

// ─────────────────────────────────────────────────────────────────────────
// DRAFTS LIST UI
// ─────────────────────────────────────────────────────────────────────────

async function refreshDraftsList() {
  try {
    const drafts = await getAllDrafts();
    const container = document.getElementById("draftsList");

    if (!container) return; // Tab not available

    if (drafts.length === 0) {
      container.innerHTML =
        '<p class="text-muted">No drafts saved yet. Start filling the form above.</p>';
      return;
    }

    let html = '<div class="list-group">';
    for (const draft of drafts.sort((a, b) => b.updated_at - a.updated_at)) {
      const date = new Date(draft.updated_at).toLocaleString();
      const name = draft.item_name || `Draft ${draft.id.slice(0, 8)}`;

      html += `
        <div class="list-group-item d-flex justify-content-between align-items-center">
          <div>
            <h6 class="mb-1">${name}</h6>
            <small class="text-muted">Last edited: ${date}</small>
          </div>
          <div>
            <button class="btn btn-sm btn-primary" onclick="window.editDraft('${draft.id}')">
              Edit
            </button>
            <button class="btn btn-sm btn-danger" onclick="window.deleteDraftUI('${draft.id}')">
              Delete
            </button>
          </div>
        </div>
      `;
    }
    html += "</div>";
    container.innerHTML = html;
  } catch (err) {
    console.error("[DRAFTS] Error:", err);
  }
}

// ─────────────────────────────────────────────────────────────────────────
// SUBMISSIONS LIST UI
// ─────────────────────────────────────────────────────────────────────────

async function refreshSubmissionsList() {
  try {
    const submissions = await getAllSubmissions();
    const container = document.getElementById("submissionsList");

    if (!container) return; // Tab not available

    if (submissions.length === 0) {
      container.innerHTML =
        '<p class="text-muted">No submissions yet. Submit forms to see them here.</p>';
      return;
    }

    let html = '<div class="list-group">';
    for (const sub of submissions.sort(
      (a, b) => b.submitted_at - a.submitted_at,
    )) {
      const date = new Date(sub.submitted_at).toLocaleString();
      const name = sub.item_name || `Item ${sub.id.slice(0, 8)}`;

      let statusBadge = "";
      if (sub.status === "synced") {
        statusBadge = '<span class="badge bg-success">✓ Synced</span>';
      } else if (sub.status === "syncing") {
        statusBadge = '<span class="badge bg-warning">⏳ Syncing</span>';
      } else if (sub.status === "error") {
        statusBadge = '<span class="badge bg-danger">✗ Error</span>';
      } else {
        statusBadge = '<span class="badge bg-info">💾 Local</span>';
      }

      html += `
        <div class="list-group-item">
          <div class="d-flex justify-content-between align-items-start">
            <div>
              <h6 class="mb-1">${name}</h6>
              <small class="text-muted">Submitted: ${date}</small>
              ${sub.monday_item_id ? `<br/><small>Monday ID: ${sub.monday_item_id}</small>` : ""}
              ${sub.last_sync_error ? `<br/><small class="text-danger">Error: ${sub.last_sync_error}</small>` : ""}
            </div>
            <div>
              ${statusBadge}
            </div>
          </div>
        </div>
      `;
    }
    html += "</div>";
    container.innerHTML = html;
  } catch (err) {
    console.error("[SUBMISSIONS] Error:", err);
  }
}

// ─────────────────────────────────────────────────────────────────────────
// DELETE DRAFT (with confirmation)
// ─────────────────────────────────────────────────────────────────────────

async function deleteDraftUI(draftId) {
  if (!confirm("Delete this draft? This cannot be undone.")) return;

  try {
    await deleteDraft(draftId);
    if (currentEditingDraftId === draftId) {
      currentEditingDraftId = null;
    }
    await refreshDraftsList();
  } catch (err) {
    console.error("[DELETE] Error:", err);
    alert(`Error: ${err.message}`);
  }
}

// ─────────────────────────────────────────────────────────────────────────
// EXPORT GLOBAL FUNCTIONS (for HTML onclick handlers)
// ─────────────────────────────────────────────────────────────────────────

window.editDraft = editDraft;
window.deleteDraftUI = deleteDraftUI;
window.handleSaveDraft = handleSaveDraft;
window.handleSubmit = handleSubmit;

// ─────────────────────────────────────────────────────────────────────────
// BUTTON HANDLERS (Attach to HTML)
// ─────────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  const saveDraftBtn = document.querySelector("[data-action='save-draft']");
  const submitBtn = document.getElementById("submitBtn");

  if (saveDraftBtn) {
    saveDraftBtn.addEventListener("click", handleSaveDraft);
  }
  if (submitBtn) {
    submitBtn.addEventListener("click", handleSubmit);
  }
});
