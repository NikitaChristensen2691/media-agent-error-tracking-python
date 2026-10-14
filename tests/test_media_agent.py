from media_agent import Delivery, InfraiClient, MediaAsset, process_asset


class RecordingClient(InfraiClient):
    def __init__(self):
        self.captured = []

    def capture_error(self, **payload):
        self.captured.append(payload)
        return {"event_id": "evt-test"}


def test_processing_exception_becomes_review_delivery_and_is_captured():
    client = RecordingClient()
    asset = MediaAsset("clip-7", "creator-2", "upload")

    def rejected_transform(_asset):
        raise ValueError("codec rejected")

    result = process_asset(asset, rejected_transform, client)

    assert result == Delivery("clip-7", "creator-2", "needs_review")
    assert client.captured[0]["fingerprint"] == ["media-agent", "processing", "clip-7"]


def test_successful_processing_is_ready_for_creator():
    client = RecordingClient()
    result = process_asset(MediaAsset("clip-8", "creator-2", "upload"), lambda _: "clip-8-h264", client)
    assert result == Delivery("clip-8-h264", "creator-2", "ready")
    assert client.captured == []
