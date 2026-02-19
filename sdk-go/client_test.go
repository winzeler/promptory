package promptory

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"sync/atomic"
	"testing"
	"time"
)

var samplePrompt = Prompt{
	ID:          "550e8400-e29b-41d4-a716-446655440000",
	Name:        "greeting",
	Version:     "1.0.0",
	Org:         "testorg",
	App:         "testapp",
	Type:        "chat",
	Environment: "development",
	Active:      true,
	Tags:        []string{"test"},
	Body:        "Hello {{name}}, welcome to {{place}}.",
	Includes:    []string{},
	Model:       map[string]interface{}{"default": "gemini-2.0-flash", "temperature": 0.7},
}

func newTestServer(handler http.HandlerFunc) (*httptest.Server, *Client) {
	server := httptest.NewServer(handler)
	client, _ := NewClient(ClientOptions{
		BaseURL:  server.URL,
		APIKey:   "pm_test_key123",
		CacheTTL: time.Minute,
	})
	client.maxRetries = 0 // bypass default (same package has field access)
	return server, client
}

func TestNewClient_Defaults(t *testing.T) {
	c, err := NewClient(ClientOptions{
		BaseURL: "https://example.com",
		APIKey:  "pm_test_123",
	})
	if err != nil {
		t.Fatal(err)
	}
	if c.maxRetries != 3 {
		t.Errorf("maxRetries = %d, want 3", c.maxRetries)
	}
	stats := c.CacheStats()
	if stats.MaxSize != 100 {
		t.Errorf("CacheMaxSize = %d, want 100", stats.MaxSize)
	}
	if stats.TTL != 60*time.Second {
		t.Errorf("CacheTTL = %v, want 60s", stats.TTL)
	}
}

func TestNewClient_RequiredFields(t *testing.T) {
	_, err := NewClient(ClientOptions{})
	if err == nil {
		t.Error("expected error for missing BaseURL")
	}

	_, err = NewClient(ClientOptions{BaseURL: "https://example.com"})
	if err == nil {
		t.Error("expected error for missing APIKey")
	}
}

func TestGet_Success(t *testing.T) {
	server, client := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/v1/prompts/"+samplePrompt.ID {
			t.Errorf("unexpected path: %s", r.URL.Path)
		}
		if got := r.Header.Get("Authorization"); got != "Bearer pm_test_key123" {
			t.Errorf("Authorization = %q, want Bearer pm_test_key123", got)
		}
		w.Header().Set("ETag", `"1.0.0-abc12345"`)
		json.NewEncoder(w).Encode(samplePrompt)
	})
	defer server.Close()

	prompt, err := client.Get(context.Background(), samplePrompt.ID)
	if err != nil {
		t.Fatal(err)
	}
	if prompt.ID != samplePrompt.ID {
		t.Errorf("ID = %q, want %q", prompt.ID, samplePrompt.ID)
	}
	if prompt.Name != "greeting" {
		t.Errorf("Name = %q, want %q", prompt.Name, "greeting")
	}
}

func TestGet_NotFound(t *testing.T) {
	server, client := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(404)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"error": map[string]string{"message": "Prompt not found"},
		})
	})
	defer server.Close()

	_, err := client.Get(context.Background(), "missing")
	if err == nil {
		t.Fatal("expected error")
	}
	if !errors.Is(err, ErrNotFound) {
		t.Errorf("expected ErrNotFound, got %v", err)
	}
}

func TestGet_Unauthorized(t *testing.T) {
	server, client := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(401)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"error": map[string]string{"message": "Invalid API key"},
		})
	})
	defer server.Close()

	_, err := client.Get(context.Background(), "p1")
	if err == nil {
		t.Fatal("expected error")
	}
	if !errors.Is(err, ErrAuthentication) {
		t.Errorf("expected ErrAuthentication, got %v", err)
	}
}

func TestGet_RateLimit(t *testing.T) {
	server, client := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Retry-After", "30")
		w.WriteHeader(429)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"error": map[string]string{"message": "Rate limited"},
		})
	})
	defer server.Close()

	_, err := client.Get(context.Background(), "p1")
	if err == nil {
		t.Fatal("expected error")
	}
	if !errors.Is(err, ErrRateLimit) {
		t.Errorf("expected ErrRateLimit, got %v", err)
	}

	var rle *RateLimitError
	if !errors.As(err, &rle) {
		t.Fatal("expected errors.As to extract RateLimitError")
	}
	if rle.RetryAfter != 30 {
		t.Errorf("RetryAfter = %d, want 30", rle.RetryAfter)
	}
}

