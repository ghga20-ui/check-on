// IndexedDB persistence for the E2E sync key.
//
// The key is received once from the desktop via the pairing QR / manual code
// and never leaves the device. Like db.ts, every function degrades to a no-op
// when IndexedDB is unavailable so callers can use them unconditionally.

import { hasIndexedDB, KEYS_STORE, openDb } from "./db";

const KEY_ID = "syncKey";

export async function saveSyncKey(bytes: Uint8Array): Promise<void> {
  if (!hasIndexedDB()) return;
  const db = await openDb();
  try {
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(KEYS_STORE, "readwrite");
      tx.objectStore(KEYS_STORE).put(bytes, KEY_ID);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
      tx.onabort = () => reject(tx.error);
    });
  } finally {
    db.close();
  }
}

export async function loadSyncKey(): Promise<Uint8Array | null> {
  if (!hasIndexedDB()) return null;
  const db = await openDb();
  try {
    return await new Promise((resolve, reject) => {
      const request = db.transaction(KEYS_STORE, "readonly").objectStore(KEYS_STORE).get(KEY_ID);
      request.onsuccess = () => resolve(request.result ? new Uint8Array(request.result) : null);
      request.onerror = () => reject(request.error);
    });
  } finally {
    db.close();
  }
}

export async function clearSyncKey(): Promise<void> {
  if (!hasIndexedDB()) return;
  const db = await openDb();
  try {
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(KEYS_STORE, "readwrite");
      tx.objectStore(KEYS_STORE).delete(KEY_ID);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
      tx.onabort = () => reject(tx.error);
    });
  } finally {
    db.close();
  }
}
