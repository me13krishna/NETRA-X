"""
NETRA-X Redis Streams Event Bus & Pipeline Coordinator
Dispatches PAGE_COLLECTED -> EXTRACTION_COMPLETED -> RELATIONSHIP_DISCOVERED -> GRAPH_PROJECTED events.
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Callable, Optional

try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False


class RedisEventBus:
    """Redis Streams event bus for real-time asynchronous pipeline coordination."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self.client = None
        self.in_memory_queue: List[Dict[str, Any]] = []

        if HAS_REDIS:
            try:
                self.client = redis.from_url(redis_url, decode_responses=True)
            except Exception:
                self.client = None

    def publish_event(self, stream_name: str, event_data: Dict[str, Any]) -> str:
        """Publish event to Redis Stream or fallback queue."""
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "payload": json.dumps(event_data)
        }

        if self.client:
            try:
                msg_id = self.client.xadd(stream_name, payload)
                return str(msg_id)
            except Exception:
                pass

        # Fallback to in-memory event tracking
        msg_id = f"mem_{len(self.in_memory_queue) + 1}"
        self.in_memory_queue.append({"stream": stream_name, "id": msg_id, "data": payload})
        return msg_id
