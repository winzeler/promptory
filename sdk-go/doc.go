// Package promptory provides a Go client for the Promptory prompt management API.
//
// Promptory is a centralized prompt management platform that stores, versions,
// and serves LLM prompts. This SDK provides type-safe access with built-in
// caching, retry logic, and error handling.
//
// # Quick Start
//
//	client, err := promptory.NewClient(promptory.ClientOptions{
//	    BaseURL: "https://prompts.futureself.app",
//	    APIKey:  "pm_live_...",
//	})
//	if err != nil {
//	    log.Fatal(err)
//	}
//	defer client.Close()
//
//	prompt, err := client.GetByName(ctx, "futureself", "meditate", "meditation_script_relax")
//	if err != nil {
//	    log.Fatal(err)
//	}
//
//	rendered := client.RenderLocal(prompt.Body, map[string]string{
//	    "name": "Alice",
//	})
//
// # Features
//
//   - Fetch prompts by UUID or fully qualified name (org/app/name)
//   - LRU cache with TTL and ETag-based conditional fetches
//   - Typed errors with errors.Is / errors.As support
//   - Retry with exponential backoff on 429/5xx
//   - Basic {{var}} local rendering
//   - Zero external dependencies (stdlib only)
//   - Goroutine-safe (sync.RWMutex protected cache)
package promptory
