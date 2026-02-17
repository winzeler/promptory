"""Parse and serialize Markdown files with YAML front-matter."""

from __future__ import annotations

import hashlib
import json
import uuid

import frontmatter
import yaml


def parse_prompt_file(content: str) -> tuple[dict, str]:
    """Parse a .md file into (front_matter_dict, body_string)."""
    post = frontmatter.loads(content)
    return dict(post.metadata), post.content


def serialize_prompt_file(front_matter: dict, body: str) -> str:
    """Serialize front-matter dict + body string into a .md file."""
    post = frontmatter.Post(body, **front_matter)
    return frontmatter.dumps(post)


def body_hash(body: str) -> str:
    """SHA-256 hash of prompt body for change detection."""
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


def ensure_id(front_matter: dict) -> dict:
    """Ensure front-matter has an id field; generate one if missing."""
    if "id" not in front_matter or not front_matter["id"]:
        front_matter["id"] = str(uuid.uuid4())
    return front_matter


def ensure_version(front_matter: dict, bump: str = "patch") -> dict:
    """Ensure front-matter has a version; bump if present."""
    version = front_matter.get("version", "0.0.0")
    if not version:
        version = "0.0.0"

    parts = version.split(".")
    if len(parts) != 3:
        parts = ["0", "0", "0"]

    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

    if bump == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump == "minor":
        minor += 1
        patch = 0
    else:
        patch += 1

    front_matter["version"] = f"{major}.{minor}.{patch}"
    return front_matter


def front_matter_to_json(front_matter: dict) -> str:
    """Serialize front-matter dict to JSON string for SQLite storage."""
    return json.dumps(front_matter, default=str)


def extract_tags(front_matter: dict) -> str:
    """Extract tags as JSON array string."""
    tags = front_matter.get("tags", [])
    if isinstance(tags, list):
        return json.dumps(tags)
    return "[]"
