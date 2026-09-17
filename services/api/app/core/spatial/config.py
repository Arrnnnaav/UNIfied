"""Adapter: expose StudyOS settings with the attribute names the synced Spatial modules expect
(`settings.providers`, `settings.provider_order`, `settings.ocr_enabled`, ...)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.config import get_settings


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    base_url: str
    api_key: str | None
    model: str
    vision_model: str | None
    kind: str  # "openai" (chat/completions), "ollama" (native /api/chat), "anthropic" (messages)

    @property
    def configured(self) -> bool:
        if self.kind == "bedrock":  # base_url holds the region; credentials come from the AWS chain (role/env/profile)
            return bool(self.base_url) and self.api_key == "1"
        return bool(self.base_url) and (self.kind == "ollama" or bool(self.api_key))


def _none_if_off(value: str | None) -> str | None:
    return (
        None if value is None or value.strip().lower() in {"", "none", "off"} else value
    )


def _build_providers() -> dict[str, ProviderConfig]:
    s = get_settings()
    return {
        "ollama": ProviderConfig(
            "ollama",
            s.local_llm_base_url or "",
            None,
            s.local_llm_model,
            _none_if_off(s.local_vision_model),
            "ollama",
        ),
        "openrouter": ProviderConfig(
            "openrouter",
            "https://openrouter.ai/api/v1",
            s.openrouter_api_key,
            s.openrouter_model,
            _none_if_off(s.openrouter_vision_model),
            "openai",
        ),
        "nvidia": ProviderConfig(
            "nvidia",
            "https://integrate.api.nvidia.com/v1",
            s.nvidia_api_key,
            s.nvidia_model,
            _none_if_off(s.nvidia_vision_model),
            "openai",
        ),
        "openai": ProviderConfig(
            "openai",
            "https://api.openai.com/v1",
            s.openai_api_key,
            s.tutor_model or "gpt-4o-mini",
            _none_if_off(s.openai_vision_model),
            "openai",
        ),
        "bedrock": ProviderConfig("bedrock", s.aws_region or "", "1" if s.bedrock_enabled else None, s.bedrock_model, _none_if_off(s.bedrock_vision_model), "bedrock"),
        "anthropic": ProviderConfig(
            "anthropic",
            "https://api.anthropic.com/v1",
            s.anthropic_api_key,
            s.tutor_model or "claude-sonnet-5",
            _none_if_off(s.anthropic_vision_model),
            "anthropic",
        ),
    }


@dataclass
class SpatialSettings:
    providers: dict[str, ProviderConfig] = field(default_factory=_build_providers)
    provider_order: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            p.strip() for p in get_settings().spatial_providers.split(",") if p.strip()
        )
    )
    ocr_enabled: bool = field(default_factory=lambda: get_settings().spatial_ocr)
    timeout_seconds: float = field(
        default_factory=lambda: get_settings().spatial_timeout_seconds
    )
    stt_model: str = field(default_factory=lambda: get_settings().spatial_stt_model)
    stt_device: str = field(default_factory=lambda: get_settings().spatial_stt_device)
    tts_enabled: bool = field(default_factory=lambda: get_settings().spatial_tts)
    tts_voice: str = field(default_factory=lambda: get_settings().spatial_tts_voice)
    audio_idle_unload_seconds: int = field(
        default_factory=lambda: get_settings().spatial_audio_idle_unload_seconds
    )
    force_ipv4: bool = field(default_factory=lambda: get_settings().spatial_force_ipv4)


settings = SpatialSettings()
