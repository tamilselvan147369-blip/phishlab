"""Real-time event broadcasting architecture using Server-Sent Events (SSE).

Supports:
1. Upstash Redis REST + Redis Streams (UPSTASH_REDIS_REST_URL + UPSTASH_REDIS_REST_TOKEN)
   for serverless Vercel deployments across isolated function invocations.
2. Standard redis:// pub/sub (REDIS_URL) for multi-worker Gunicorn deployments.
3. Thread-safe in-memory SSE queues for local development and single-worker mode.
"""

import os
import json
import queue
import threading
import importlib
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone

STREAM_KEY = "phishlab:events"


class EventBroadcaster:
    """Pub/sub and Redis Streams event broadcaster for live dashboard updates."""

    def __init__(self):
        self._subscribers = []
        self._lock = threading.Lock()
        self._redis = None
        self._upstash = None

        # 1. Upstash Redis REST (serverless-safe, uses Redis Streams)
        upstash_url = (os.getenv("UPSTASH_REDIS_REST_URL") or os.getenv("KV_REST_API_URL") or "").strip()
        upstash_token = (os.getenv("UPSTASH_REDIS_REST_TOKEN") or os.getenv("KV_REST_API_TOKEN") or "").strip()
        if upstash_url and upstash_token:
            try:
                upstash_mod = importlib.import_module("upstash_redis")
                self._upstash = upstash_mod.Redis(url=upstash_url, token=upstash_token)
            except Exception:
                self._upstash = None

        # 2. Standard TCP redis:// / rediss:// (never pass Upstash HTTPS REST URL to redis.from_url)
        redis_url = (os.getenv("REDIS_URL") or "").strip()
        if not self._upstash and redis_url.startswith(("redis://", "rediss://")):
            try:
                redis_mod = importlib.import_module("redis")
                self._redis = redis_mod.from_url(redis_url)
                pubsub = self._redis.pubsub()
                pubsub.subscribe(**{"phishlab_events": self._handle_redis_message})
                t = threading.Thread(target=pubsub.run_in_thread, kwargs={"sleep_time": 0.05}, daemon=True)
                t.start()
            except Exception:
                self._redis = None

    def _handle_redis_message(self, message):
        if message and message.get("type") == "message":
            try:
                data = json.loads(message.get("data"))
                self._dispatch_local(data)
            except Exception:
                pass

    def subscribe(self) -> queue.Queue:
        """Register a new SSE client subscriber queue."""
        q = queue.Queue(maxsize=100)
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue):
        """Unregister a disconnected subscriber queue."""
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def _dispatch_local(self, event_data: Dict[str, Any]):
        with self._lock:
            dead_queues = []
            for q in self._subscribers:
                try:
                    q.put_nowait(event_data)
                except queue.Full:
                    dead_queues.append(q)
            for dq in dead_queues:
                if dq in self._subscribers:
                    self._subscribers.remove(dq)

    def publish(self, event_data: Dict[str, Any]):
        """Broadcast event via Upstash Redis Streams, redis:// pub/sub, and local queues."""
        if self._upstash:
            try:
                self._upstash.xadd(
                    STREAM_KEY,
                    "*",
                    {"payload": json.dumps(event_data)},
                    maxlen=1000,
                    approximate_trim=True,
                )
            except Exception:
                pass
        elif self._redis:
            try:
                self._redis.publish("phishlab_events", json.dumps(event_data))
                return
            except Exception:
                pass
        self._dispatch_local(event_data)

    def read_stream_since(self, last_id: str = "$", count: int = 20) -> Tuple[str, List[Dict[str, Any]]]:
        """Read new events from Upstash Redis Stream starting after last_id."""
        if not self._upstash:
            return last_id, []
        try:
            res = self._upstash.xread({STREAM_KEY: last_id}, count=count)
            if not res:
                return last_id, []
            events = []
            newest_id = last_id
            for _stream_name, entries in res:
                for entry_id, fields in entries:
                    newest_id = entry_id
                    if isinstance(fields, dict) and "payload" in fields:
                        events.append(json.loads(fields["payload"]))
                    elif isinstance(fields, list) and len(fields) >= 2:
                        for i in range(0, len(fields) - 1, 2):
                            if fields[i] == "payload":
                                events.append(json.loads(fields[i + 1]))
            return newest_id, events
        except Exception:
            return last_id, []

    def ping(self) -> str:
        """Return health status of configured Redis backend."""
        if self._upstash:
            try:
                self._upstash.ping()
                return "upstash_connected"
            except Exception:
                return "unavailable"
        if self._redis:
            try:
                self._redis.ping()
                return "connected"
            except Exception:
                return "unavailable"
        if os.getenv("UPSTASH_REDIS_REST_URL") or os.getenv("KV_REST_API_URL") or os.getenv("REDIS_URL"):
            return "unavailable"
        return "not_configured"


# Global broadcaster instance
broadcaster = EventBroadcaster()


def broadcast_event(event_type: str, campaign_id: int, details: str, browser: str = "Unknown", os: str = "Unknown", device: str = "Desktop"):
    """Helper to publish an event to all live monitoring dashboards."""
    broadcaster.publish({
        "event_type": event_type,
        "campaign_id": campaign_id,
        "details": details,
        "browser_family": browser,
        "os_family": os,
        "device_category": device,
        "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
    })
