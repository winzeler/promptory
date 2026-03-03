"""Convert between Promptdis .md format and Microsoft .prompty format.

Prompty spec: https://prompty.ai/docs/prompty-file-spec
Mapping follows PROMPTDIS_API_DOCS.md section 9.1.
"""

from __future__ import annotations

import yaml


def md_to_prompty(front_matter: dict, body: str) -> str:
    """Convert a Promptdis .md prompt (front-matter + body) to .prompty format."""
    prompty: dict = {}

    # Direct mappings
    if front_matter.get("name"):
        prompty["name"] = front_matter["name"]
    if front_matter.get("description"):
        prompty["description"] = front_matter["description"]
    if front_matter.get("version"):
        prompty["version"] = front_matter["version"]

    # Authors from org
    if front_matter.get("org"):
        prompty["authors"] = [front_matter["org"]]

    # Tags
    if front_matter.get("tags"):
        prompty["tags"] = front_matter["tags"]

    # Model mapping: model.default -> model.api + model.configuration.name
    model = front_matter.get("model", {})
    if isinstance(model, dict) and model:
        prompty_model: dict = {}
        if model.get("default"):
            prompty_model["api"] = "chat"
            prompty_model["configuration"] = {"name": model["default"]}
        params = {}
        if model.get("temperature") is not None:
            params["temperature"] = model["temperature"]
        if model.get("max_tokens") is not None:
            params["max_tokens"] = model["max_tokens"]
        if model.get("top_p") is not None:
            params["top_p"] = model["top_p"]
        if params:
            prompty_model["parameters"] = params
        if prompty_model:
            prompty["model"] = prompty_model

    # Sample from variables if available
    if front_matter.get("variables"):
        prompty["sample"] = front_matter["variables"]

    # Build .prompty content
    header = yaml.dump(prompty, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return f"---\n{header}---\n{body}"


def prompty_to_md(prompty_content: str) -> tuple[dict, str]:
    """Parse a .prompty file and return (front_matter_dict, body).

    Returns a front-matter dict compatible with Promptdis .md format.
    """
    # Split on YAML front-matter delimiters
    if not prompty_content.startswith("---"):
        return {}, prompty_content

    parts = prompty_content.split("---", 2)
    if len(parts) < 3:
        return {}, prompty_content

    raw_meta = parts[1].strip()
    body = parts[2].lstrip("\n")

    try:
        meta = yaml.safe_load(raw_meta) or {}
    except yaml.YAMLError:
        return {}, prompty_content

    front_matter: dict = {}

    # Direct mappings
    if meta.get("name"):
        front_matter["name"] = meta["name"]
    if meta.get("description"):
        front_matter["description"] = meta["description"]
    if meta.get("version"):
        front_matter["version"] = meta["version"]

    # Authors -> org (first author)
    authors = meta.get("authors", [])
    if authors and isinstance(authors, list):
        front_matter["org"] = authors[0]

    # Tags
    if meta.get("tags"):
        front_matter["tags"] = meta["tags"]

    # Model mapping: reverse of md_to_prompty
    prompty_model = meta.get("model", {})
    if isinstance(prompty_model, dict) and prompty_model:
        model: dict = {}
        config = prompty_model.get("configuration", {})
        if isinstance(config, dict) and config.get("name"):
            model["default"] = config["name"]
        params = prompty_model.get("parameters", {})
        if isinstance(params, dict):
            if params.get("temperature") is not None:
                model["temperature"] = params["temperature"]
            if params.get("max_tokens") is not None:
                model["max_tokens"] = params["max_tokens"]
            if params.get("top_p") is not None:
                model["top_p"] = params["top_p"]
        if model:
            front_matter["model"] = model

    # Sample -> variables (best-effort)
    if meta.get("sample") and isinstance(meta["sample"], dict):
        front_matter["variables"] = meta["sample"]

    return front_matter, body
