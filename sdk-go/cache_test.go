package promptdis

import (
	"sync"
	"testing"
	"time"
)

func TestLRUCache_GetSet(t *testing.T) {
	c := newLRUCache(10, time.Minute)
	p := &Prompt{ID: "1", Name: "test"}
	c.set("key1", p, "etag1")

	entry, fresh := c.get("key1")
	if entry == nil {
		t.Fatal("expected non-nil entry")
	}
	if !fresh {
		t.Error("expected fresh entry")
	}
	if entry.value.ID != "1" {
		t.Errorf("ID = %q, want %q", entry.value.ID, "1")
	}
	if entry.etag != "etag1" {
		t.Errorf("etag = %q, want %q", entry.etag, "etag1")
	}
}

func TestLRUCache_Miss(t *testing.T) {
	c := newLRUCache(10, time.Minute)
	entry, fresh := c.get("missing")
	if entry != nil {
		t.Error("expected nil entry for cache miss")
	}
	if fresh {
		t.Error("expected fresh=false for cache miss")
	}
}

func TestLRUCache_TTLExpiry(t *testing.T) {
	c := newLRUCache(10, 50*time.Millisecond)
	c.set("key1", &Prompt{ID: "1"}, "")

	// Should be fresh immediately
	entry, fresh := c.get("key1")
	if entry == nil || !fresh {
		t.Fatal("expected fresh entry immediately after set")
	}

	// Wait for TTL to expire
	time.Sleep(60 * time.Millisecond)

	entry, fresh = c.get("key1")
	if entry == nil {
		t.Fatal("expected stale entry (not nil) after TTL")
	}
	if fresh {
		t.Error("expected fresh=false after TTL expiry")
	}
}

func TestLRUCache_LRUEviction(t *testing.T) {
	c := newLRUCache(2, time.Minute)
	c.set("a", &Prompt{ID: "a"}, "")
	c.set("b", &Prompt{ID: "b"}, "")
	c.set("c", &Prompt{ID: "c"}, "") // Should evict "a"

	entry, _ := c.get("a")
	if entry != nil {
		t.Error("expected 'a' to be evicted")
	}

	entry, _ = c.get("b")
	if entry == nil {
		t.Error("expected 'b' to still be cached")
	}

	entry, _ = c.get("c")
	if entry == nil {
		t.Error("expected 'c' to still be cached")
	}
}

func TestLRUCache_MoveToFront(t *testing.T) {
	c := newLRUCache(2, time.Minute)
	c.set("a", &Prompt{ID: "a"}, "")
	c.set("b", &Prompt{ID: "b"}, "")

	// Access "a" to move it to front
	c.get("a")

	// Add "c" — should evict "b" (not "a" since we accessed it)
	c.set("c", &Prompt{ID: "c"}, "")

	entry, _ := c.get("a")
	if entry == nil {
		t.Error("expected 'a' to be retained after access")
	}

	entry, _ = c.get("b")
	if entry != nil {
		t.Error("expected 'b' to be evicted")
	}
}

func TestLRUCache_RefreshTTL(t *testing.T) {
	c := newLRUCache(10, 80*time.Millisecond)
	c.set("key1", &Prompt{ID: "1"}, "")

	// Wait until near expiry
	time.Sleep(60 * time.Millisecond)

	// Refresh TTL
	c.refreshTTL("key1")

	// Wait past original expiry but within refreshed TTL
	time.Sleep(40 * time.Millisecond)

	entry, fresh := c.get("key1")
	if entry == nil || !fresh {
		t.Error("expected fresh entry after TTL refresh")
	}
}

func TestLRUCache_Invalidate(t *testing.T) {
	c := newLRUCache(10, time.Minute)
	c.set("key1", &Prompt{ID: "1"}, "")

	removed := c.invalidate("key1")
	if !removed {
		t.Error("expected invalidate to return true")
	}

	entry, _ := c.get("key1")
	if entry != nil {
		t.Error("expected nil entry after invalidate")
	}

	// Invalidating non-existent key
	if c.invalidate("missing") {
		t.Error("expected invalidate to return false for missing key")
	}
}

func TestLRUCache_InvalidateByPrefix(t *testing.T) {
	c := newLRUCache(10, time.Minute)
	c.set("id:abc", &Prompt{ID: "abc"}, "")
	c.set("id:def", &Prompt{ID: "def"}, "")
	c.set("name:org/app/test:any", &Prompt{ID: "1"}, "")

	count := c.invalidateByPrefix("id:")
	if count != 2 {
		t.Errorf("invalidateByPrefix() = %d, want 2", count)
	}

	entry, _ := c.get("name:org/app/test:any")
	if entry == nil {
		t.Error("expected name-prefixed entry to remain")
	}
}

func TestLRUCache_Clear(t *testing.T) {
	c := newLRUCache(10, time.Minute)
	c.set("a", &Prompt{ID: "a"}, "")
	c.set("b", &Prompt{ID: "b"}, "")

	c.clear()

	stats := c.stats()
	if stats.Size != 0 {
		t.Errorf("Size = %d, want 0 after clear", stats.Size)
	}
}

func TestLRUCache_Stats(t *testing.T) {
	c := newLRUCache(50, 5*time.Second)
	c.set("a", &Prompt{ID: "a"}, "")
	c.set("b", &Prompt{ID: "b"}, "")

	stats := c.stats()
	if stats.Size != 2 {
		t.Errorf("Size = %d, want 2", stats.Size)
	}
	if stats.MaxSize != 50 {
		t.Errorf("MaxSize = %d, want 50", stats.MaxSize)
	}
	if stats.TTL != 5*time.Second {
		t.Errorf("TTL = %v, want 5s", stats.TTL)
	}
}

func TestLRUCache_ConcurrentAccess(t *testing.T) {
	c := newLRUCache(100, time.Minute)

	var wg sync.WaitGroup
	for i := 0; i < 50; i++ {
		wg.Add(2)
		key := "key" + string(rune('a'+i%26))
		go func(k string) {
			defer wg.Done()
			c.set(k, &Prompt{ID: k}, "")
		}(key)
		go func(k string) {
			defer wg.Done()
			c.get(k) // may or may not find it
		}(key)
	}
	wg.Wait()

	// If we get here without panic or data race, the test passes.
	stats := c.stats()
	if stats.Size < 0 || stats.Size > 100 {
		t.Errorf("unexpected cache size: %d", stats.Size)
	}
}

func TestLRUCache_UpdateExisting(t *testing.T) {
	c := newLRUCache(10, time.Minute)
	c.set("key1", &Prompt{ID: "old"}, "etag1")
	c.set("key1", &Prompt{ID: "new"}, "etag2")

	entry, _ := c.get("key1")
	if entry == nil {
		t.Fatal("expected non-nil entry")
	}
	if entry.value.ID != "new" {
		t.Errorf("ID = %q, want %q", entry.value.ID, "new")
	}
	if entry.etag != "etag2" {
		t.Errorf("etag = %q, want %q", entry.etag, "etag2")
	}

	// Should not have duplicate entries
	stats := c.stats()
	if stats.Size != 1 {
		t.Errorf("Size = %d, want 1", stats.Size)
	}
}
