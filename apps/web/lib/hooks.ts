"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { ApiError, api } from "./api";
import type { Job, Me, PublicConfig } from "./types";

export function useMe() {
  return useQuery<Me | null>({
    queryKey: ["me"],
    queryFn: async () => {
      try {
        return await api<Me>("/me");
      } catch (e) {
        if (e instanceof ApiError && (e.status === 401 || e.status === 403)) return null;
        throw e;
      }
    },
    staleTime: 60_000,
  });
}

export function usePublicConfig() {
  return useQuery<PublicConfig>({ queryKey: ["config"], queryFn: () => api<PublicConfig>("/config/public"), staleTime: 300_000 });
}

/** Job progress over SSE with a 3 s polling fallback (Part 2 §9.5). */
export function useJob(
  jobId: string | null | undefined,
  onDone?: (job: Job) => void,
  onProgress?: (job: Job) => void
) {
  const [job, setJob] = useState<Job | null>(null);
  const doneRef = useRef(onDone);
  const progressRef = useRef(onProgress);
  useEffect(() => {
    doneRef.current = onDone;
  }, [onDone]);
  useEffect(() => {
    progressRef.current = onProgress;
  }, [onProgress]);

  useEffect(() => {
    if (!jobId) return;
    let closed = false;
    let es: EventSource | null = null;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const finish = (j: Job) => {
      setJob(j);
      progressRef.current?.(j);
      if (j.status === "completed" || j.status === "failed") {
        closed = true;
        es?.close();
        doneRef.current?.(j);
      }
    };
    const poll = async () => {
      if (closed) return;
      try {
        finish(await api<Job>(`/jobs/${jobId}`));
      } catch {
        /* keep polling */
      }
      if (!closed) timer = setTimeout(poll, 3000);
    };
    if (typeof EventSource !== "undefined") {
      es = new EventSource(`/api/v1/jobs/${jobId}/events`, { withCredentials: true });
      const handler = (e: MessageEvent) => finish(JSON.parse(e.data));
      es.addEventListener("progress", handler as EventListener);
      es.addEventListener("done", handler as EventListener);
      es.onerror = () => {
        es?.close();
        es = null;
        if (!closed) void poll();
      };
    } else {
      void poll();
    }
    return () => {
      closed = true;
      es?.close();
      if (timer) clearTimeout(timer);
    };
  }, [jobId]);
  return job;
}

export function useOnline(): boolean {
  const [online, setOnline] = useState(true);
  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    update();
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);
  return online;
}

export function useInvalidate() {
  const qc = useQueryClient();
  return (...keys: unknown[][]) => Promise.all(keys.map((k) => qc.invalidateQueries({ queryKey: k })));
}
