"""
Time-Ordered UUIDv7 Generator (RFC 9562 compliant)
Used across NETRA-X for entity IDs, evidence IDs, event IDs, case IDs, hypothesis IDs, and audit IDs.
"""

import os
import time
import uuid

def generate_uuidv7() -> uuid.UUID:
    """Generate a time-ordered UUIDv7."""
    timestamp_ms = int(time.time() * 1000)
    time_high = (timestamp_ms >> 16) & 0xFFFFFFFF
    time_low = timestamp_ms & 0xFFFF

    random_bytes = os.urandom(10)
    rand_a = int.from_bytes(random_bytes[:2], 'big') & 0x0FFF
    rand_b = int.from_bytes(random_bytes[2:], 'big') & 0x3FFFFFFFFFFFFFFF

    time_and_version = (time_low << 16) | 0x7000 | rand_a
    variant_and_rand_b = 0x8000000000000000 | rand_b

    int_val = (time_high << 96) | (time_and_version << 64) | variant_and_rand_b
    return uuid.UUID(int=int_val)

def uuidv7_str() -> str:
    """Return string representation of a new UUIDv7."""
    return str(generate_uuidv7())
