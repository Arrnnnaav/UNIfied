from __future__ import annotations

import ipaddress
import re
import socket
from html import unescape
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


def validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("only public http(s) URLs are supported")
    host = parsed.hostname.lower()
    if host in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("local URLs are not allowed")
    try:
        addresses = socket.getaddrinfo(host, None)
        if any(ipaddress.ip_address(address[4][0]).is_private for address in addresses):
            raise ValueError("private network URLs are not allowed")
    except socket.gaierror as exc:
        raise ValueError("hostname could not be resolved") from exc


class _SafeRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_web_text(url: str, max_bytes: int = 5_000_000) -> str:
    validate_public_url(url)
    request = Request(url, headers={"User-Agent": "StudyOS/0.1 resource-ingestion"})
    opener = build_opener(_SafeRedirectHandler)
    with opener.open(request, timeout=10) as response:
        payload = response.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise ValueError("resource exceeds maximum fetch size")
    html = payload.decode("utf-8", errors="replace")
    try:
        import trafilatura
        extracted = trafilatura.extract(html, include_comments=False, include_tables=True)
        if extracted: return extracted.strip()
    except ImportError:
        pass
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def fetch_github_text(url: str, max_bytes: int = 5_000_000) -> str:
    """Fetch a public repository README through GitHub's API without cloning arbitrary code."""
    validate_public_url(url)
    parsed = urlparse(url)
    if parsed.hostname not in {"github.com", "www.github.com"}:
        raise ValueError("GitHub ingestion requires a github.com URL")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        raise ValueError("GitHub URL must identify a repository")
    owner, repository = parts[0], parts[1].removesuffix(".git")
    api_url = f"https://api.github.com/repos/{owner}/{repository}/readme"
    request = Request(api_url, headers={"Accept": "application/vnd.github.raw+json", "User-Agent": "StudyOS/0.1 github-ingestion"})
    opener = build_opener(_SafeRedirectHandler)
    with opener.open(request, timeout=10) as response:
        payload = response.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise ValueError("repository README exceeds maximum fetch size")
    return payload.decode("utf-8", errors="replace").strip()


def youtube_video_id(url: str) -> str:
    parsed = urlparse(url)
    if parsed.hostname not in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}:
        raise ValueError("YouTube ingestion requires a youtube.com or youtu.be URL")
    if parsed.hostname == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0]
    else:
        if parsed.path == "/watch":
            from urllib.parse import parse_qs
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        else:
            parts = [part for part in parsed.path.split("/") if part]
            video_id = parts[1] if len(parts) >= 2 and parts[0] in {"embed", "shorts", "live"} else ""
    if not re.fullmatch(r"[A-Za-z0-9_-]{6,20}", video_id or ""):
        raise ValueError("YouTube URL does not contain a valid video id")
    return video_id


def fetch_youtube_transcript(url: str, max_chars: int = 1_000_000) -> str:
    """Fetch an available transcript; captions are optional and no video media is downloaded."""
    video_id = youtube_video_id(url)
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        entries = YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "en-US", "hi"])
    except Exception as exc:
        raise ValueError("transcript unavailable for this video") from exc
    lines = []
    total = 0
    for entry in entries:
        text = re.sub(r"\s+", " ", str(entry.get("text", ""))).strip()
        if not text:
            continue
        total += len(text) + 1
        if total > max_chars:
            raise ValueError("video transcript exceeds maximum size")
        lines.append(text)
    if not lines:
        raise ValueError("transcript unavailable for this video")
    return "\n".join(lines)
