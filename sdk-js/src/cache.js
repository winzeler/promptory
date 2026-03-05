/**
 * LRU cache with TTL support using Map insertion order.
 * Map preserves insertion order — oldest entries are evicted first.
 */
export class LRUCache {
  /** @type {Map<string, {value: *, etag: string|null, expiresAt: number}>} */
  #map = new Map();
  #maxSize;
  #ttlMs;

  /**
   * @param {number} [maxSize=100]
   * @param {number} [ttlMs=60000]
   */
  constructor(maxSize = 100, ttlMs = 60_000) {
    this.#maxSize = maxSize;
    this.#ttlMs = ttlMs;
  }

  /**
   * @param {string} key
   * @returns {{ value: *, etag: string|null } | null}
   */
  get(key) {
    const entry = this.#map.get(key);
    if (!entry) return null;

    if (Date.now() > entry.expiresAt) {
      this.#map.delete(key);
      return null;
    }

    // Move to end (most recently used)
    this.#map.delete(key);
    this.#map.set(key, entry);

    return { value: entry.value, etag: entry.etag };
  }

  /**
   * @param {string} key
   * @param {*} value
   * @param {string|null} [etag=null]
   */
  set(key, value, etag = null) {
    // Delete first to reset position
    this.#map.delete(key);

    // Evict oldest if at capacity
    if (this.#map.size >= this.#maxSize) {
      const firstKey = this.#map.keys().next().value;
      if (firstKey !== undefined) {
        this.#map.delete(firstKey);
      }
    }

    this.#map.set(key, {
      value,
      etag,
      expiresAt: Date.now() + this.#ttlMs,
    });
  }

  /** @param {string} key */
  invalidate(key) {
    return this.#map.delete(key);
  }

  clear() {
    this.#map.clear();
  }

  get size() {
    return this.#map.size;
  }

  /** @returns {{ size: number, maxSize: number, ttlMs: number }} */
  stats() {
    return { size: this.#map.size, maxSize: this.#maxSize, ttlMs: this.#ttlMs };
  }
}
