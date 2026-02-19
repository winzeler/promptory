package promptory

import "fmt"

// PromptoryError is the base error type for all Promptory SDK errors.
// It wraps an HTTP status code and a human-readable message.
type PromptoryError struct {
	StatusCode int
	Message    string
}

func (e *PromptoryError) Error() string {
	if e.StatusCode > 0 {
		return fmt.Sprintf("promptory: %d: %s", e.StatusCode, e.Message)
	}
	return fmt.Sprintf("promptory: %s", e.Message)
}

// Is supports errors.Is matching against sentinel error values.
// Two PromptoryErrors match if they have the same StatusCode.
func (e *PromptoryError) Is(target error) bool {
	t, ok := target.(*PromptoryError)
	if !ok {
		return false
	}
	return e.StatusCode == t.StatusCode
}

// Sentinel errors for use with errors.Is.
var (
	// ErrNotFound indicates the requested prompt was not found (HTTP 404).
	ErrNotFound = &PromptoryError{StatusCode: 404, Message: "prompt not found"}

	// ErrAuthentication indicates authentication failed (HTTP 401).
	ErrAuthentication = &PromptoryError{StatusCode: 401, Message: "authentication failed"}

	// ErrRateLimit indicates the rate limit was exceeded (HTTP 429).
	ErrRateLimit = &PromptoryError{StatusCode: 429, Message: "rate limit exceeded"}
)

// RateLimitError extends PromptoryError with a RetryAfter field
// parsed from the Retry-After header. Use errors.As to extract it.
type RateLimitError struct {
	PromptoryError
	RetryAfter int // seconds until the rate limit resets
}

func (e *RateLimitError) Error() string {
	if e.RetryAfter > 0 {
		return fmt.Sprintf("promptory: 429: rate limit exceeded (retry after %ds)", e.RetryAfter)
	}
	return "promptory: 429: rate limit exceeded"
}

// Is supports errors.Is matching. A RateLimitError matches ErrRateLimit.
func (e *RateLimitError) Is(target error) bool {
	t, ok := target.(*PromptoryError)
	if !ok {
		return false
	}
	return t.StatusCode == 429
}

// Unwrap returns the underlying PromptoryError for errors.As support.
func (e *RateLimitError) Unwrap() error {
	return &e.PromptoryError
}
