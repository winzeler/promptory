/** Prompt data returned from the Promptory API. */
export interface Prompt {
  id: string;
  name: string;
  version: string;
  org: string;
  app: string;
  domain: string | null;
  description: string | null;
  type: string;
  role: string;
  model: Record<string, unknown>;
  environment: string;
  active: boolean;
  tags: string[];
  body: string;
  includes: string[];
  git_sha: string | null;
  updated_at: string | null;
}

/**
 * Render basic `{{variable}}` placeholders in a prompt body.
 *
 * This handles simple Mustache-style substitution only.
 * For full Jinja2 rendering (conditionals, loops, includes),
 * use `client.render()` which delegates to the server.
 */
export function renderLocal(body: string, variables: Record<string, string>): string {
  return body.replace(/\{\{\s*(\w+)\s*\}\}/g, (_, key) => {
    return variables[key] ?? "";
  });
}
