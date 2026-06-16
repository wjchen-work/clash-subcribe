"""User configuration loader and validator.

The user-facing YAML schema is intentionally permissive — sources can be HTTP(S)
URLs or local paths, processors are an ordered list that accepts both bare
names (``- dedup``) and keyed options (``- filter: {keywords: [...]}``). We
normalize that into strict pydantic models so the rest of the pipeline can
trust the shape of the data.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .exceptions import ConfigError

# --------------------------------------------------------------------------------------
# Source: exactly one of (url, path) must be set.
# --------------------------------------------------------------------------------------


class SourceConfig(BaseModel):
    """A single subscription source."""

    model_config = ConfigDict(extra="forbid")

    name: str
    url: str | None = None
    path: str | None = None
    # When True, a failure on this source aborts the whole pipeline.
    required: bool = False

    @model_validator(mode="after")
    def _exactly_one_transport(self) -> SourceConfig:
        has_url = self.url is not None
        has_path = self.path is not None
        if has_url == has_path:
            raise ValueError("source must set exactly one of `url` or `path`")
        return self

    @property
    def transport(self) -> Literal["http", "file"]:
        return "http" if self.url is not None else "file"


# --------------------------------------------------------------------------------------
# Processors: ordered list accepting bare names or {name: options}.
# --------------------------------------------------------------------------------------


class ProcessorEntry(BaseModel):
    """A single entry in the processor chain.

    YAML accepts two equivalent shapes::

        - dedup
        - filter:
            keywords: [免费]

    Both are normalized into ``(name, options)`` so downstream code doesn't have
    to care which form the user picked.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    options: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data: Any) -> dict[str, Any]:
        if isinstance(data, str):
            return {"name": data, "options": {}}
        if isinstance(data, dict) and len(data) == 1:
            ((key, value),) = data.items()
            if not isinstance(key, str):
                raise ValueError("processor key must be a string")
            options: dict[str, Any] = {}
            if value is not None:
                if not isinstance(value, dict):
                    raise ValueError(
                        f"processor {key!r} options must be a mapping, got {type(value).__name__}"
                    )
                options = value
            return {"name": key, "options": options}
        raise ValueError(f"processor entry must be a string or a single-key mapping, got {data!r}")


# --------------------------------------------------------------------------------------
# Output: file | stdout | http.
# --------------------------------------------------------------------------------------


class FileOutputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["file"]
    path: str
    template: str | None = None


class StdoutOutputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["stdout"]
    template: str | None = None


class HttpOutputConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["http"]
    port: int = 8080
    host: str = "127.0.0.1"
    template: str | None = None


OutputConfig = Annotated[
    FileOutputConfig | StdoutOutputConfig | HttpOutputConfig,
    Field(discriminator="type"),
]


# --------------------------------------------------------------------------------------
# Top-level user config.
# --------------------------------------------------------------------------------------


class UserConfig(BaseModel):
    """Root user configuration loaded from YAML."""

    model_config = ConfigDict(extra="forbid")

    sources: list[SourceConfig]
    processors: list[ProcessorEntry] = Field(default_factory=list)
    output: OutputConfig


# --------------------------------------------------------------------------------------
# Loader.
# --------------------------------------------------------------------------------------


def load_config(path: str | Path) -> UserConfig:
    """Load and validate a user config from a YAML file.

    Raises:
        ConfigError: if the file cannot be read or its contents don't validate.
    """
    config_path = Path(path)
    if not config_path.is_file():
        raise ConfigError(f"config file not found: {config_path}")

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML in {config_path}: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"cannot read {config_path}: {exc}") from exc

    if raw is None:
        raise ConfigError(f"config file is empty: {config_path}")
    if not isinstance(raw, dict):
        raise ConfigError(f"config root must be a mapping, got {type(raw).__name__}")

    try:
        return UserConfig.model_validate(raw)
    except Exception as exc:  # pydantic.ValidationError is a subclass
        raise ConfigError(f"invalid config {config_path}: {exc}") from exc
