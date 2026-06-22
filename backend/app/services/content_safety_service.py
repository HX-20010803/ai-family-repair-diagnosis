from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Callable
from urllib.request import Request, urlopen

from app.core.config import settings


class ContentSafetyConfigError(RuntimeError):
    pass


class ContentSafetyProviderError(RuntimeError):
    pass


class ContentSafetyProvider:
    name = "base"

    def check(self, text: str) -> tuple[bool, list[str]]:
        raise NotImplementedError


class LocalKeywordProvider(ContentSafetyProvider):
    name = "local"
    BLOCKED_WORDS = ("违法", "炸药", "自杀", "色情")

    def check(self, text: str) -> tuple[bool, list[str]]:
        hits = [word for word in self.BLOCKED_WORDS if word in text]
        return len(hits) == 0, hits


TencentTransport = Callable[[str, dict[str, str], str, int], dict[str, Any]]


class TencentTextModerationProvider(ContentSafetyProvider):
    name = "tencent"
    endpoint = "https://tms.tencentcloudapi.com"
    service = "tms"
    action = "TextModeration"
    version = "2020-12-29"

    def __init__(
        self,
        secret_id: str,
        secret_key: str,
        region: str = "ap-guangzhou",
        timeout_seconds: int = 10,
        transport: TencentTransport | None = None,
        max_retries: int = 2,
    ):
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.region = region
        self.timeout_seconds = timeout_seconds
        self.transport = transport or self._default_transport
        self.max_retries = max_retries

    def check(self, text: str) -> tuple[bool, list[str]]:
        payload = {
            "Content": base64.b64encode(text.encode("utf-8")).decode("ascii"),
        }
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        data = self._call_with_retry(body)
        response = data.get("Response", data)
        if isinstance(response, dict) and response.get("Error"):
            error = response["Error"]
            code = error.get("Code", "Unknown") if isinstance(error, dict) else "Unknown"
            message = error.get("Message", str(error)) if isinstance(error, dict) else str(error)
            raise ContentSafetyProviderError(f"Tencent content safety failed: {code}: {message}")

        suggestion = str(response.get("Suggestion", "")).strip().lower() if isinstance(response, dict) else ""
        hits = self._extract_hits(response if isinstance(response, dict) else {})
        safe = suggestion not in {"block", "review"}
        if not safe and not hits:
            hits = [suggestion]
        return safe, hits

    def _call_with_retry(self, body: str) -> dict[str, Any]:
        # Retry only transient transport-layer errors (timeouts, connection resets).
        # Tencent business errors (Response.Error, e.g. AuthFailure) surface from
        # check() after a successful HTTP round-trip and must NOT be retried —
        # re-sign on every attempt because the TC3 timestamp expires.
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            headers = self._signed_headers(body)
            try:
                return self.transport(self.endpoint, headers, body, self.timeout_seconds)
            except Exception as exc:
                last_exc = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(0.5 * (attempt + 1))
        raise ContentSafetyProviderError(
            f"Tencent content safety request failed after {self.max_retries + 1} attempts: {last_exc}"
        ) from last_exc

    def _signed_headers(self, body: str, timestamp: int | None = None) -> dict[str, str]:
        timestamp = timestamp or int(time.time())
        host = "tms.tencentcloudapi.com"
        content_type = "application/json; charset=utf-8"
        canonical_headers = (
            f"content-type:{content_type}\n"
            f"host:{host}\n"
            f"x-tc-action:{self.action.lower()}\n"
        )
        signed_headers = "content-type;host;x-tc-action"
        hashed_request_payload = hashlib.sha256(body.encode("utf-8")).hexdigest()
        canonical_request = (
            "POST\n/\n\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{hashed_request_payload}"
        )

        request_date = time.strftime("%Y-%m-%d", time.gmtime(timestamp))
        credential_scope = f"{request_date}/{self.service}/tc3_request"
        hashed_canonical_request = hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
        string_to_sign = (
            "TC3-HMAC-SHA256\n"
            f"{timestamp}\n"
            f"{credential_scope}\n"
            f"{hashed_canonical_request}"
        )

        secret_date = self._hmac_sha256(("TC3" + self.secret_key).encode("utf-8"), request_date)
        secret_service = self._hmac_sha256(secret_date, self.service)
        secret_signing = self._hmac_sha256(secret_service, "tc3_request")
        signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
        authorization = (
            "TC3-HMAC-SHA256 "
            f"Credential={self.secret_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )

        return {
            "Authorization": authorization,
            "Content-Type": content_type,
            "Host": host,
            "X-TC-Action": self.action,
            "X-TC-Version": self.version,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Region": self.region,
        }

    @staticmethod
    def _hmac_sha256(key: bytes, message: str) -> bytes:
        return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()

    @staticmethod
    def _default_transport(url: str, headers: dict[str, str], body: str, timeout: int) -> dict[str, Any]:
        request = Request(url, data=body.encode("utf-8"), headers=headers, method="POST")
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _extract_hits(response: dict[str, Any]) -> list[str]:
        hits: list[str] = []
        label = response.get("Label")
        if label:
            hits.append(str(label))
        for detail in response.get("DetailResults") or []:
            if not isinstance(detail, dict):
                continue
            detail_label = detail.get("Label") or detail.get("SubLabel")
            if detail_label:
                hits.append(str(detail_label))
        return list(dict.fromkeys(hits))


class ContentSafetyService:
    def __init__(self, provider: ContentSafetyProvider | None = None):
        self.provider = provider or build_provider_from_config()

    @classmethod
    def from_config(
        cls,
        deployment_mode: str,
        provider_name: str,
        access_key: str,
        secret_key: str,
        region: str = "ap-guangzhou",
        timeout_seconds: int = 10,
    ) -> "ContentSafetyService":
        return cls(build_provider_from_config(deployment_mode, provider_name, access_key, secret_key, region, timeout_seconds))

    @property
    def provider_name(self) -> str:
        return self.provider.name

    def check_text(self, text: str) -> tuple[bool, list[str]]:
        return self.provider.check(text)


def build_provider_from_config(
    deployment_mode: str | None = None,
    provider_name: str | None = None,
    access_key: str | None = None,
    secret_key: str | None = None,
    region: str | None = None,
    timeout_seconds: int | None = None,
) -> ContentSafetyProvider:
    mode = deployment_mode if deployment_mode is not None else settings.deployment_mode
    provider = (provider_name if provider_name is not None else settings.content_safety_provider).strip().lower()
    key = access_key if access_key is not None else settings.content_safety_access_key
    secret = secret_key if secret_key is not None else settings.content_safety_secret_key
    provider_region = region if region is not None else settings.content_safety_region
    provider_timeout = timeout_seconds if timeout_seconds is not None else settings.content_safety_timeout_seconds

    if provider == "local":
        if mode in {"external_test", "production"}:
            raise ContentSafetyConfigError("local content safety is not allowed for external_test or production.")
        return LocalKeywordProvider()

    if provider == "tencent":
        if key and secret:
            return TencentTextModerationProvider(key, secret, provider_region, provider_timeout)
        if mode == "internal_demo":
            return LocalKeywordProvider()
        raise ContentSafetyConfigError(f"{provider} content safety keys are required for {mode}.")

    if provider in {"aliyun", "baidu"}:
        if mode == "internal_demo" and not (key or secret):
            return LocalKeywordProvider()
        raise ContentSafetyConfigError(f"Unsupported formal content safety provider: {provider}. Supported: tencent.")

    raise ContentSafetyConfigError(f"Unsupported content safety provider: {provider}")


def get_content_safety_runtime_status(
    deployment_mode: str | None = None,
    provider_name: str | None = None,
    access_key: str | None = None,
    secret_key: str | None = None,
    region: str | None = None,
    timeout_seconds: int | None = None,
) -> dict:
    requested_provider = (provider_name if provider_name is not None else settings.content_safety_provider).strip().lower()
    try:
        provider = build_provider_from_config(deployment_mode, provider_name, access_key, secret_key, region, timeout_seconds)
    except ContentSafetyConfigError as exc:
        return {
            "content_safety_provider": requested_provider,
            "content_safety_active_provider": None,
            "content_safety_configured": False,
            "content_safety_status": "error",
            "content_safety_error": str(exc),
        }
    return {
        "content_safety_provider": requested_provider,
        "content_safety_active_provider": provider.name,
        "content_safety_configured": True,
        "content_safety_status": "ok",
    }
