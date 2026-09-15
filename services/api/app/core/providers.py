"""Model routing seam: fast local models for interaction, stronger APIs for synthesis."""
from __future__ import annotations

from dataclasses import dataclass
import base64
import hashlib
import json
import math
import re
from functools import lru_cache
from time import perf_counter
from urllib.parse import urlparse

from app.core.config import get_settings


@dataclass(frozen=True)
class ModelDecision:
    provider: str
    model: str
    reason: str
    local_first: bool


def choose_model(task: str, latency_sensitive: bool = False) -> ModelDecision:
    settings = get_settings()
    if latency_sensitive or task in {"spatial_resolve", "classify", "rerank"}:
        return ModelDecision("local", settings.local_embedding_model or settings.embedding_model, "fast, private interaction path", True)
    if settings.local_llm_base_url:
        return ModelDecision("local", settings.local_llm_model, "configured local synthesis runtime", True)
    if settings.openai_api_key:
        return ModelDecision("openai", settings.tutor_model or "configured-tutor", "strong synthesis with citations", False)
    if settings.anthropic_api_key:
        return ModelDecision("anthropic", settings.tutor_model or "configured-tutor", "strong synthesis with citations", False)
    return ModelDecision("local", settings.local_llm_model, "no cloud provider configured", True)


@lru_cache(maxsize=2048)
def embed_text(text: str, dimensions: int = 384) -> list[float]:
    """Use Ollama or a local sentence-transformer before falling back to offline hashing."""
    settings = get_settings()
    if settings.local_llm_base_url:
        try:
            import httpx
            with httpx.Client(trust_env=False, timeout=min(settings.llm_timeout_seconds, 5)) as client:
                response = client.post(f"{settings.local_llm_base_url.rstrip('/')}/embeddings",
                                       json={"model": settings.local_embedding_model or "embeddinggemma:latest", "input": text})
            response.raise_for_status()
            values = response.json()["data"][0]["embedding"]
            if len(values) > dimensions:
                values = values[:dimensions]
            else:
                values = list(values) + [0.0] * (dimensions - len(values))
            norm = math.sqrt(sum(float(value) * float(value) for value in values)) or 1.0
            return [round(float(value) / norm, 6) for value in values]
        except Exception:
            pass
    if settings.use_local_embeddings:
        try:
            model = _local_embedder(settings.local_embedding_model or settings.embedding_model)
            values = model.encode(text, normalize_embeddings=True).tolist()
            if len(values) == dimensions:
                return [round(float(value), 6) for value in values]
            if len(values) > dimensions:
                values = values[:dimensions]
            else:
                values.extend([0.0] * (dimensions - len(values)))
            return [round(float(value), 6) for value in values]
        except Exception:
            pass
    vector = [0.0] * dimensions
    for token in re.findall(r"[a-z0-9_]+", text.lower()):
        digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
        vector[int.from_bytes(digest[:4], "big") % dimensions] += 1.0 if digest[4] & 1 else -1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [round(value / norm, 6) for value in vector]


@lru_cache(maxsize=2)
def _local_embedder(model_name: str):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(model_name)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def warm_local_models() -> dict[str, str]:
    """Bounded, observable warm-up; never downloads or persists model data in StudyOS."""
    settings = get_settings()
    if not settings.local_llm_base_url:
        return {"status": "not-configured"}
    try:
        import httpx
        parsed = urlparse(settings.local_llm_base_url)
        native_base = settings.local_llm_base_url.rstrip("/")[:-3] if parsed.path.rstrip("/").endswith("/v1") else settings.local_llm_base_url.rstrip("/")
        # Cold model loading is a deployment concern, not an interactive
        # request. Give it a bounded but independent budget so a 12s tutor
        # timeout does not falsely mark an otherwise healthy local runtime as
        # unavailable.
        with httpx.Client(trust_env=False, timeout=max(45, min(settings.llm_timeout_seconds, 120))) as client:
            response = client.post(f"{native_base}/api/chat", json={"model": settings.local_llm_model, "stream": False, "think": False,
                "options": {"temperature": 0.0, "num_predict": 1}, "messages": [{"role": "user", "content": "Reply with OK."}]})
        response.raise_for_status()
        return {"status": "ready", "provider": "local", "model": settings.local_llm_model}
    except Exception as exc:
        return {"status": "unavailable", "provider": "local", "model": settings.local_llm_model, "error": str(exc)[:160]}


