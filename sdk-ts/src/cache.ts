interface CacheEntry<T> {
  value: T;
  etag: string | null;
  expiresAt: number;
}

/**
 * LRU cache with TTL support using Map insertion order.
 * Map preserves insertion order — oldest entries are evicted first.
 */
export class LRUCache<T> {
  private map = new Map<string, CacheEntry<T>>();
  private maxSize: number;
  private ttlMs: number;

  constructor(maxSize = 100, ttlMs = 60_000) {
    this.maxSize = maxSize;
    this.ttlMs = ttlMs;
  }

  get(key: string): { value: T; etag: string | null } | null {
    const entry = this.map.get(key);
    if (!entry) return null;

    if (Date.now() > entry.expiresAt) {
      this.map.delete(key);
      return null;
    }

    // Move to end (most recently used)
    this.map.delete(key);
    this.map.set(key, entry);

    return { value: entry.value, etag: entry.etag };
  }

  set(key: string, value: T, etag: string | null = null): void {
    // Delete first to reset position
    this.map.delete(key);

    // Evict oldest if at capacity
    if (this.map.size >= this.maxSize) {
      const firstKey = this.map.keys().next().value;
      if (firstKey !== undefined) {
        this.map.delete(firstKey);
      }
    }

    this.map.set(key, {
      value,
      etag,
      expiresAt: Date.now() + this.ttlMs,
    });
  }

  invalidate(key: string): boolean {
    return this.map.delete(key);
  }

  clear(): void {
    this.map.clear();
  }

  get size(): number {
    return this.map.size;
  }

  stats(): { size: number; maxSize: number; ttlMs: number } {
    return { size: this.map.size, maxSize: this.maxSize, ttlMs: this.ttlMs };
  }
}
