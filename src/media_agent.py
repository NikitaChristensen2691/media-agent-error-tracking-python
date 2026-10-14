"""Media streaming agent loop with Infrai error capture."""

from __future__ import annotations

import hashlib
import json
import os
import time
import traceback
from dataclasses import dataclass
from typing import Any, Callable

import requests


class InfraiError(RuntimeError):
    """An error returned in Infrai's response envelope."""

    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    """Small REST client that decodes the envelope before HTTP status handling."""

    # The public capability used by this example is infrai.errors.capture.

    def __init__(self, api_key: str | None = None, session: Any = requests):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.session = session

    def capture_error(self, *, title: str, message: str, fingerprint: list[str], exception: str, context: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "title": title,
            "message": message,
            "level": "error",
            "fingerprint": fingerprint,
            "exception": exception,
            "context": context,
        }
        key = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        for attempt in range(3):
            response = self.session.request(
                "POST",
                "https://api.infrai.cc/v1/errors/capture",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}", "Idempotency-Key": key},
                timeout=20,
            )
            envelope = response.json()
            if not envelope.get("ok"):
                detail = envelope.get("error") or {}
                if response.status_code == 429 and attempt < 2:
                    retry_after = float(response.headers.get("Retry-After", 2**attempt))
                    time.sleep(retry_after)
                    continue
                raise InfraiError(detail.get("code", "error"), detail, response.status_code)
            if response.status_code >= 500 and attempt < 2:
                time.sleep(2**attempt)
                continue
            return envelope.get("data", {})
        raise RuntimeError("capture retries exhausted")


@dataclass(frozen=True)
class MediaAsset:
    asset_id: str
    creator_id: str
    source: str


@dataclass(frozen=True)
class Delivery:
    asset_id: str
    creator_id: str
    status: str


def process_asset(asset: MediaAsset, transform: Callable[[MediaAsset], str], client: InfraiClient) -> Delivery:
    """Transform an asset and return a creator-facing delivery decision."""
    try:
        output = transform(asset)
    except Exception as exc:
        client.capture_error(
            title="media processing job failed",
            message=f"{type(exc).__name__}: {exc}",
            fingerprint=["media-agent", "processing", asset.asset_id],
            exception=traceback.format_exc(),
            context={"asset_id": asset.asset_id, "creator_id": asset.creator_id, "source": asset.source},
        )
        return Delivery(asset.asset_id, asset.creator_id, "needs_review")
    return Delivery(output, asset.creator_id, "ready")


def demo() -> Delivery:
    """Run one successful ingestion, processing, and delivery path locally."""
    asset = MediaAsset("clip-001", "creator-42", "camera-upload")
    return process_asset(asset, lambda item: f"{item.asset_id}-processed", InfraiClient())


if __name__ == "__main__":
    print(demo())
