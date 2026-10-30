"use client";

import { api } from "./api";

/** Client-side photo compression: ≤ 1600 px long edge, JPEG, stepping quality down to ≤ 500 KB (Part 2 §9.1). */
export async function compressPhoto(file: Blob, maxSide = 1600, maxBytes = 500 * 1024): Promise<Blob> {
  const bitmap = await createImageBitmap(file, { imageOrientation: "from-image" } as ImageBitmapOptions).catch(() => null);
  if (!bitmap) return file;
  const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height));
  const w = Math.round(bitmap.width * scale);
  const h = Math.round(bitmap.height * scale);
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  if (!ctx) return file;
  ctx.drawImage(bitmap, 0, 0, w, h);
  bitmap.close?.();
  let quality = 0.85;
  let blob: Blob | null = null;
  for (let i = 0; i < 6; i++) {
    blob = await new Promise<Blob | null>((r) => canvas.toBlob(r, "image/jpeg", quality));
    if (blob && blob.size <= maxBytes) break;
    quality -= 0.1;
  }
  return blob || file;
}

/** Mean luminance of a photo (0–255) for the "photo too dark" warning on A06. */
export async function brightness(file: Blob): Promise<number> {
  const bitmap = await createImageBitmap(file).catch(() => null);
  if (!bitmap) return 128;
  const c = document.createElement("canvas");
  c.width = 48;
  c.height = 48;
  const ctx = c.getContext("2d");
  if (!ctx) return 128;
  ctx.drawImage(bitmap, 0, 0, 48, 48);
  const d = ctx.getImageData(0, 0, 48, 48).data;
  let sum = 0;
  for (let i = 0; i < d.length; i += 4) sum += 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2];
  return sum / (d.length / 4);
}

export function mediaDuration(file: Blob, kind: "video" | "audio"): Promise<number | null> {
  return new Promise((resolve) => {
    const el = document.createElement(kind);
    el.preload = "metadata";
    const url = URL.createObjectURL(file);
    el.onloadedmetadata = () => {
      const d = el.duration;
      URL.revokeObjectURL(url);
      resolve(Number.isFinite(d) ? d : null);
    };
    el.onerror = () => {
      URL.revokeObjectURL(url);
      resolve(null);
    };
    el.src = url;
  });
}

interface StartUpload {
  media_id: string;
  part_size: number;
  part_count: number;
  parts: { part_number: number; url: string }[];
}

export interface UploadState {
  mediaId?: string;
  done?: { part_number: number; etag: string | null }[];
}

/**
 * Resumable multipart upload: presigned part URLs (S3) or token URLs (local), each part retried
 * with backoff; `state` can be persisted (IndexedDB) to resume after an app restart.
 */
export async function uploadMedia(
  file: Blob,
  kind: "photo" | "voice" | "video" | "document",
  opts: { durationS?: number | null; onProgress?: (p: number) => void; state?: UploadState; onState?: (s: UploadState) => void } = {},
): Promise<string> {
  const mime = file.type || (kind === "photo" ? "image/jpeg" : kind === "voice" ? "audio/webm" : "video/mp4");
  let start: StartUpload;
  const state: UploadState = { ...(opts.state || {}) };
  if (state.mediaId) {
    const total = Math.max(1, Math.ceil(file.size / (5 * 1024 * 1024)));
    const numbers = Array.from({ length: total }, (_, i) => i + 1).filter((n) => !(state.done || []).some((d) => d.part_number === n));
    const more = await api<{ parts: { part_number: number; url: string }[] }>(`/media/uploads/${state.mediaId}/parts`, {
      method: "POST",
      body: { part_numbers: numbers },
    });
    start = { media_id: state.mediaId, part_size: 5 * 1024 * 1024, part_count: total, parts: more.parts };
  } else {
    start = await api<StartUpload>("/media/uploads", { method: "POST", body: { kind, mime, bytes: file.size, duration_s: opts.durationS ?? null } });
    state.mediaId = start.media_id;
    state.done = [];
    opts.onState?.(state);
  }
  const done = [...(state.done || [])];
  for (const part of start.parts) {
    const chunk = file.slice((part.part_number - 1) * start.part_size, part.part_number * start.part_size);
    let etag: string | null = null;
    for (let attempt = 0; attempt < 5; attempt++) {
      try {
        const res = await fetch(part.url, { method: "PUT", body: chunk, credentials: "omit" });
        if (!res.ok) throw new Error(`part ${part.part_number}: ${res.status}`);
        etag = res.headers.get("ETag");
        break;
      } catch (e) {
        if (attempt === 4) throw e;
        await new Promise((r) => setTimeout(r, 800 * 2 ** attempt));
      }
    }
    done.push({ part_number: part.part_number, etag });
    state.done = done;
    opts.onState?.({ ...state });
    opts.onProgress?.(done.length / start.part_count);
  }
  const complete = await api<{ id: string }>(`/media/uploads/${start.media_id}/complete`, {
    method: "POST",
    body: { parts: done.sort((a, b) => a.part_number - b.part_number), duration_s: opts.durationS ?? null },
  });
  return complete.id;
}

export async function uploadPhoto(file: Blob, onProgress?: (p: number) => void): Promise<string> {
  const small = await compressPhoto(file);
  return uploadMedia(small, "photo", { onProgress });
}
