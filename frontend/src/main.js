/**
 * main.js — Application entry point.
 * Imports styles (Vite bundles them to main.css) and orchestrates all modules.
 * Depends on CDN globals: window.$, window.SignaturePad, window.bootstrap
 */

import "./style.css";

import {
  openDB,
  buildSignaturePads,
  initPads,
  updatePendingBadge,
  syncPending,
  clearPending,
  uploadSignature,
  saveSignatureBlob,
  sigBlobs,
  pads,
  SIG_PADS,
  captureSignature,
  clearPad,
} from "./signatures.js";

import { loadDraft, clearDraft } from "./draft.js";
import { initOfflineUI } from "./offline-ui.js";

// ── Select2 initialisation ────────────────────────────────────────────────────

/** Render a person option with avatar/initials like Monday's people column */
function formatPerson(person) {
  if (!person.id) return person.text;
  const photo = person.photo
    ? `<img src="${person.photo}" class="people-avatar" alt="" />`
    : `<span class="people-initials">${person.initials || "?"}</span>`;
  return window.$(
    `<span class="people-option">${photo}<span class="people-name">${person.text}</span></span>`,
  );
}

/** Render a selected person tag */
function formatPersonSelection(person) {
  if (!person.id) return person.text;
  const photo = person.photo
    ? `<img src="${person.photo}" class="people-avatar-sm" alt="" />`
    : `<span class="people-initials-sm">${person.initials || "?"}</span>`;
  return window.$(`<span class="people-tag">${photo} ${person.text}</span>`);
}

function initSelect2() {
  if (!window.$ || !window.$.fn.select2) {
    setTimeout(initSelect2, 100);
    return;
  }
  try {
    // Service request dropdown
    window.$('select[name="linked_item_id"]').select2({
      placeholder: "Type to search service requests...",
      allowClear: true,
      width: "100%",
      ajax: {
        url: "/search_linked_items",
        dataType: "json",
        delay: 300,
        data: (params) => ({ q: params.term || "" }),
        processResults: (data) => ({ results: data.results }),
        cache: false,
      },
      minimumInputLength: 1,
      language: {
        inputTooShort: () => "Type at least 1 character to search…",
        searching: () => "Searching Monday.com…",
        noResults: () => "No service requests found",
      },
    });

    // Machine System dropdown with search
    window.$(".machine-picker").select2({
      placeholder: "Search machine systems…",
      allowClear: true,
      width: "100%",
      minimumResultsForSearch: 0,
    });

    // People picker — TSP WORKWITH
    window.$(".people-picker").select2({
      placeholder: "Search team members…",
      allowClear: true,
      width: "100%",
      ajax: {
        url: "/api/users",
        dataType: "json",
        delay: 250,
        data: (params) => ({ q: params.term || "" }),
        processResults: (data) => ({ results: data.results }),
        cache: true,
      },
      minimumInputLength: 0,
      templateResult: formatPerson,
      templateSelection: formatPersonSelection,
      language: {
        searching: () => "Searching team members…",
        noResults: () => "No members found",
      },
    });
  } catch (e) {
    console.error("Select2 init error:", e);
  }
}

// ── Form submission ───────────────────────────────────────────────────────────

