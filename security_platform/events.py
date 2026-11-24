"""Real-time event broadcasting architecture using Server-Sent Events (SSE).

Supports multi-threaded in-memory SSE event streams for Gunicorn gthread workers,
and optional Redis pub/sub broadcasting when scaling across multiple worker processes.
"""

import os
import json
import queue
import threading
from typing import Dict, Any
from datetime import datetime, timezone


class EventBroadcaster:
    """Thread-safe pub/sub event broadcaster for live dashboard updates.

    In a multi-threaded Gunicorn worker (worker_class='gthread', workers=1, threads=8),
    all incoming participant events are immediately broadcast to all active SSE client
    threads in memory.

    When multi-process scaling is enabled (workers > 1), setting the REDIS_URL
    environment variable automatically activates shared cross-process message bus.
    """

    def __init__(self):
        self._subscribers = []
        self._lock = threading.Lock()
        self._redis = None

        redis_url = os.getenv('REDIS_URL')
        if redis_url:
            try:
                import importlib
                redis_mod = importlib.import_module('redis')
                self._redis = redis_mod.from_url(redis_url)
                pubsub = self._redis.pubsub()
                pubsub.subscribe(**{'phishlab_events': self._handle_redis_message})
                t = threading.Thread(target=pubsub.run_in_thread, kwargs={'sleep_time': 0.05}, daemon=True)
                t.start()
            except Exception:
                self._redis = None

    def _handle_redis_message(self, message):
        if message and message.get('type') == 'message':
            try:
                data = json.loads(message.get('data'))
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
        """Broadcast event to all connected dashboard clients."""
        if self._redis:
            try:
                self._redis.publish('phishlab_events', json.dumps(event_data))
                return
            except Exception:
                pass
        self._dispatch_local(event_data)


from datetime import datetime, timezone

# Global broadcaster instance
broadcaster = EventBroadcaster()


def broadcast_event(event_type: str, campaign_id: int, details: str, browser: str = 'Unknown', os: str = 'Unknown', device: str = 'Desktop'):
    """Helper to publish an event to all live monitoring dashboards."""
    broadcaster.publish({
        'event_type': event_type,
        'campaign_id': campaign_id,
        'details': details,
        'browser_family': browser,
        'os_family': os,
        'device_category': device,
        'timestamp': datetime.now(timezone.utc).strftime('%H:%M:%S UTC')
    })
