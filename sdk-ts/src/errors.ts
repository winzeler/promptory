/** Base error for all Promptory SDK errors. */
export class PromptoryError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "PromptoryError";
  }
}

/** Thrown when a prompt is not found (404). */
export class NotFoundError extends PromptoryError {
  constructor(message = "Prompt not found") {
    super(message);
    this.name = "NotFoundError";
  }
}

/** Thrown when authentication fails (401). */
export class AuthenticationError extends PromptoryError {
  constructor(message = "Authentication failed") {
    super(message);
    this.name = "AuthenticationError";
  }
}

/** Thrown when rate limit is exceeded (429). */
export class RateLimitError extends PromptoryError {
  public retryAfter: number | null;

  constructor(retryAfter: number | null = null) {
    super("Rate limit exceeded");
    this.name = "RateLimitError";
    this.retryAfter = retryAfter;
  }
}
