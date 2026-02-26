package promptdis

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"strings"
	"time"
)

// ClientOptions configures a new Promptdis Client.
type ClientOptions struct {
	// BaseURL is the Promptdis server URL (required).
	BaseURL string

	// APIKey is the API key for authentication (required).
	// Format: pm_live_... or pm_test_...
	APIKey string

	// CacheMaxSize is the maximum number of cached prompts (default: 100).
	CacheMaxSize int

	// CacheTTL is the cache time-to-live (default: 60s).
	CacheTTL time.Duration

	// MaxRetries is the number of retry attempts on 429/5xx (default: 3).
	MaxRetries int

	// Timeout is the HTTP request timeout (default: 10s).
	Timeout time.Duration

	// HTTPClient is an optional custom HTTP client. If nil, a default client
	// is created with the configured Timeout.
	HTTPClient *http.Client
}

// Client is the Promptdis SDK client. It is safe for concurrent use.
type Client struct {
	baseURL    string
	apiKey     string
	cache      *lruCache
	maxRetries int
	httpClient *http.Client
}

// NewClient creates a new Promptdis Client with the given options.
// BaseURL and APIKey are required; other fields have sensible defaults.
func NewClient(opts ClientOptions) (*Client, error) {
	if opts.BaseURL == "" {
		return nil, &PromptdisError{Message: "BaseURL is required"}
	}
	if opts.APIKey == "" {
		return nil, &PromptdisError{Message: "APIKey is required"}
	}

	if opts.CacheMaxSize <= 0 {
		opts.CacheMaxSize = 100
	}
	if opts.CacheTTL <= 0 {
		opts.CacheTTL = 60 * time.Second
	}
	if opts.MaxRetries <= 0 {
		opts.MaxRetries = 3
	}
	if opts.Timeout <= 0 {
		opts.Timeout = 10 * time.Second
	}

	httpClient := opts.HTTPClient
	if httpClient == nil {
		httpClient = &http.Client{Timeout: opts.Timeout}
	}

	return &Client{
		baseURL:    strings.TrimRight(opts.BaseURL, "/"),
		apiKey:     opts.APIKey,
		cache:      newLRUCache(opts.CacheMaxSize, opts.CacheTTL),
		maxRetries: opts.MaxRetries,
		httpClient: httpClient,
	}, nil
}

// Get fetches a prompt by UUID.
func (c *Client) Get(ctx context.Context, promptID string) (*Prompt, error) {
	cacheKey := "id:" + promptID
	path := "/api/v1/prompts/" + promptID
	return c.fetchWithCache(ctx, path, cacheKey)
}

// GetOption configures optional parameters for GetByName.
type GetOption func(*getOptions)

type getOptions struct {
	environment string
}

// WithEnvironment filters GetByName results to a specific environment.
func WithEnvironment(env string) GetOption {
	return func(o *getOptions) {
		o.environment = env
	}
}

// GetByName fetches a prompt by fully qualified name (org/app/name).
func (c *Client) GetByName(ctx context.Context, org, app, name string, opts ...GetOption) (*Prompt, error) {
	o := &getOptions{}
	for _, fn := range opts {
		fn(o)
	}

	envSuffix := "any"
	pathSuffix := ""
	if o.environment != "" {
		envSuffix = o.environment
		pathSuffix = "?environment=" + o.environment
	}

	cacheKey := fmt.Sprintf("name:%s/%s/%s:%s", org, app, name, envSuffix)
	path := fmt.Sprintf("/api/v1/prompts/by-name/%s/%s/%s%s", org, app, name, pathSuffix)
	return c.fetchWithCache(ctx, path, cacheKey)
}

// Render sends variables to the server for full Jinja2 rendering.
func (c *Client) Render(ctx context.Context, promptID string, variables map[string]interface{}) (*RenderResult, error) {
	path := "/api/v1/prompts/" + promptID + "/render"

	body := map[string]interface{}{"variables": variables}
	bodyBytes, err := json.Marshal(body)
	if err != nil {
		return nil, &PromptdisError{Message: "failed to marshal variables: " + err.Error()}
	}

	resp, err := c.doRequest(ctx, http.MethodPost, path, bodyBytes)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, c.handleError(resp)
	}

	var result RenderResult
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, &PromptdisError{Message: "failed to decode render response: " + err.Error()}
	}
	return &result, nil
}

// RenderLocal performs basic {{var}} substitution locally.
// For full Jinja2 rendering, use Render which delegates to the server.
func (c *Client) RenderLocal(body string, variables map[string]string) string {
	return RenderLocal(body, variables)
}

// CacheStats returns current cache statistics.
func (c *Client) CacheStats() CacheStats {
	return c.cache.stats()
}

// CacheInvalidate removes a specific cache entry. Returns true if found.
func (c *Client) CacheInvalidate(key string) bool {
	return c.cache.invalidate(key)
}

// CacheClear removes all cache entries.
func (c *Client) CacheClear() {
	c.cache.clear()
}

// Close releases resources held by the client (closes idle HTTP connections).
func (c *Client) Close() {
	c.httpClient.CloseIdleConnections()
}

// --- Internal methods ---

