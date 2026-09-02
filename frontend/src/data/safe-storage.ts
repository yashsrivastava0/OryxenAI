// Safe storage wrapper (docs/Frontend/05 §18, §19 Phase 5).
// Prevents unhandled DOMExceptions (SecurityError, QuotaExceededError)
// in private browsing, cross-origin iframes, or restricted webviews by
// falling back transparently to an in-memory dictionary.

const memoryFallback = new Map<string, string>();

function isStorageAvailable(type: "sessionStorage" | "localStorage"): boolean {
  if (typeof window === "undefined") return false;
  try {
    const storage = window[type];
    if (!storage) return false;
    const testKey = "__oryxenai_storage_probe__";
    storage.setItem(testKey, "1");
    storage.removeItem(testKey);
    return true;
  } catch {
    return false;
  }
}

const hasSessionStorage = isStorageAvailable("sessionStorage");
const hasLocalStorage = isStorageAvailable("localStorage");

export const safeSessionStorage = {
  getItem(key: string): string | null {
    if (hasSessionStorage) {
      try {
        return window.sessionStorage.getItem(key);
      } catch {
        // Fall back to in-memory
      }
    }
    return memoryFallback.get(`session:${key}`) ?? null;
  },

  setItem(key: string, value: string): void {
    if (hasSessionStorage) {
      try {
        window.sessionStorage.setItem(key, value);
        return;
      } catch {
        // Quota exceeded or security error -> fall back to in-memory
      }
    }
    memoryFallback.set(`session:${key}`, value);
  },

  removeItem(key: string): void {
    if (hasSessionStorage) {
      try {
        window.sessionStorage.removeItem(key);
      } catch {
        // Fall back to in-memory
      }
    }
    memoryFallback.delete(`session:${key}`);
  },

  clear(): void {
    if (hasSessionStorage) {
      try {
        window.sessionStorage.clear();
      } catch {
        // Fall back to in-memory
      }
    }
    for (const k of Array.from(memoryFallback.keys())) {
      if (k.startsWith("session:")) memoryFallback.delete(k);
    }
  },
};

export const safeLocalStorage = {
  getItem(key: string): string | null {
    if (hasLocalStorage) {
      try {
        return window.localStorage.getItem(key);
      } catch {
        // Fall back to in-memory
      }
    }
    return memoryFallback.get(`local:${key}`) ?? null;
  },

  setItem(key: string, value: string): void {
    if (hasLocalStorage) {
      try {
        window.localStorage.setItem(key, value);
        return;
      } catch {
        // Quota exceeded or security error -> fall back to in-memory
      }
    }
    memoryFallback.set(`local:${key}`, value);
  },

  removeItem(key: string): void {
    if (hasLocalStorage) {
      try {
        window.localStorage.removeItem(key);
      } catch {
        // Fall back to in-memory
      }
    }
    memoryFallback.delete(`local:${key}`);
  },
};
