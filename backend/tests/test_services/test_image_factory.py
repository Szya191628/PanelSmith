from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.config import Settings
from app.services.image import ImageProviderError
from app.services.image_factory import FallbackImageService, create_image_service


@pytest.mark.asyncio
async def test_fallback_keeps_reference_and_sticks_to_backup():
    primary = AsyncMock()
    backup = AsyncMock()
    primary.generate_url.side_effect = ImageProviderError("HTTP 429 quota", status_code=429)
    backup.generate_url.return_value = "https://cdn.test/backup.png"
    service = FallbackImageService(primary, backup, model="backup-model")

    kwargs = {"prompt": "a character", "image_bytes": b"reference", "size": "1024x1024"}
    assert await service.generate_url(**kwargs) == "https://cdn.test/backup.png"
    assert await service.generate_url(**kwargs) == "https://cdn.test/backup.png"
    assert primary.generate_url.await_count == 1
    assert backup.generate_url.await_count == 2
    backup.generate_url.assert_awaited_with(**kwargs)
    assert "backup-model" in service.fallback_notice


@pytest.mark.asyncio
async def test_fallback_does_not_retry_bad_prompt_or_payload():
    primary = AsyncMock()
    backup = AsyncMock()
    primary.generate_url.side_effect = RuntimeError("HTTP 400 invalid prompt")
    service = FallbackImageService(primary, backup, model="backup-model")
    with pytest.raises(RuntimeError, match="invalid prompt"):
        await service.generate_url(prompt="draw")
    backup.generate_url.assert_not_awaited()


@pytest.mark.asyncio
async def test_both_providers_fail_without_endless_switching():
    primary = AsyncMock()
    backup = AsyncMock()
    primary.generate_url.side_effect = ImageProviderError("主服务额度不足", status_code=429)
    backup.generate_url.side_effect = ImageProviderError("备用服务不可用", status_code=503)
    service = FallbackImageService(primary, backup, model="backup-model")
    with pytest.raises(ImageProviderError, match="备用服务不可用"):
        await service.generate_url(prompt="draw")
    assert primary.generate_url.await_count == backup.generate_url.await_count == 1


def test_factory_builds_backup_with_distinct_endpoint():
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:", image_provider="openai",
        image_base_url="https://image.test/v1", image_api_key="primary-key",
        image_model="primary-model", image_endpoint="/chat/completions",
        image_fallback_model="backup-model", image_fallback_endpoint="/images/generations",
    )
    service = create_image_service(settings)
    assert isinstance(service, FallbackImageService)
    assert service.backup.settings.image_model == "backup-model"
    assert service.backup.settings.image_endpoint == "/images/generations"
    assert service.backup.settings.image_api_key == "primary-key"


def test_different_backup_host_requires_its_own_key():
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:", image_provider="openai",
        image_base_url="https://primary.test", image_api_key="primary-key",
        image_fallback_model="backup-model", image_fallback_base_url="https://backup.test",
    )
    with pytest.raises(ValueError, match="单独配置备用 API 密钥"):
        create_image_service(settings)


def test_create_image_service_openai():
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        image_provider="openai",
        image_base_url="https://image.example.com",
        image_api_key="test",
    )
    svc = create_image_service(settings)
    from app.services.image import ImageService

    assert isinstance(svc, ImageService)


def test_create_image_service_modelscope():
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        image_provider="modelscope",
        image_base_url="https://api-inference.modelscope.cn",
        image_api_key="test",
    )
    svc = create_image_service(settings)
    from app.services.image import ImageService

    assert isinstance(svc, ImageService)


def test_create_image_service_fake():
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        image_provider="fake",
        fake_image_fixture_url="/static/images/dev.png",
    )
    svc = create_image_service(settings)
    from app.services.fake_image import FakeImageService

    assert isinstance(svc, FakeImageService)


def test_create_image_service_unsupported():
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        image_provider="unsupported",
    )
    with pytest.raises(ValueError, match="Unsupported image provider"):
        create_image_service(settings)