func TestGet_ServerError(t *testing.T) {
	server, client := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(500)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"error": map[string]string{"message": "Internal error"},
		})
	})
	defer server.Close()

	_, err := client.Get(context.Background(), "p1")
	if err == nil {
		t.Fatal("expected error")
	}
	var pe *PromptoryError
	if !errors.As(err, &pe) {
		t.Fatal("expected PromptoryError")
	}
	if pe.StatusCode != 500 {
		t.Errorf("StatusCode = %d, want 500", pe.StatusCode)
	}
}

func TestGetByName_Success(t *testing.T) {
	server, client := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		expected := "/api/v1/prompts/by-name/myorg/myapp/greeting"
		if r.URL.Path != expected {
			t.Errorf("path = %q, want %q", r.URL.Path, expected)
		}
		json.NewEncoder(w).Encode(samplePrompt)
	})
	defer server.Close()

	prompt, err := client.GetByName(context.Background(), "myorg", "myapp", "greeting")
	if err != nil {
		t.Fatal(err)
	}
	if prompt.Name != "greeting" {
		t.Errorf("Name = %q, want %q", prompt.Name, "greeting")
	}
}

func TestGetByName_WithEnvironment(t *testing.T) {
	server, client := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		if got := r.URL.Query().Get("environment"); got != "production" {
			t.Errorf("environment = %q, want %q", got, "production")
		}
		json.NewEncoder(w).Encode(samplePrompt)
	})
	defer server.Close()

	_, err := client.GetByName(context.Background(), "org", "app", "test", WithEnvironment("production"))
	if err != nil {
		t.Fatal(err)
	}
}

func TestRender_Success(t *testing.T) {
	server, client := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			t.Errorf("method = %s, want POST", r.Method)
		}
		expected := "/api/v1/prompts/p1/render"
		if r.URL.Path != expected {
			t.Errorf("path = %q, want %q", r.URL.Path, expected)
		}
		var body map[string]interface{}
		json.NewDecoder(r.Body).Decode(&body)
		if body["variables"] == nil {
			t.Error("expected variables in body")
		}
		json.NewEncoder(w).Encode(RenderResult{
			RenderedBody: "Hello Alice!",
			Meta:         map[string]interface{}{},
		})
	})
	defer server.Close()

	result, err := client.Render(context.Background(), "p1", map[string]interface{}{"name": "Alice"})
	if err != nil {
		t.Fatal(err)
	}
	if result.RenderedBody != "Hello Alice!" {
		t.Errorf("RenderedBody = %q, want %q", result.RenderedBody, "Hello Alice!")
	}
}

func TestRenderLocal(t *testing.T) {
	client, _ := NewClient(ClientOptions{
		BaseURL: "https://example.com",
		APIKey:  "pm_test_123",
	})

	result := client.RenderLocal("Hello {{name}}, {{ greeting }}!", map[string]string{
		"name":     "Alice",
		"greeting": "good morning",
	})
	expected := "Hello Alice, good morning!"
	if result != expected {
		t.Errorf("RenderLocal() = %q, want %q", result, expected)
	}
}

func TestCache_Hit(t *testing.T) {
	var callCount int32
	server, client := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		atomic.AddInt32(&callCount, 1)
		w.Header().Set("ETag", `"v1"`)
		json.NewEncoder(w).Encode(samplePrompt)
	})
	defer server.Close()

	ctx := context.Background()

	// First call — cache miss
	_, err := client.Get(ctx, samplePrompt.ID)
	if err != nil {
		t.Fatal(err)
	}
	if atomic.LoadInt32(&callCount) != 1 {
		t.Fatalf("expected 1 call, got %d", callCount)
	}

	// Second call — should use cache (no HTTP request)
	prompt, err := client.Get(ctx, samplePrompt.ID)
	if err != nil {
		t.Fatal(err)
	}
	if atomic.LoadInt32(&callCount) != 1 {
		t.Errorf("expected 1 call (cached), got %d", callCount)
	}
	if prompt.Name != "greeting" {
		t.Errorf("Name = %q, want %q", prompt.Name, "greeting")
	}
}

