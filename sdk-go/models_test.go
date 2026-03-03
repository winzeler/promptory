package promptdis

import "testing"

func TestPrompt_ModelDefault(t *testing.T) {
	p := &Prompt{Model: map[string]interface{}{"default": "gemini-2.0-flash"}}
	if got := p.ModelDefault("fallback"); got != "gemini-2.0-flash" {
		t.Errorf("ModelDefault() = %q, want %q", got, "gemini-2.0-flash")
	}
}

func TestPrompt_ModelDefault_Fallback(t *testing.T) {
	p := &Prompt{Model: map[string]interface{}{}}
	if got := p.ModelDefault("gpt-4o"); got != "gpt-4o" {
		t.Errorf("ModelDefault() = %q, want %q", got, "gpt-4o")
	}
}

func TestPrompt_ModelDefault_NilModel(t *testing.T) {
	p := &Prompt{}
	if got := p.ModelDefault("gpt-4o"); got != "gpt-4o" {
		t.Errorf("ModelDefault() = %q, want %q", got, "gpt-4o")
	}
}

func TestPrompt_ModelTemperature(t *testing.T) {
	p := &Prompt{Model: map[string]interface{}{"temperature": 0.7}}
	if got := p.ModelTemperature(0.5); got != 0.7 {
		t.Errorf("ModelTemperature() = %v, want %v", got, 0.7)
	}
}

func TestPrompt_ModelTemperature_Fallback(t *testing.T) {
	p := &Prompt{Model: map[string]interface{}{}}
	if got := p.ModelTemperature(0.5); got != 0.5 {
		t.Errorf("ModelTemperature() = %v, want %v", got, 0.5)
	}
}

func TestPrompt_ModelMaxTokens(t *testing.T) {
	p := &Prompt{Model: map[string]interface{}{"max_tokens": float64(4000)}}
	if got := p.ModelMaxTokens(2000); got != 4000 {
		t.Errorf("ModelMaxTokens() = %v, want %v", got, 4000)
	}
}

func TestPrompt_ModelMaxTokens_Fallback(t *testing.T) {
	p := &Prompt{Model: map[string]interface{}{}}
	if got := p.ModelMaxTokens(2000); got != 2000 {
		t.Errorf("ModelMaxTokens() = %v, want %v", got, 2000)
	}
}

func TestRenderLocal_Simple(t *testing.T) {
	result := RenderLocal("Hello {{name}}!", map[string]string{"name": "Alice"})
	if result != "Hello Alice!" {
		t.Errorf("RenderLocal() = %q, want %q", result, "Hello Alice!")
	}
}

func TestRenderLocal_Spaces(t *testing.T) {
	result := RenderLocal("Hello {{ name }}!", map[string]string{"name": "Bob"})
	if result != "Hello Bob!" {
		t.Errorf("RenderLocal() = %q, want %q", result, "Hello Bob!")
	}
}

func TestRenderLocal_Missing(t *testing.T) {
	result := RenderLocal("Hello {{name}}!", map[string]string{})
	if result != "Hello !" {
		t.Errorf("RenderLocal() = %q, want %q", result, "Hello !")
	}
}

func TestRenderLocal_Multiple(t *testing.T) {
	result := RenderLocal("{{greeting}} {{name}}, welcome to {{place}}.", map[string]string{
		"greeting": "Hello",
		"name":     "Alice",
		"place":    "Wonderland",
	})
	expected := "Hello Alice, welcome to Wonderland."
	if result != expected {
		t.Errorf("RenderLocal() = %q, want %q", result, expected)
	}
}