func (c *Client) fetchWithCache(ctx context.Context, path, cacheKey string) (*Prompt, error) {
	cached, fresh := c.cache.get(cacheKey)

	if cached != nil && fresh {
		return cached.value, nil
	}

	headers := map[string]string{}
	if cached != nil && cached.etag != "" {
		headers["If-None-Match"] = cached.etag
	}

	resp, err := c.doRequestWithHeaders(ctx, http.MethodGet, path, nil, headers)
	if err != nil {
		// On network error, return stale cache if available
		if cached != nil {
			return cached.value, nil
		}
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusNotModified && cached != nil {
		c.cache.refreshTTL(cacheKey)
		return cached.value, nil
	}

	if resp.StatusCode != http.StatusOK {
		apiErr := c.handleError(resp)
		// On server error, return stale cache if available
		if cached != nil {
			pe, ok := apiErr.(*PromptdisError)
			if ok && pe.StatusCode >= 500 {
				return cached.value, nil
			}
		}
		return nil, apiErr
	}

	var prompt Prompt
	if err := json.NewDecoder(resp.Body).Decode(&prompt); err != nil {
		return nil, &PromptdisError{Message: "failed to decode prompt: " + err.Error()}
	}

	etag := resp.Header.Get("ETag")
	c.cache.set(cacheKey, &prompt, etag)
	return &prompt, nil
}

func (c *Client) doRequest(ctx context.Context, method, path string, body []byte) (*http.Response, error) {
	return c.doRequestWithHeaders(ctx, method, path, body, nil)
}

func (c *Client) doRequestWithHeaders(ctx context.Context, method, path string, body []byte, extraHeaders map[string]string) (*http.Response, error) {
	url := c.baseURL + path

	var lastErr error
	for attempt := 0; attempt <= c.maxRetries; attempt++ {
		var bodyReader io.Reader
		if body != nil {
			bodyReader = bytes.NewReader(body)
		}

		req, err := http.NewRequestWithContext(ctx, method, url, bodyReader)
		if err != nil {
			return nil, &PromptdisError{Message: "failed to create request: " + err.Error()}
		}

		req.Header.Set("Authorization", "Bearer "+c.apiKey)
		req.Header.Set("Content-Type", "application/json")
		for k, v := range extraHeaders {
			req.Header.Set(k, v)
		}

		resp, err := c.httpClient.Do(req)
		if err != nil {
			lastErr = err
			if attempt < c.maxRetries {
				delay := backoffDelay(attempt, 0)
				if err := sleepCtx(ctx, delay); err != nil {
					return nil, &PromptdisError{Message: "request cancelled"}
				}
			}
			continue
		}

		// Retry on 429 or 5xx
		if attempt < c.maxRetries && (resp.StatusCode == 429 || resp.StatusCode >= 500) {
			retryAfter := 0
			if raHeader := resp.Header.Get("Retry-After"); raHeader != "" {
				if parsed, err := strconv.Atoi(raHeader); err == nil {
					retryAfter = parsed
				}
			}
			resp.Body.Close()
			delay := backoffDelay(attempt, retryAfter)
			if err := sleepCtx(ctx, delay); err != nil {
				return nil, &PromptdisError{Message: "request cancelled"}
			}
			continue
		}

		return resp, nil
	}

	return nil, &PromptdisError{
		Message: fmt.Sprintf("request failed after %d attempts: %v", c.maxRetries+1, lastErr),
	}
}

func (c *Client) handleError(resp *http.Response) error {
	var body struct {
		Error struct {
			Message string `json:"message"`
		} `json:"error"`
	}
	_ = json.NewDecoder(resp.Body).Decode(&body)

	message := body.Error.Message
	if message == "" {
		message = resp.Status
	}

	switch resp.StatusCode {
	case 401:
		return &PromptdisError{StatusCode: 401, Message: message}
	case 404:
		return &PromptdisError{StatusCode: 404, Message: message}
	case 429:
		retryAfter := 0
		if raHeader := resp.Header.Get("Retry-After"); raHeader != "" {
			if parsed, err := strconv.Atoi(raHeader); err == nil {
				retryAfter = parsed
			}
		}
		return &RateLimitError{
			PromptdisError: PromptdisError{StatusCode: 429, Message: "rate limit exceeded"},
			RetryAfter:     retryAfter,
		}
	default:
		return &PromptdisError{
			StatusCode: resp.StatusCode,
			Message:    message,
		}
	}
}

// backoffDelay calculates the delay for a retry attempt.
// If retryAfterSec > 0, it's used directly. Otherwise, exponential backoff
// is applied: 1s, 2s, 4s, ... capped at 10s.
func backoffDelay(attempt, retryAfterSec int) time.Duration {
	if retryAfterSec > 0 {
		return time.Duration(retryAfterSec) * time.Second
	}
	delay := time.Duration(1<<uint(attempt)) * time.Second
	if delay > 10*time.Second {
		delay = 10 * time.Second
	}
	return delay
}

// sleepCtx sleeps for the given duration, returning early if the context is cancelled.
func sleepCtx(ctx context.Context, d time.Duration) error {
	timer := time.NewTimer(d)
	defer timer.Stop()
	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-timer.C:
		return nil
	}
}