def _resolve_local_vision(image_data: str | None, utterance: str, marks: list[dict]) -> dict | None:
    settings = get_settings()
    if not image_data or not settings.local_vision_model or not settings.local_llm_base_url:
        return None
    try:
        encoded = image_data.split(",", 1)[-1]
        raw = base64.b64decode(encoded, validate=True)
        if len(raw) > 4_000_000:
            return {"status": "rejected", "reason": "image exceeds 4 MB"}
        import httpx
        parsed = urlparse(settings.local_llm_base_url)
        native_base = settings.local_llm_base_url.rstrip("/")[:-3] if parsed.path.rstrip("/").endswith("/v1") else settings.local_llm_base_url.rstrip("/")
        prompt = (
            "Return JSON only with keys labels (array of short visual labels), "
            "selected_region_summary (string), and confidence (number from 0 to 1). "
            "Do not infer text that is not visible. "
            f"Student question: {utterance[:2000]}. "
            f"Marks: {json.dumps(marks, separators=(',', ':'))}"
        )
        with httpx.Client(trust_env=False, timeout=min(settings.llm_timeout_seconds, 8)) as client:
            response = client.post(f"{native_base}/api/chat", json={"model": settings.local_vision_model, "stream": False, "think": False,
                "format": "json", "options": {"temperature": 0.0, "num_predict": 180},
                "messages": [{"role": "user", "content": prompt, "images": [encoded]}]})
        response.raise_for_status()
        content = response.json().get("message", {}).get("content", "{}")
        parsed_content = json.loads(content)
        confidence = max(0.0, min(1.0, float(parsed_content.get("confidence", 0.0))))
        return {"status": "generated", "provider": "local", "model": settings.local_vision_model,
                "labels": [str(label)[:120] for label in parsed_content.get("labels", [])[:12]],
                "selected_region_summary": str(parsed_content.get("selected_region_summary", ""))[:500], "confidence": confidence}
    except Exception as exc:
        return {"status": "fallback", "provider": "local", "model": settings.local_vision_model, "error": str(exc)[:160]}


