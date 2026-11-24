"""Simulator utilities for PhishLab.

Currently the Flask routes directly record events, but this module can be
extended to simulate additional victim behaviours (e.g., delayed opens or
multiple clicks). It provides a simple async‑style helper that can be
scheduled via the /schedule slash command.
"""

import time
from threading import Thread
from .database import db, Event
from .app import record_event  # avoid circular import by importing lazily in actual use

def delayed_event(campaign_id: int, event_type: str, delay_seconds: int):
    """Record an event after a delay (in a background thread).

    This can be used to mimic realistic user interaction timing.
    """
    def _worker():
        time.sleep(delay_seconds)
        record_event(campaign_id, event_type)
    Thread(target=_worker, daemon=True).start()