async function handleSubmit(e) {
  e.preventDefault();

  const form = document.getElementById("mainForm");
  const btn = document.getElementById("submitBtn");
  const statusDiv = document.getElementById("uploadStatus");

  btn.disabled = true;
  btn.textContent = "Submitting...";
  statusDiv.style.display = "block";
  statusDiv.className = "upload-status bg-info-subtle text-info";
  statusDiv.textContent = "Creating item on Monday.com...";

  try {
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

    // Step 1: Submit form data
    const formData = new FormData(form);

    // Select2 AJAX selections are NOT reliably reflected in the native <select>
    // DOM element. Use select2('data') which reads Select2's internal state.
    if (window.$ && window.$.fn.select2) {
      const peopleEl = window.$("#field-workwith");
      if (peopleEl.length) {
        formData.delete("tsp_workwith");
        const selected = peopleEl.select2("data") || [];
        console.log("[WORKWITH] select2 data:", selected);
        for (const item of selected) {
          if (item.id) formData.append("tsp_workwith", item.id);
        }
        console.log(
          "[WORKWITH] FormData tsp_workwith:",
          formData.getAll("tsp_workwith"),
        );
      }
    }

    const res = await fetch("/submit", {
      method: "POST",
      headers: { "X-Requested-With": "XMLHttpRequest" },
      body: formData,
    });
    const result = await res.json();

    if (!result.success || !result.item_id) {
      statusDiv.className = "upload-status bg-danger-subtle text-danger";
      statusDiv.textContent =
        "Error: " + (result.error || "Failed to create item");
      btn.disabled = false;
      btn.textContent = "Submit to Monday.com";
      return;
    }

    const itemId = result.item_id;
    statusDiv.textContent = `Item created (ID: ${itemId}). Uploading signatures…`;

    // Step 2: Upload signatures
    const sigKeys = Object.keys(sigBlobs);
    let uploaded = 0;
    let failed = 0;

    for (const key of sigKeys) {
      statusDiv.textContent = `Uploading ${key}… (${uploaded + 1}/${sigKeys.length})`;
      try {
        const uploadResult = await uploadSignature(key, sigBlobs[key], itemId);
        if (uploadResult.success) {
          uploaded++;
        } else {
          console.warn(`[SIG] ${key} failed:`, uploadResult.error);
          await saveSignatureBlob(key, sigBlobs[key], itemId);
          failed++;
        }
      } catch (err) {
        console.error(`[SIG] ${key} error:`, err);
        await saveSignatureBlob(key, sigBlobs[key], itemId);
        failed++;
      }
    }

    // Step 3: Show result
    if (failed === 0 && sigKeys.length > 0) {
      statusDiv.className = "upload-status bg-success-subtle text-success";
      statusDiv.textContent = `Done! Item created + ${uploaded} signature(s) uploaded.`;
    } else if (failed > 0) {
      statusDiv.className = "upload-status bg-warning-subtle text-warning";
      statusDiv.textContent = `Item created. ${uploaded} uploaded, ${failed} saved offline (use Sync).`;
    } else {
      statusDiv.className = "upload-status bg-success-subtle text-success";
      statusDiv.textContent = `Item "${result.item_name}" created successfully!`;
    }

    // Cleanup
    for (const key of sigKeys) delete sigBlobs[key];
    for (const cfg of SIG_PADS) clearPad(cfg.key);
    form.reset();
    clearDraft();
    await updatePendingBadge();
  } catch (err) {
    console.error("[SUBMIT] Error:", err);
    statusDiv.className = "upload-status bg-danger-subtle text-danger";
    statusDiv.textContent = "Submission error: " + err.message;
  }

  btn.disabled = false;
  btn.textContent = "Submit to Monday.com";
}

// ── DOMContentLoaded ──────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", async () => {
  // IndexedDB
  try {
    await openDB();
  } catch (e) {
    console.warn("IndexedDB unavailable:", e);
  }

  // Initialize offline-first UI (drafts + submissions tabs)
  try {
    await initOfflineUI();
  } catch (e) {
    console.warn("[OFFLINE] UI init failed:", e);
  }

  // Signature pads (DOM injection + initialise after CDN scripts loaded)
  buildSignaturePads();

  // Wait for CDN scripts (deferred) then init pads + select2
  const waitForCDN = () => {
    if (window.SignaturePad && window.$) {
      initPads();
      initSelect2();
    } else {
      setTimeout(waitForCDN, 50);
    }
  };
  waitForCDN();

  // Form events
  document.getElementById("mainForm")?.addEventListener("submit", handleSubmit);
  // Note: saveDraftBtn click is handled by offline-ui.js initOfflineUI() via [data-action='save-draft']

  // Sidebar pending-signature actions
  document.getElementById("syncBtn")?.addEventListener("click", syncPending);
  document
    .getElementById("clearPendingBtn")
    ?.addEventListener("click", clearPending);

  // Draft restore + pending badge
  loadDraft();
  await updatePendingBadge();

  console.log("[INIT] Service Report Portal ready");
});
