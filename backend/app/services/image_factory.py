from __future__ import annotations

from typing import Any, Protocol

from app.config import Settings
from app.services.image import ImageProviderError


class ImageServiceProtocol(Protocol):
    async def generate(self, **kwargs: Any) -> dict[str, Any]:
        ...

    async def generate_url(
        self,
        *,
        prompt: str,
        size: str = "1024x1024",
        image_bytes: bytes | None = None,
        **kwargs: Any,
    ) -> str:
        ...

    async def cache_external_image(self, url: str) -> str:
        ...


class FallbackImageService:
    """Use the configured backup after a provider-wide failure, for this run only."""

    def __init__(self, primary: ImageServiceProtocol, backup: ImageServiceProtocol, *, model: str):
        self.primary = primary
        self.backup = backup
        self.model = model
        self.active = primary
        self.fallback_notice: str | None = None

    async def _call(self, method: str, kwargs: dict[str, Any]) -> Any:
        try:
            return await getattr(self.active, method)(**kwargs)
        except ImageProviderError as primary_error:
            if self.active is self.backup:
                raise
            self.active = self.backup
            self.fallback_notice = f"主图像服务暂不可用，已尝试切换备用模型 {self.model}。"
            try:
                result = await getattr(self.backup, method)(**kwargs)
            except Exception as backup_error:
                detail = str(backup_error) if isinstance(backup_error, ImageProviderError) else "备用服务请求失败"
                raise ImageProviderError(
                    f"主图像服务失败：{primary_error}；备用模型 {self.model} 也未成功：{detail}",
                    status_code=getattr(backup_error, "status_code", 0),
                ) from backup_error
            self.fallback_notice = f"已自动切换到备用图像模型 {self.model}，继续生成图片。"
            return result

    async def generate(self, **kwargs: Any) -> dict[str, Any]:
        return await self._call("generate", kwargs)  # type: ignore[no-any-return]

    async def generate_url(self, **kwargs: Any) -> str:
        return await self._call("generate_url", kwargs)  # type: ignore[no-any-return]

    async def cache_external_image(self, url: str) -> str:
        return await self.active.cache_external_image(url)

    async def close(self) -> None:
        for service in (self.primary, self.backup):
            close = getattr(service, "close", None)
            if callable(close):
                await close()


def create_image_service(settings: Settings) -> ImageServiceProtocol:
    primary = _create_single_image_service(settings)
    fallback_model = (settings.image_fallback_model or "").strip()
    if settings.image_provider.lower() == "fake" or not fallback_model:
        return primary
    # A new host needs an explicit backup key; never send the primary secret to
    # a different server merely because a fallback URL has been entered.
    backup_url = (settings.image_fallback_base_url or settings.image_base_url).strip()
    if backup_url.rstrip("/") != settings.image_base_url.rstrip("/") and not settings.image_fallback_api_key:
        raise ValueError("备用图像服务地址不同时，必须单独配置备用 API 密钥")
    backup_settings = settings.model_copy(update={
        "image_provider": (settings.image_fallback_provider or settings.image_provider).strip().lower(),
        "image_model": fallback_model,
        "image_base_url": backup_url,
        "image_api_key": settings.image_fallback_api_key or settings.image_api_key,
        "image_endpoint": settings.image_fallback_endpoint or settings.image_endpoint,
        "image_fallback_model": None,
    })
    if backup_settings.image_provider not in {"openai", "modelscope"}:
        raise ValueError("备用图像提供商仅支持 openai 或 modelscope")
    return FallbackImageService(primary, _create_single_image_service(backup_settings),
                                model=backup_settings.image_model)


def _create_single_image_service(settings: Settings) -> ImageServiceProtocol:
    provider = settings.image_provider.lower()
    if provider in {"openai", "modelscope"}:
        from app.services.image import ImageService

        return ImageService(settings)
    if provider == "fake":
        from app.services.fake_image import FakeImageService

        return FakeImageService(settings)
    raise ValueError(f"Unsupported image provider: {settings.image_provider}")
