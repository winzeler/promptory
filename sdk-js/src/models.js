/**
 * @typedef {Object} Prompt
 * @property {string} id
 * @property {string} name
 * @property {string} version
 * @property {string} org
 * @property {string} app
 * @property {string|null} domain
 * @property {string|null} description
 * @property {string} type
 * @property {string} role
 * @property {Object} model
 * @property {string} environment
 * @property {boolean} active
 * @property {string[]} tags
 * @property {string} body
 * @property {string[]} includes
 * @property {string|null} git_sha
 * @property {string|null} updated_at
 */

/**
 * Render basic `{{variable}}` placeholders in a prompt body.
 *
 * This handles simple Mustache-style substitution only.
 * For full Jinja2 rendering (conditionals, loops, includes),
 * use `client.render()` which delegates to the server.
 *
 * @param {string} body
 * @param {Record<string, string>} variables
 * @returns {string}
 */
export function renderLocal(body, variables) {
  return body.replace(/\{\{\s*(\w+)\s*\}\}/g, (_, key) => {
    return variables[key] ?? "";
  });
}
