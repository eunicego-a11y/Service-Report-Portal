/**
 * signatures.js — IndexedDB storage + SignaturePad management.
 * All functions are exported so main.js can orchestrate them.
 */

const DB_NAME = "ServiceReportDB";
const DB_VERSION = 4; // v4: must match draft.js to avoid upgrade blocking

/** @type {IDBDatabase|null} */
let db = null;

/** @type {Record<string, import('signature_pad').default>} */
export const pads = {};

/** @type {Record<string, Blob>} */
export const sigBlobs = {};

export const SIG_PADS = [
  {
    key: "sig_tsp",
    label: "TSP Representative",
    col: "col-12 col-sm-6 col-lg-4",
  },
  { key: "sig_customer", label: "Customer", col: "col-12 col-sm-6 col-lg-4" },
  {
    key: "sig_biomed",
    label: "BIOMED Representative",
    col: "col-12 col-sm-6 col-lg-4",
  },
  {
    key: "sig_tsp_workwith",
    label: "TSP WORKWITH",
    col: "col-12 col-sm-6 col-lg-4",
  },
];

// ── IndexedDB ─────────────────────────────────────────────────────────────────

export function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = (e) => {
      const database = e.target.result;
      const oldVersion = e.oldVersion;

      // v4 migration: delete old drafts store that had keyPath:'key'
      if (oldVersion < 4 && database.objectStoreNames.contains("drafts")) {
        database.deleteObjectStore("drafts");
      }

      if (!database.objectStoreNames.contains("signatures")) {
        database.createObjectStore("signatures", {
          keyPath: "id",
          autoIncrement: true,
        });
      }
      if (!database.objectStoreNames.contains("drafts")) {
        database.createObjectStore("drafts", { keyPath: "id" });
      }
      if (!database.objectStoreNames.contains("submissions")) {
        database.createObjectStore("submissions", { keyPath: "id" });
      }
    };
    req.onsuccess = (e) => {
      db = e.target.result;
      // Close this connection when a higher version is requested (prevents blocking)
      db.onversionchange = () => {
        db.close();
        db = null;
        console.warn("[OFFLINE-DB] Connection closed for version upgrade");
      };
      resolve(db);
    };
    req.onerror = (e) => {
      console.error("IndexedDB error:", e);
      reject(e);
    };
    req.onblocked = () => {
      console.warn(
        "[OFFLINE-DB] Open blocked — close other tabs using this app",
      );
    };
  });
}

export async function saveSignatureBlob(sigKey, blob, itemId) {
  if (!db) return;
  try {
    const tx = db.transaction("signatures", "readwrite");
    tx.objectStore("signatures").add({
      sigKey,
      blob,
      itemId: itemId || null,
      status: itemId ? "pending" : "draft",
      createdAt: new Date().toISOString(),
    });
    await new Promise((res, rej) => {
      tx.oncomplete = res;
      tx.onerror = rej;
    });
  } catch (e) {
    console.error("saveSignatureBlob error:", e);
  }
}

export async function getPendingSignatures() {
  if (!db) return [];
  try {
    const tx = db.transaction("signatures", "readonly");
    const all = await new Promise((res, rej) => {
      const req = tx.objectStore("signatures").getAll();
      req.onsuccess = () => res(req.result);
      req.onerror = rej;
    });
    return all.filter((r) => r.status === "pending");
  } catch (e) {
    console.error("getPendingSignatures error:", e);
    return [];
  }
}

export async function deleteSignatureRecord(id) {
  if (!db) return;
  try {
    const tx = db.transaction("signatures", "readwrite");
    tx.objectStore("signatures").delete(id);
    await new Promise((res, rej) => {
      tx.oncomplete = res;
      tx.onerror = rej;
    });
  } catch (e) {
    console.error("deleteSignatureRecord error:", e);
  }
}

export async function updatePendingBadge() {
  const pending = await getPendingSignatures();
  const badge = document.getElementById("pendingBadge");
  const card = document.getElementById("pendingCard");
  const list = document.getElementById("pendingList");
  if (!badge) return;
  if (pending.length > 0) {
    badge.style.display = "inline";
    badge.textContent = `${pending.length} pending`;
    if (card) card.style.display = "block";
    if (list) {
      list.innerHTML = pending
        .map(
          (p) =>
            `<div class="d-flex justify-content-between mb-1"><span>${p.sigKey}</span><span class="text-muted">Item: ${p.itemId || "?"}</span></div>`,
        )
        .join("");
    }
  } else {
    badge.style.display = "none";
    if (card) card.style.display = "none";
  }
}

// ── Canvas / Pad helpers ──────────────────────────────────────────────────────

/**
 * Resize a canvas to match its CSS size × devicePixelRatio.
 * Must be called after layout so getBoundingClientRect works.
 */
