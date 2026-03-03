package promptdis

import "regexp"

// Prompt represents a prompt returned from the Promptdis API.
type Prompt struct {
	ID          string                 `json:"id"`
	Name        string                 `json:"name"`
	Version     string                 `json:"version"`
	Org         string                 `json:"org"`
	App         string                 `json:"app"`
	Domain      *string                `json:"domain"`
	Description *string                `json:"description"`
	Type        string                 `json:"type"`
	Role        *string                `json:"role"`
	Model       map[string]interface{} `json:"model"`
	Modality    map[string]interface{} `json:"modality,omitempty"`
	TTS         map[string]interface{} `json:"tts,omitempty"`
	Audio       map[string]interface{} `json:"audio,omitempty"`
	Environment string                 `json:"environment"`
	Active      bool                   `json:"active"`
	Tags        []string               `json:"tags"`
	Body        string                 `json:"body"`
	Includes    []string               `json:"includes"`
	GitSHA      *string                `json:"git_sha"`
	UpdatedAt   *string                `json:"updated_at"`
}

// ModelDefault returns the default model name from the model config.
// Returns fallback if not set or not a string.
func (p *Prompt) ModelDefault(fallback string) string {
	if p.Model == nil {
		return fallback
	}
	v, ok := p.Model["default"]
	if !ok {
		return fallback
	}
	s, ok := v.(string)
	if !ok {
		return fallback
	}
	return s
}

// ModelTemperature returns the temperature from the model config.
// Returns fallback if not set or not a number.
func (p *Prompt) ModelTemperature(fallback float64) float64 {
	if p.Model == nil {
		return fallback
	}
	v, ok := p.Model["temperature"]
	if !ok {
		return fallback
	}
	switch n := v.(type) {
	case float64:
		return n
	case int:
		return float64(n)
	default:
		return fallback
	}
}

// ModelMaxTokens returns the max_tokens from the model config.
// Returns fallback if not set or not a number.
func (p *Prompt) ModelMaxTokens(fallback int) int {
	if p.Model == nil {
		return fallback
	}
	v, ok := p.Model["max_tokens"]
	if !ok {
		return fallback
	}
	switch n := v.(type) {
	case float64:
		return int(n)
	case int:
		return n
	default:
		return fallback
	}
}

// RenderResult is the response from server-side prompt rendering.
type RenderResult struct {
	RenderedBody string                 `json:"rendered_body"`
	Meta         map[string]interface{} `json:"meta"`
}

// varPattern matches {{variable}} placeholders with optional whitespace.
var varPattern = regexp.MustCompile(`\{\{\s*(\w+)\s*\}\}`)

// RenderLocal performs basic {{variable}} substitution on a prompt body.
// Variables not found in the map are replaced with an empty string.
// For full Jinja2 rendering (conditionals, loops, includes), use Client.Render.
func RenderLocal(body string, variables map[string]string) string {
	return varPattern.ReplaceAllStringFunc(body, func(match string) string {
		groups := varPattern.FindStringSubmatch(match)
		if len(groups) < 2 {
			return match
		}
		if val, ok := variables[groups[1]]; ok {
			return val
		}
		return ""
	})
}
