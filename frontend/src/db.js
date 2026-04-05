/**
 * Offline-First Database Module
 * Handles drafts (work in progress) and submissions (queued to sync)
 */

const DB_NAME = "ServiceReportDB";
const DB_VERSION = 1;
const STORE_DRAFTS = "drafts";
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

      // Create drafts store
      if (!db.objectStoreNames.contains(STORE_DRAFTS)) {
        const draftStore = db.createObjectStore(STORE_DRAFTS, {
          keyPath: "id",
        });
        draftStore.createIndex("status", "status", { unique: false });
        draftStore.createIndex("updated_at", "updated_at", { unique: false });
        console.log("[DB] Drafts store created");
      }

      // Create submissions store
      if (!db.objectStoreNames.contains(STORE_SUBMISSIONS)) {
        const subStore = db.createObjectStore(STORE_SUBMISSIONS, {
          keyPath: "id",
        });
        subStore.createIndex("status", "status", { unique: false });
        subStore.createIndex("submitted_at", "submitted_at", { unique: false });
        console.log("[DB] Submissions store created");
      }
    };
  });
}

// ── DRAFTS ──────────────────────────────────────────────────────────────

export async function saveDraft(draft) {
  if (!dbInstance) await initDB();
  return new Promise((resolve, reject) => {
    const tx = dbInstance.transaction([STORE_DRAFTS], "readwrite");
    const store = tx.objectStore(STORE_DRAFTS);
    const req = store.put(draft); // put = add or update

    req.onerror = () => reject(new Error("Failed to save draft"));
    req.onsuccess = () => {
      console.log("[DB] Draft saved:", draft.id);
      resolve(draft.id);
    };
  });
}

export async function getDraft(id) {
  if (!dbInstance) await initDB();
  return new Promise((resolve, reject) => {
    const tx = dbInstance.transaction([STORE_DRAFTS], "readonly");
    const store = tx.objectStore(STORE_DRAFTS);
    const req = store.get(id);

    req.onerror = () => reject(new Error("Failed to get draft"));
    req.onsuccess = () => resolve(req.result);
  });
}

export async function getAllDrafts() {
  if (!dbInstance) await initDB();
  return new Promise((resolve, reject) => {
    const tx = dbInstance.transaction([STORE_DRAFTS], "readonly");
    const store = tx.objectStore(STORE_DRAFTS);
    const req = store.getAll();

    req.onerror = () => reject(new Error("Failed to get drafts"));
    req.onsuccess = () => resolve(req.result || []);
  });
}

export async function updateDraft(id, updates) {
  const existing = await getDraft(id);
  if (!existing) throw new Error("Draft not found");

  const updated = {
    ...existing,
    ...updates,
    updated_at: Date.now(),
  };
  return saveDraft(updated);
}

export async function deleteDraft(id) {
  if (!dbInstance) await initDB();
  return new Promise((resolve, reject) => {
    const tx = dbInstance.transaction([STORE_DRAFTS], "readwrite");
    const store = tx.objectStore(STORE_DRAFTS);
    const req = store.delete(id);

    req.onerror = () => reject(new Error("Failed to delete draft"));
    req.onsuccess = () => {
      console.log("[DB] Draft deleted:", id);
      resolve(true);
    };
  });
}

// ── SUBMISSIONS ──────────────────────────────────────────────────────────

export async function saveSubmission(submission) {
  if (!dbInstance) await initDB();
  return new Promise((resolve, reject) => {
    const tx = dbInstance.transaction([STORE_SUBMISSIONS], "readwrite");
    const store = tx.objectStore(STORE_SUBMISSIONS);
    const req = store.add(submission);

    req.onerror = () => reject(new Error("Failed to save submission"));
    req.onsuccess = () => {
      console.log("[DB] Submission saved:", submission.id);
      resolve(submission.id);
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

export async function getAllSubmissions() {
  if (!dbInstance) await initDB();
  return new Promise((resolve, reject) => {
    const tx = dbInstance.transaction([STORE_SUBMISSIONS], "readonly");
    const store = tx.objectStore(STORE_SUBMISSIONS);
    const req = store.getAll();

    req.onerror = () => reject(new Error("Failed to get submissions"));
    req.onsuccess = () => resolve(req.result || []);
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
    req.onsuccess = () => resolve(req.result || []);
  });
}

export async function updateSubmission(id, updates) {
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
    req.onsuccess = () => {
      console.log("[DB] Submission deleted:", id);
      resolve(true);
    };
  });
}

// ── CONVERSIONS ──────────────────────────────────────────────────────────

/**
 * Convert a draft to a submission (when user clicks Submit)
 */
export async function convertDraftToSubmission(draftId) {
  const draft = await getDraft(draftId);
  if (!draft) throw new Error("Draft not found");

  const submission = {
    id: crypto.randomUUID(),
    status: "local", // Ready to sync
    item_name: draft.item_name,
    formData: draft.formData,
    signatures: draft.signatures,
    submitted_at: Date.now(),
    monday_item_id: null,
    sync_attempts: 0,
    last_sync_error: null,
    synced_at: null,
  };

  await saveSubmission(submission);
  await deleteDraft(draftId);

  console.log("[DB] Draft converted to submission:", submission.id);
  return submission;
}

// ── CLEANUP ──────────────────────────────────────────────────────────────

/**
 * Delete old synced submissions (30+ days)
 */
export async function cleanupOldSubmissions(daysOld = 30) {
  const allSubs = await getAllSubmissions();
  const cutoff = Date.now() - daysOld * 24 * 60 * 60 * 1000;

  let deleted = 0;
  for (const sub of allSubs) {
    if (sub.status === "synced" && sub.synced_at < cutoff) {
      await deleteSubmission(sub.id);
      deleted++;
    }
  }

  console.log(`[DB] Cleaned up ${deleted} old submissions`);
  return deleted;
}

/**
 * Delete old drafts (30+ days)
 */
export async function cleanupOldDrafts(daysOld = 30) {
  const allDrafts = await getAllDrafts();
  const cutoff = Date.now() - daysOld * 24 * 60 * 60 * 1000;

  let deleted = 0;
  for (const draft of allDrafts) {
    if (draft.updated_at < cutoff) {
      await deleteDraft(draft.id);
      deleted++;
    }
  }

  console.log(`[DB] Cleaned up ${deleted} old drafts`);
  return deleted;
}