export function resizeCanvas(canvas, pad) {
  const ratio = Math.max(window.devicePixelRatio || 1, 1);
  const rect = canvas.getBoundingClientRect();
  const w = rect.width || canvas.offsetWidth || 300;
  const h = rect.height || canvas.offsetHeight || 160;
  canvas.width = w * ratio;
  canvas.height = h * ratio;
  const ctx = canvas.getContext("2d");
  ctx.scale(ratio, ratio);
  pad.clear();
}

/**
 * Inject signature pad DOM into #signaturePads and initialise SignaturePad instances.
 * Depends on window.SignaturePad being loaded (CDN script in base.html).
 */
export function buildSignaturePads() {
  const container = document.getElementById("signaturePads");
  if (!container) return;

  for (const cfg of SIG_PADS) {
    const div = document.createElement("div");
    div.className = `${cfg.col} sig-container`;
    div.innerHTML = `
      <div class="sig-label">${cfg.label}</div>
      <div class="sig-box" id="box-${cfg.key}">
        <canvas id="canvas-${cfg.key}"></canvas>
        <div class="sig-toolbar">
          <button type="button" class="btn btn-success btn-sm flex-grow-1"
                  data-sig-capture="${cfg.key}">Use Signature</button>
          <button type="button" class="btn btn-outline-secondary btn-sm"
                  data-sig-clear="${cfg.key}">Clear</button>
        </div>
        <div class="sig-preview" id="preview-${cfg.key}">
          <div class="d-flex align-items-center gap-2">
            <img id="thumb-${cfg.key}" src="" alt="signature preview" />
            <span class="badge bg-success">Captured</span>
          </div>
        </div>
      </div>`;
    container.appendChild(div);
  }

  // Delegate click events
  container.addEventListener("click", (e) => {
    const captureKey = e.target.dataset.sigCapture;
    const clearKey = e.target.dataset.sigClear;
    if (captureKey) captureSignature(captureKey);
    if (clearKey) clearPad(clearKey);
  });
}

export function initPads() {
  for (const cfg of SIG_PADS) {
    const canvas = document.getElementById(`canvas-${cfg.key}`);
    if (!canvas) continue;
    const pad = new window.SignaturePad(canvas, {
      minWidth: 0.5,
      maxWidth: 2.5,
      throttle: 16,
    });
    pads[cfg.key] = pad;
    resizeCanvas(canvas, pad);
  }

  let resizeTimer;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      for (const cfg of SIG_PADS) {
        const canvas = document.getElementById(`canvas-${cfg.key}`);
        if (canvas && pads[cfg.key]) resizeCanvas(canvas, pads[cfg.key]);
      }
    }, 200);
  });
}

export function captureSignature(key) {
  const pad = pads[key];
  if (!pad) {
    alert("Signature pad not ready");
    return;
  }
  if (pad.isEmpty()) {
    alert("Please draw a signature first");
    return;
  }

  const canvas = document.getElementById(`canvas-${key}`);
  canvas.toBlob((blob) => {
    if (!blob) {
      alert("Failed to capture signature");
      return;
    }
    sigBlobs[key] = blob;
    const url = URL.createObjectURL(blob);
    document.getElementById(`thumb-${key}`).src = url;
    document.getElementById(`preview-${key}`).style.display = "block";
    document.getElementById(`box-${key}`).classList.add("has-signature");
  }, "image/png");
}

export function clearPad(key) {
  const pad = pads[key];
  if (pad) pad.clear();
  delete sigBlobs[key];
  const preview = document.getElementById(`preview-${key}`);
  const box = document.getElementById(`box-${key}`);
  if (preview) preview.style.display = "none";
  if (box) box.classList.remove("has-signature");
}

// ── Upload ────────────────────────────────────────────────────────────────────

export async function uploadSignature(key, blob, itemId) {
  const formData = new FormData();
  formData.append("file", blob, `${key}.png`);
  formData.append("item_id", itemId);
  formData.append("sig_key", key);
  const res = await fetch("/api/upload_signature", {
    method: "POST",
    body: formData,
  });
  const data = await res.json();
  console.log(`[SIG UPLOAD] ${key}:`, data);
  return data;
}

export async function syncPending() {
  const pending = await getPendingSignatures();
  if (pending.length === 0) {
    alert("No pending signatures");
    return;
  }
  let synced = 0;
  for (const rec of pending) {
    try {
      const result = await uploadSignature(rec.sigKey, rec.blob, rec.itemId);
      if (result.success) {
        await deleteSignatureRecord(rec.id);
        synced++;
      }
    } catch (e) {
      console.error("Sync failed for", rec.sigKey, e);
    }
  }
  await updatePendingBadge();
  alert(`Synced ${synced}/${pending.length} signatures`);
}

export async function clearPending() {
  if (!confirm("Clear all pending signatures? This cannot be undone.")) return;
  const pending = await getPendingSignatures();
  for (const rec of pending) await deleteSignatureRecord(rec.id);
  await updatePendingBadge();
  alert(`Cleared ${pending.length} pending signatures`);
}
