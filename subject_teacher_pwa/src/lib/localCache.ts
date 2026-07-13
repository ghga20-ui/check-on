// Stale-while-revalidate cache for the home screen's Drive snapshot.
//
// On a successful loadAll() the result (LoadedDriveData) is stored in IndexedDB
// together with the month it covers and a save timestamp. On next launch Root
// renders this snapshot instantly (stale=true) without opening a Google window,
// then refreshes from Drive only on an explicit user gesture.
//
// Why IndexedDB and not localStorage: the snapshot can contain student names,
// which stay on-device but must never be dumped as bulk plaintext in
// localStorage. Access tokens are NEVER cached — they remain memory-only per
// the auth design.
//
// Like keyStore/db, every function degrades to a no-op / null when IndexedDB is
// unavailable (e.g. jsdom) so callers can use them unconditionally.

import { CACHE_STORE, hasIndexedDB, openDb } from "./db";
import type { LoadedDriveData } from "./driveData";

const CACHE_ID = "driveData";

export interface CachedDriveData {
  /** The last successfully loaded Drive snapshot. */
  data: LoadedDriveData;
  /** Month (YYYY-MM) the attendance in `data` covers. */
  month: string;
  /** Epoch ms when the snapshot was cached. */
  savedAt: number;
}

/** Persist the latest Drive snapshot. No-op when storage is unavailable. */
export async function saveDriveCache(data: LoadedDriveData, month: string): Promise<void> {
  if (!hasIndexedDB()) return;
  const record: CachedDriveData = { data, month, savedAt: Date.now() };
  const db = await openDb();
  try {
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(CACHE_STORE, "readwrite");
      tx.objectStore(CACHE_STORE).put(record, CACHE_ID);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
      tx.onabort = () => reject(tx.error);
    });
  } finally {
    db.close();
  }
}

/** Load the cached snapshot, or null when none is stored / storage is off. */
export async function loadDriveCache(): Promise<CachedDriveData | null> {
  if (!hasIndexedDB()) return null;
  const db = await openDb();
  try {
    return await new Promise<CachedDriveData | null>((resolve, reject) => {
      const request = db
        .transaction(CACHE_STORE, "readonly")
        .objectStore(CACHE_STORE)
        .get(CACHE_ID);
      request.onsuccess = () => resolve((request.result as CachedDriveData | undefined) ?? null);
      request.onerror = () => reject(request.error);
    });
  } finally {
    db.close();
  }
}

/** Delete the cached snapshot (called on sign-out / disconnect). */
export async function clearDriveCache(): Promise<void> {
  if (!hasIndexedDB()) return;
  const db = await openDb();
  try {
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(CACHE_STORE, "readwrite");
      tx.objectStore(CACHE_STORE).delete(CACHE_ID);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
      tx.onabort = () => reject(tx.error);
    });
  } finally {
    db.close();
  }
}
