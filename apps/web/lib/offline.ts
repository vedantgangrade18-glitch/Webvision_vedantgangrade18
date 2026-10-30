"use client";

import Dexie, { type Table } from "dexie";
import { api } from "./api";
import { compressPhoto, uploadMedia, type UploadState } from "./media";

/** Offline-first Snap + Speak (Part 2 §9.2): drafts and their media live in IndexedDB; an outbox
 *  uploads media (resumably), creates the draft listing and records the job to follow. */

export interface OutboxItem {
  id?: number;
  createdAt: number;
  status: "pending" | "uploading" | "submitted" | "failed";
  photos: Blob[];
  voice?: Blob | null;
  voiceDuration?: number | null;
  transcript?: string;
  sourceLang: string;
  uploads: Record<string, UploadState>; // "photo-0" | "voice" → resumable state
  mediaIds: Record<string, string>;
  listingId?: string;
  jobId?: string;
  error?: string;
  attempts: number;
}

class KaruDB extends Dexie {
  outbox!: Table<OutboxItem, number>;

  constructor() {
    super("karu");
    this.version(1).stores({ outbox: "++id, status, createdAt" });
  }
}

let _db: KaruDB | null = null;
export function db(): KaruDB {
  if (!_db) _db = new KaruDB();
  return _db;
}

export async function enqueueDraft(item: Omit<OutboxItem, "id" | "status" | "uploads" | "mediaIds" | "attempts" | "createdAt">): Promise<number> {
  const photos = await Promise.all(item.photos.map((p) => compressPhoto(p)));
  const id = await db().outbox.add({ ...item, photos, status: "pending", uploads: {}, mediaIds: {}, attempts: 0, createdAt: Date.now() });
  registerBackgroundSync();
  return id;
}

let running: Promise<void> | null = null;
type Listener = () => void;
const listeners = new Set<Listener>();
export function onOutboxChange(fn: Listener): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}
function emit() {
  listeners.forEach((l) => l());
}

async function processItem(item: OutboxItem): Promise<void> {
  const table = db().outbox;
  await table.update(item.id!, { status: "uploading", error: undefined });
  emit();
  const save = async (patch: Partial<OutboxItem>) => {
    Object.assign(item, patch);
    await table.update(item.id!, patch);
  };
  for (let i = 0; i < item.photos.length; i++) {
    const key = `photo-${i}`;
    if (item.mediaIds[key]) continue;
    const id = await uploadMedia(item.photos[i], "photo", {
      state: item.uploads[key],
      onState: (s) => void save({ uploads: { ...item.uploads, [key]: s } }),
    });
    await save({ mediaIds: { ...item.mediaIds, [key]: id } });
  }
  if (item.voice && !item.mediaIds.voice) {
    const id = await uploadMedia(item.voice, "voice", {
      durationS: item.voiceDuration,
      state: item.uploads.voice,
      onState: (s) => void save({ uploads: { ...item.uploads, voice: s } }),
    });
    await save({ mediaIds: { ...item.mediaIds, voice: id } });
  }
  if (!item.listingId) {
    const photoIds = item.photos.map((_, i) => item.mediaIds[`photo-${i}`]);
    const res = await api<{ listing_id: string; job_id: string }>("/listings", {
      method: "POST",
      body: { photo_media_ids: photoIds, voice_media_id: item.mediaIds.voice || null, client_transcript: item.transcript || null, source_lang: item.sourceLang },
    });
    await save({ listingId: res.listing_id, jobId: res.job_id });
  }
  // Media blobs are no longer needed once the server has them.
  await save({ status: "submitted", photos: [], voice: null });
  emit();
}

export function processOutbox(): Promise<void> {
  if (running) return running;
  running = (async () => {
    if (typeof navigator !== "undefined" && !navigator.onLine) return;
    const items = await db().outbox.where("status").anyOf("pending", "uploading", "failed").toArray();
    for (const item of items) {
      if (item.status === "failed" && item.attempts >= 8) continue;
      try {
        await processItem(item);
      } catch (e) {
        await db().outbox.update(item.id!, { status: "failed", error: String((e as Error)?.message || e), attempts: item.attempts + 1 });
        emit();
        if (typeof navigator !== "undefined" && !navigator.onLine) break;
      }
    }
  })().finally(() => {
    running = null;
  });
  return running;
}

export async function retryItem(id: number): Promise<void> {
  await db().outbox.update(id, { status: "pending", attempts: 0 });
  emit();
  await processOutbox();
}

export async function pendingCount(): Promise<{ pending: number; failed: number }> {
  const all = await db().outbox.toArray();
  return {
    pending: all.filter((i) => i.status === "pending" || i.status === "uploading").length,
    failed: all.filter((i) => i.status === "failed").length,
  };
}

function registerBackgroundSync() {
  if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) return;
  navigator.serviceWorker.ready
    .then((reg) => (reg as ServiceWorkerRegistration & { sync?: { register(tag: string): Promise<void> } }).sync?.register("karu-outbox"))
    .catch(() => undefined);
}

let wired = false;
/** Retry on reconnect, on app open and when the service worker's Background Sync fires. */
export function wireOutbox(): void {
  if (wired || typeof window === "undefined") return;
  wired = true;
  window.addEventListener("online", () => void processOutbox());
  navigator.serviceWorker?.addEventListener("message", (e) => {
    if (e.data?.type === "karu-sync") void processOutbox();
  });
  void processOutbox();
}
