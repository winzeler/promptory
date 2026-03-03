import { useEffect, useRef } from "react";

const AUTOSAVE_INTERVAL = 30_000; // 30 seconds

export function useAutoSave(key: string, data: unknown) {
  const timerRef = useRef<ReturnType<typeof setInterval>>();

  useEffect(() => {
    timerRef.current = setInterval(() => {
      try {
        localStorage.setItem(`promptdis_draft_${key}`, JSON.stringify(data));
      } catch {
        // Storage full or unavailable
      }
    }, AUTOSAVE_INTERVAL);

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [key, data]);
}

export function loadDraft<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(`promptdis_draft_${key}`);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function clearDraft(key: string) {
  localStorage.removeItem(`promptdis_draft_${key}`);
}