def resolve_spatial_marks(marks: list[dict], canvas: dict | None = None, anchors: list[dict] | None = None, image_data: str | None = None, utterance: str = "") -> dict:
    """Cheap deterministic resolver used before any VLM call; returns explainable confidence."""
    started = perf_counter()
    candidates = []
    normalized = []
    valid_anchors = []
    for anchor in anchors or []:
        if not isinstance(anchor, dict) or not anchor.get("id"):
            continue
        bbox = anchor.get("bbox") or anchor.get("rect")
        if not isinstance(bbox, dict):
            continue
        try:
            valid_anchors.append({"id": str(anchor["id"]), "type": str(anchor.get("type", "unknown")),
                                  "x": float(bbox.get("x", 0)), "y": float(bbox.get("y", 0)),
                                  "width": max(0.0, float(bbox.get("width", 0))), "height": max(0.0, float(bbox.get("height", 0)))})
        except (TypeError, ValueError):
            continue
    canvas_width = max(float((canvas or {}).get("width", 1)), 1.0)
    canvas_height = max(float((canvas or {}).get("height", 1)), 1.0)
    for index, mark in enumerate(marks):
        kind = mark.get("type", "unknown")
        if kind not in {"point", "rectangle", "circle", "polygon", "arrow", "line"}:
            continue
        clean = dict(mark)
        try:
            for axis in ("x", "y", "width", "height"):
                if axis in clean:
                    clean[axis] = max(0.0, float(clean[axis]))
            if kind in {"point", "rectangle", "circle", "arrow", "line"}:
                if "x" in clean: clean["x_norm"] = round(min(clean["x"] / canvas_width, 1.0), 6)
                if "y" in clean: clean["y_norm"] = round(min(clean["y"] / canvas_height, 1.0), 6)
                if "width" in clean: clean["width_norm"] = round(min(clean["width"] / canvas_width, 1.0), 6)
                if "height" in clean: clean["height_norm"] = round(min(clean["height"] / canvas_height, 1.0), 6)
        except (TypeError, ValueError):
            continue
        normalized.append(clean)
        candidate = {"mark_index": index, "kind": kind, "role": mark.get("role", "reference")}
        if valid_anchors and "x" in clean and "y" in clean:
            mark_width = max(0.0, clean.get("width", 0))
            mark_height = max(0.0, clean.get("height", 0))
            mark_right = clean["x"] + mark_width
            mark_bottom = clean["y"] + mark_height
            scored = []
            for anchor in valid_anchors:
                right = anchor["x"] + anchor["width"]
                bottom = anchor["y"] + anchor["height"]
                intersection = max(0.0, min(mark_right, right) - max(clean["x"], anchor["x"])) * max(0.0, min(mark_bottom, bottom) - max(clean["y"], anchor["y"]))
                mark_area = mark_width * mark_height
                anchor_area = anchor["width"] * anchor["height"]
                union = mark_area + anchor_area - intersection
                iou = intersection / union if union else 0.0
                mark_overlap = intersection / mark_area if mark_area else 0.0
                anchor_overlap = intersection / anchor_area if anchor_area else 0.0
                center_x = clean["x"] + mark_width / 2
                center_y = clean["y"] + mark_height / 2
                contains_center = anchor["x"] <= center_x <= right and anchor["y"] <= center_y <= bottom
                contains_anchor = clean["x"] <= anchor["x"] and clean["y"] <= anchor["y"] and mark_right >= right and mark_bottom >= bottom
                score = max(iou, min(0.94, mark_overlap * 0.9), min(0.95, anchor_overlap * 0.95), 0.95 if contains_center and not mark_area else 0.0, 0.96 if contains_anchor else 0.0)
                if score >= 0.10:
                    match_type = "contains_anchor" if contains_anchor else ("contains_center" if contains_center and not mark_area else "overlap_ranked")
                    scored.append((score, anchor, match_type))
            if scored:
                score, anchor, match = max(scored, key=lambda item: (item[0], -item[1]["width"] * item[1]["height"]))
                candidate.update({"anchor_id": anchor["id"], "anchor_type": anchor["type"], "anchor_match": match, "anchor_overlap": round(score, 3)})
        candidates.append(candidate)
    confidence = 0.78 if candidates else 0.0
    matched = sum("anchor_id" in candidate for candidate in candidates)
    if valid_anchors and candidates:
        confidence = min(0.99, confidence + 0.18 * matched / len(candidates))
        if not matched:
            confidence = min(confidence, 0.72)
    roles = {item["role"] for item in candidates}
    if "source" in roles and "target" in roles:
        confidence = min(0.97, confidence + 0.03)
    if canvas and any("width" in item and "height" in item and (item["width"] == 0 or item["height"] == 0) for item in normalized):
        confidence = min(confidence, 0.65)
    vision = _resolve_local_vision(image_data, utterance, marks)
    return {"candidates": candidates, "normalized_marks": normalized, "anchors_considered": len(valid_anchors),
            "canvas": {"width": canvas_width, "height": canvas_height}, "confidence": confidence,
            "vision": vision,
            "resolver": "structured-anchor-v1" if valid_anchors else "deterministic-v1", "latency_ms": round((perf_counter()-started)*1000),
            "next": "plugin/dom/uia resolver" if canvas else "crop-or-document resolver"}
