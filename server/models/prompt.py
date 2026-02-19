from __future__ import annotations

from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    default: str
    fallback: list[str] = []
    temperature: float = 0.7
    max_tokens: int = 4000
    top_p: float = 0.9
    response_format: str = "text"
    json_schema: dict | None = None


class ModalityConfig(BaseModel):
    input: str = "text"
    output: str = "text"


class TTSConfig(BaseModel):
    provider: str = "elevenlabs"
    voice_id: str = ""
    model_id: str = "eleven_multilingual_v2"
    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0
    use_speaker_boost: bool = True


class AudioConfig(BaseModel):
    target_duration_minutes: float = 10
    binaural_frequency_hz: float = 5.0
    bpm: int = 50
    key_signature: str = "C Minor"
    background_track: str = ""
    pause_marker_format: str = "[PAUSE:3s]"


class EvalAssertion(BaseModel):
    type: str
    value: str
    threshold: float | None = None


class EvalConfig(BaseModel):
    dataset: str | None = None
    provider: str = "promptfoo"
    assertions: list[EvalAssertion] = []


class PromptResponse(BaseModel):
    """Response for public API prompt fetching."""
    id: str
    name: str
    version: str
    org: str
    app: str
    domain: str | None = None
    description: str | None = None
    type: str = "chat"
    role: str = "system"
    model: ModelConfig | dict = {}
    modality: ModalityConfig | dict | None = None
    tts: TTSConfig | dict | None = None
    audio: AudioConfig | dict | None = None
    environment: str = "development"
    active: bool = True
    tags: list[str] = []
    body: str = ""
    includes: list[str] = []
    git_sha: str | None = None
    updated_at: str | None = None


class PromptCreate(BaseModel):
    """Request body for creating a new prompt."""
    app_id: str
    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    domain: str | None = None
    description: str | None = None
    model: ModelConfig | dict = {}
    type: str = "chat"
    role: str = "system"
    modality: ModalityConfig | dict | None = None
    tts: TTSConfig | dict | None = None
    audio: AudioConfig | dict | None = None
    environment: str = "development"
    tags: list[str] = []
    body: str = ""
    includes: list[str] = []
    commit_message: str = "Add new prompt"


class PromptUpdate(BaseModel):
    """Request body for updating a prompt."""
    front_matter: dict | None = None
    body: str | None = None
    commit_message: str = "Update prompt"


class RenderRequest(BaseModel):
    """Request body for rendering a prompt with variables."""
    variables: dict = {}


class RenderResponse(BaseModel):
    id: str
    name: str
    rendered_body: str
    meta: dict = {}
    model: dict = {}


class PromptListItem(BaseModel):
    """Summary item for prompt listing."""
    id: str
    name: str
    domain: str | None = None
    description: str | None = None
    type: str = "chat"
    environment: str = "development"
    tags: list[str] = []
    active: bool = True
    version: str | None = None
    default_model: str | None = None
    modality_input: str | None = None
    modality_output: str | None = None
    updated_at: str | None = None
