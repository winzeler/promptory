package promptdis

import (
	"strings"
	"sync"
	"time"
)

// CacheStats reports the current state of the LRU cache.
type CacheStats struct {
	Size    int           `json:"size"`
	MaxSize int           `json:"max_size"`
	TTL     time.Duration `json:"ttl"`
}

// cacheEntry is a node in the doubly-linked list used by lruCache.
type cacheEntry struct {
	key       string
	value     *Prompt
	etag      string
	expiresAt time.Time
	prev      *cacheEntry
	next      *cacheEntry
}

// lruCache is a thread-safe LRU cache with TTL support.
// It uses a doubly-linked list for O(1) eviction and a map for O(1) lookups.
type lruCache struct {
	mu      sync.RWMutex
	entries map[string]*cacheEntry
	head    *cacheEntry // most recently used
	tail    *cacheEntry // least recently used (eviction candidate)
	maxSize int
	ttl     time.Duration
}

// newLRUCache creates a new LRU cache with the given max size and TTL.
func newLRUCache(maxSize int, ttl time.Duration) *lruCache {
	return &lruCache{
		entries: make(map[string]*cacheEntry),
		maxSize: maxSize,
		ttl:     ttl,
	}
}

// get retrieves a cache entry. Returns (entry, true) if the entry exists
// and has not expired, (entry, false) if expired but present (stale),
// or (nil, false) if not found.
func (c *lruCache) get(key string) (entry *cacheEntry, fresh bool) {
	c.mu.Lock()
	defer c.mu.Unlock()

	e, ok := c.entries[key]
	if !ok {
		return nil, false
	}

	c.moveToFront(e)

	if time.Now().Before(e.expiresAt) {
		return e, true
	}
	return e, false
}

// set adds or updates an entry in the cache with the given TTL.
func (c *lruCache) set(key string, value *Prompt, etag string) {
	c.mu.Lock()
	defer c.mu.Unlock()

	if e, ok := c.entries[key]; ok {
		e.value = value
		e.etag = etag
		e.expiresAt = time.Now().Add(c.ttl)
		c.moveToFront(e)
		return
	}

	e := &cacheEntry{
		key:       key,
		value:     value,
		etag:      etag,
		expiresAt: time.Now().Add(c.ttl),
	}
	c.entries[key] = e
	c.pushFront(e)

	if len(c.entries) > c.maxSize {
		c.evictLRU()
	}
}

// refreshTTL resets the expiry time for an existing entry (e.g., after a 304 response).
func (c *lruCache) refreshTTL(key string) {
	c.mu.Lock()
	defer c.mu.Unlock()

	if e, ok := c.entries[key]; ok {
		e.expiresAt = time.Now().Add(c.ttl)
		c.moveToFront(e)
	}
}

// invalidate removes a specific cache entry. Returns true if the entry existed.
func (c *lruCache) invalidate(key string) bool {
	c.mu.Lock()
	defer c.mu.Unlock()

	e, ok := c.entries[key]
	if !ok {
		return false
	}
	c.remove(e)
	delete(c.entries, key)
	return true
}

// invalidateByPrefix removes all entries whose keys start with prefix.
// Returns the count of entries removed.
func (c *lruCache) invalidateByPrefix(prefix string) int {
	c.mu.Lock()
	defer c.mu.Unlock()

	var toDelete []string
	for k := range c.entries {
		if strings.HasPrefix(k, prefix) {
			toDelete = append(toDelete, k)
		}
	}
	for _, k := range toDelete {
		e := c.entries[k]
		c.remove(e)
		delete(c.entries, k)
	}
	return len(toDelete)
}

// clear removes all entries from the cache.
func (c *lruCache) clear() {
	c.mu.Lock()
	defer c.mu.Unlock()

	c.entries = make(map[string]*cacheEntry)
	c.head = nil
	c.tail = nil
}

// stats returns the current cache statistics.
func (c *lruCache) stats() CacheStats {
	c.mu.RLock()
	defer c.mu.RUnlock()

	return CacheStats{
		Size:    len(c.entries),
		MaxSize: c.maxSize,
		TTL:     c.ttl,
	}
}

// --- Doubly-linked list operations (caller must hold lock) ---

func (c *lruCache) pushFront(e *cacheEntry) {
	e.prev = nil
	e.next = c.head
	if c.head != nil {
		c.head.prev = e
	}
	c.head = e
	if c.tail == nil {
		c.tail = e
	}
}

func (c *lruCache) remove(e *cacheEntry) {
	if e.prev != nil {
		e.prev.next = e.next
	} else {
		c.head = e.next
	}
	if e.next != nil {
		e.next.prev = e.prev
	} else {
		c.tail = e.prev
	}
	e.prev = nil
	e.next = nil
}

func (c *lruCache) moveToFront(e *cacheEntry) {
	if c.head == e {
		return
	}
	c.remove(e)
	c.pushFront(e)
}

func (c *lruCache) evictLRU() {
	if c.tail == nil {
		return
	}
	delete(c.entries, c.tail.key)
	c.remove(c.tail)
}
