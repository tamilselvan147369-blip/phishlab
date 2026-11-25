"""Unit tests for Vercel production integrations: Neon PostgreSQL, Upstash Redis Streams, and Vercel Blob Private Storage."""

import json
from unittest.mock import MagicMock, patch

from app import create_app
from security_platform.events import EventBroadcaster, STREAM_KEY
from security_platform.storage import store_demonstration_file, delete_demonstration_file, is_vercel_blob_configured


def test_upstash_redis_streams_and_no_redis_from_url_on_https(monkeypatch):
    """Upstash REST URLs must use upstash_redis.Redis Streams and NEVER redis.from_url()."""
    monkeypatch.setenv("UPSTASH_REDIS_REST_URL", "https://mock-upstash.upstash.io")
    monkeypatch.setenv("UPSTASH_REDIS_REST_TOKEN", "mock-token")
    monkeypatch.setenv("REDIS_URL", "https://mock-upstash.upstash.io")

    fake_client = MagicMock()
    fake_client.xread.return_value = [
        (STREAM_KEY, [("1700000000000-0", {"payload": json.dumps({"event_type": "link_opened"})})])
    ]
    fake_client.ping.return_value = "PONG"

    with patch("upstash_redis.Redis", return_value=fake_client) as mock_upstash_cls, \
         patch("redis.from_url") as mock_redis_from_url:
        eb = EventBroadcaster()
        mock_upstash_cls.assert_called_once_with(url="https://mock-upstash.upstash.io", token="mock-token")
        mock_redis_from_url.assert_not_called()

        eb.publish({"event_type": "link_opened", "campaign_id": 1})
        fake_client.xadd.assert_called_once()

        new_id, events = eb.read_stream_since("$")
        assert new_id == "1700000000000-0"
        assert len(events) == 1
        assert events[0]["event_type"] == "link_opened"
        assert eb.ping() == "upstash_connected"


def test_redis_from_url_ignores_https_url(monkeypatch):
    """Even without UPSTASH_REDIS_REST_URL, an https:// REDIS_URL must not be passed to redis.from_url()."""
    monkeypatch.delenv("UPSTASH_REDIS_REST_URL", raising=False)
    monkeypatch.delenv("KV_REST_API_URL", raising=False)
    monkeypatch.setenv("REDIS_URL", "https://some-rest-url.upstash.io")

    with patch("redis.from_url") as mock_redis_from_url:
        eb = EventBroadcaster()
        mock_redis_from_url.assert_not_called()
        assert eb._redis is None


def test_vercel_blob_private_storage_upload_and_delete(monkeypatch):
    """Vercel Blob uploads with x-access: private and deletes via /delete API."""
    monkeypatch.setenv("BLOB_READ_WRITE_TOKEN", "vercel_blob_rw_test_token")
    assert is_vercel_blob_configured() is True

    fake_put_resp = MagicMock()
    fake_put_resp.json.return_value = {"url": "https://private.blob.vercel-storage.com/abc_sample.txt"}

    with patch("security_platform.storage.requests.put", return_value=fake_put_resp) as mock_put, \
         patch("security_platform.storage.requests.post") as mock_post:
        stored_ref = store_demonstration_file("abc_sample.txt", b"hello", "text/plain")
        assert stored_ref == "https://private.blob.vercel-storage.com/abc_sample.txt"
        _, kwargs = mock_put.call_args
        assert kwargs["headers"]["x-access"] == "private"
        assert kwargs["headers"]["Authorization"] == "Bearer vercel_blob_rw_test_token"

        delete_demonstration_file(stored_ref)
        mock_post.assert_called_once()
        _, del_kwargs = mock_post.call_args
        assert del_kwargs["json"] == {"urls": [stored_ref]}


def test_healthz_reports_db_redis_and_storage(monkeypatch):
    """Health check returns database, redis, and storage status."""
    monkeypatch.delenv("BLOB_READ_WRITE_TOKEN", raising=False)
    app = create_app(test_config={
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
    })
    c = app.test_client()
    r = c.get("/healthz")
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "redis" in data
    assert data["storage"] == "local_filesystem"
