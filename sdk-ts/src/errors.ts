/** Base error for all Promptdis SDK errors. */
export class PromptdisError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "PromptdisError";
  }
}

/** Thrown when a prompt is not found (404). */
export class NotFoundError extends PromptdisError {
  constructor(message = "Prompt not found") {
    super(message);
    this.name = "NotFoundError";
  }
}

/** Thrown when authentication fails (401). */
export class AuthenticationError extends PromptdisError {
  constructor(message = "Authentication failed") {
    super(message);
    this.name = "AuthenticationError";
  }
}

/** Thrown when the API key lacks access to the requested resource (403). */
export class ForbiddenError extends PromptdisError {
  constructor(message = "Forbidden") {
    super(message);
    this.name = "ForbiddenError";
  }
}

/** Thrown when rate limit is exceeded (429). */
export class RateLimitError extends PromptdisError {
  public retryAfter: number | null;

  constructor(retryAfter: number | null = null) {
    super("Rate limit exceeded");
    this.name = "RateLimitError";
    this.retryAfter = retryAfter;
  }
}
