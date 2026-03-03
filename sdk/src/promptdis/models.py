"""Promptdis data models."""

from __future__ import annotations

from dataclasses import dataclass, field

from jinja2.sandbox import SandboxedEnvironment

_jinja_env = SandboxedEnvironment(autoescape=False, keep_trailing_newline=True)


@dataclass
class Prompt:
    """A prompt fetched from the Promptdis server."""

    id: str
    name: str
    version: str
    org: str
    app: str
    domain: str | None = None
    description: str | None = None
    type: str = "chat"
    role: str | None = "system"
    model: dict = field(default_factory=dict)
    modality: dict | None = None
    tts: dict | None = None
    audio: dict | None = None
    environment: str = "development"
    active: bool = True
    tags: list[str] = field(default_factory=list)
    body: str = ""
    includes: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)
    git_sha: str | None = None
    updated_at: str | None = None

    def render(self, variables: dict | None = None) -> str:
        """Render the Jinja2 template body with the given variables."""
        if variables is None:
            variables = {}
        template = _jinja_env.from_string(self.body)
        return template.render(**variables)

    @classmethod
    def from_api_response(cls, data: dict) -> Prompt:
        """Create a Prompt from an API response dict."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            version=data.get("version", ""),
            org=data.get("org", ""),
            app=data.get("app", ""),
            domain=data.get("domain"),
            description=data.get("description"),
            type=data.get("type", "chat"),
            role=data.get("role", "system"),
            model=data.get("model", {}),
            modality=data.get("modality"),
            tts=data.get("tts"),
            audio=data.get("audio"),
            environment=data.get("environment", "development"),
            active=data.get("active", True),
            tags=data.get("tags", []),
            body=data.get("body", ""),
            includes=data.get("includes", []),
            meta=data,
            git_sha=data.get("git_sha"),
            updated_at=data.get("updated_at"),
        )