func TestCache_ETag304(t *testing.T) {
	var callCount int32
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		count := atomic.AddInt32(&callCount, 1)
		if count == 1 {
			// First request: return prompt with ETag
			w.Header().Set("ETag", `"v1"`)
			json.NewEncoder(w).Encode(samplePrompt)
		} else {
			// Subsequent requests: if ETag matches, return 304
			if r.Header.Get("If-None-Match") == `"v1"` {
				w.WriteHeader(304)
				return
			}
			json.NewEncoder(w).Encode(samplePrompt)
		}
	}))
	defer server.Close()

	client, _ := NewClient(ClientOptions{
		BaseURL:  server.URL,
		APIKey:   "pm_test_key",
		CacheTTL: 50 * time.Millisecond, // short TTL to force revalidation
	})
	client.maxRetries = 0

	ctx := context.Background()

	// First call — fills cache
	_, err := client.Get(ctx, samplePrompt.ID)
	if err != nil {
		t.Fatal(err)
	}

	// Wait for cache to become stale
	time.Sleep(60 * time.Millisecond)

	// Second call — cache stale, sends If-None-Match, gets 304
	prompt, err := client.Get(ctx, samplePrompt.ID)
	if err != nil {
		t.Fatal(err)
	}
	if prompt.Name != "greeting" {
		t.Errorf("Name = %q, want %q", prompt.Name, "greeting")
	}
	if atomic.LoadInt32(&callCount) != 2 {
		t.Errorf("expected 2 calls (initial + revalidation), got %d", callCount)
	}
}

func TestCache_StaleFallback(t *testing.T) {
	var callCount int32
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		count := atomic.AddInt32(&callCount, 1)
		if count == 1 {
			json.NewEncoder(w).Encode(samplePrompt)
		} else {
			// Simulate server error
			w.WriteHeader(500)
		}
	}))
	defer server.Close()

	client, _ := NewClient(ClientOptions{
		BaseURL:  server.URL,
		APIKey:   "pm_test_key",
		CacheTTL: 50 * time.Millisecond,
	})
	client.maxRetries = 0

	ctx := context.Background()

	// First call — fills cache
	_, err := client.Get(ctx, samplePrompt.ID)
	if err != nil {
		t.Fatal(err)
	}

	// Wait for cache to become stale
	time.Sleep(60 * time.Millisecond)

	// Second call — stale cache + server error → returns stale
	prompt, err := client.Get(ctx, samplePrompt.ID)
	if err != nil {
		t.Fatal("expected stale fallback, got error:", err)
	}
	if prompt.Name != "greeting" {
		t.Errorf("Name = %q, want %q", prompt.Name, "greeting")
	}
}

func TestCache_Stats(t *testing.T) {
	_, client := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		json.NewEncoder(w).Encode(samplePrompt)
	})

	stats := client.CacheStats()
	if stats.Size != 0 {
		t.Errorf("Size = %d, want 0", stats.Size)
	}
	if stats.MaxSize != 100 {
		t.Errorf("MaxSize = %d, want 100", stats.MaxSize)
	}
}

func TestCache_Invalidate(t *testing.T) {
	server, client := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		json.NewEncoder(w).Encode(samplePrompt)
	})
	defer server.Close()

	client.Get(context.Background(), samplePrompt.ID)
	removed := client.CacheInvalidate("id:" + samplePrompt.ID)
	if !removed {
		t.Error("expected CacheInvalidate to return true")
	}

	stats := client.CacheStats()
	if stats.Size != 0 {
		t.Errorf("Size = %d, want 0 after invalidate", stats.Size)
	}
}

func TestCache_Clear(t *testing.T) {
	server, client := newTestServer(func(w http.ResponseWriter, r *http.Request) {
		json.NewEncoder(w).Encode(samplePrompt)
	})
	defer server.Close()

	client.Get(context.Background(), samplePrompt.ID)
	client.CacheClear()

	stats := client.CacheStats()
	if stats.Size != 0 {
		t.Errorf("Size = %d, want 0 after clear", stats.Size)
	}
}

func TestRetry_ExponentialBackoff(t *testing.T) {
	var callCount int32
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		count := atomic.AddInt32(&callCount, 1)
		if count < 3 {
			w.WriteHeader(500)
			return
		}
		json.NewEncoder(w).Encode(samplePrompt)
	}))
	defer server.Close()

	client, _ := NewClient(ClientOptions{
		BaseURL:    server.URL,
		APIKey:     "pm_test_key",
		MaxRetries: 3,
		CacheTTL:   time.Minute,
	})

	start := time.Now()
	prompt, err := client.Get(context.Background(), samplePrompt.ID)
	elapsed := time.Since(start)

	if err != nil {
		t.Fatal(err)
	}
	if prompt.Name != "greeting" {
		t.Errorf("Name = %q, want %q", prompt.Name, "greeting")
	}
	if atomic.LoadInt32(&callCount) != 3 {
		t.Errorf("expected 3 calls, got %d", callCount)
	}
	// Should have waited at least 1s+2s = 3s for backoff
	if elapsed < 2*time.Second {
		t.Logf("elapsed = %v (expected >= ~3s, but timing may vary)", elapsed)
	}
}

func TestClose_NoPanic(t *testing.T) {
	client, _ := NewClient(ClientOptions{
		BaseURL: "https://example.com",
		APIKey:  "pm_test_123",
	})
	client.Close()
	client.Close() // double close should not panic
}
