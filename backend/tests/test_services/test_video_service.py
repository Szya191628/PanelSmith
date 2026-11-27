from __future__ import annotations

import pytest

from app.config import Settings
from app.services import video_merger
from app.services.video import VideoService


def test_build_url():
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        video_base_url="https://video.example.com/",
        video_endpoint="videos/generations",
    )
    service = VideoService(settings)
    assert service._build_url() == "https://video.example.com/videos/generations"


@pytest.mark.asyncio
async def test_generate_url_standard(monkeypatch):
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        video_base_url="https://video.example.com",
        video_endpoint="/videos/generations",
        video_api_key="test",
    )
    service = VideoService(settings)

    async def fake_post(url, payload):
        return {"data": [{"url": "https://cdn.example.com/video.mp4"}]}

    monkeypatch.setattr(service, "_post_json_with_retry", fake_post)

    url = await service.generate_url(prompt="scene")
    assert url == "https://cdn.example.com/video.mp4"


@pytest.mark.asyncio
async def test_generate_url_chat_completions(monkeypatch):
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        video_base_url="https://video.example.com",
        video_endpoint="/chat/completions",
        video_api_key="test",
    )
    service = VideoService(settings)

    async def fake_stream(url, payload):
        return "result https://cdn.example.com/stream.mp4 done"

    monkeypatch.setattr(service, "_post_stream_with_retry", fake_stream)

    url = await service.generate_url(prompt="scene")
    assert url == "https://cdn.example.com/stream.mp4"


@pytest.mark.asyncio
async def test_generate_url_i2v(monkeypatch):
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        video_base_url="https://video.example.com",
        video_endpoint="/videos/generations",
        video_api_key="test",
        enable_image_to_video=True,
    )
    service = VideoService(settings)

    async def fake_post(url, payload):
        return {"data": [{"url": "https://cdn.example.com/i2v.mp4"}]}

    monkeypatch.setattr(service, "_post_json_with_retry", fake_post)

    url = await service.generate_url(prompt="scene", image_bytes=b"fake")
    assert url == "https://cdn.example.com/i2v.mp4"


@pytest.mark.asyncio
async def test_merge_urls(monkeypatch):
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:")
    service = VideoService(settings)

    class StubMerger:
        async def merge_videos(self, urls):
            return "/static/videos/merged.mp4"

    monkeypatch.setattr(video_merger, "get_video_merger_service", lambda: StubMerger())

    url = await service.merge_urls(["https://cdn.example.com/1.mp4", "https://cdn.example.com/2.mp4"])
    assert url == "/static/videos/merged.mp4"


@pytest.mark.asyncio
@pytest.mark.parametrize("with_image", [False, True])
async def test_sparkcine_submit_poll_and_content_redirect(monkeypatch, with_image):
    import httpx

    settings = Settings(
        video_base_url="https://hi.hi.run/api/openai/v1",
        video_endpoint="/videos",
        video_model="h3-video",
        video_api_key="test",
        enable_image_to_video=True,
    )
    service = VideoService(settings)
    submitted = []

    async def post(url, payload):
        submitted.append((url, payload, None))
        return {"id": "task-123", "status": "queued"}

    async def multipart(url, *, fields, image_bytes):
        submitted.append((url, fields, image_bytes))
        return {"id": "task-123", "status": "queued"}

    async def poll(task_id):
        assert task_id == "task-123"
        return {"id": task_id, "status": "completed"}

    class ContentClient:
        def __init__(self, **kwargs):
            assert kwargs["follow_redirects"] is False

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url, *, headers):
            assert url.endswith("/videos/task-123/content")
            return httpx.Response(
                302, headers={"location": "https://cdn.example.com/final.mp4"},
                request=httpx.Request("GET", url),
            )

    monkeypatch.setattr(service, "_post_json_with_retry", post)
    monkeypatch.setattr(service, "_post_multipart_with_retry", multipart)
    monkeypatch.setattr(service, "_poll_task_until_done", poll)
    monkeypatch.setattr(httpx, "AsyncClient", ContentClient)
    image = b"png" if with_image else None
    assert await service.generate_url(prompt="scene", duration=3.5, image_bytes=image) == (
        "https://cdn.example.com/final.mp4"
    )
    url, payload, sent_image = submitted[0]
    assert url == "https://hi.hi.run/api/openai/v1/videos"
    assert payload == {"model": "h3-video", "prompt": "scene", "seconds": "4", "size": "1280x720"}
    assert sent_image == image
