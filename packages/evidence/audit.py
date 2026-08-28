"""
SHA-256 Hash-Chained Audit Logging Service
Ensures tamper-evident, append-only provenance for every sensitive platform action.
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.evidence.uuid7 import uuidv7_str
from apps.api.database.models import AuditLog

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"


def compute_payload_hash(data: Dict[str, Any]) -> str:
    """Compute deterministic SHA-256 hash of payload JSON."""
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def append_audit_event(
    session: Session,
    actor_user_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    payload: Dict[str, Any]
) -> AuditLog:
    """Append a hash-chained audit event to the authoritative ledger."""
    # Find preceding log entry to get prev_hash
    last_log = session.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    ).scalars().first()

    prev_hash = last_log.payload_hash if last_log else GENESIS_HASH
    payload_hash = compute_payload_hash({
        "actor_user_id": actor_user_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "payload": payload,
        "prev_hash": prev_hash,
    })

    audit_entry = AuditLog(
        id=uuidv7_str(),
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        payload_hash=payload_hash,
        prev_hash=prev_hash,
        created_at=datetime.utcnow()
    )

    session.add(audit_entry)
    session.flush()
    return audit_entry


def verify_audit_chain(session: Session) -> Tuple[bool, int, Optional[str]]:
    """Verify integrity of the entire SHA-256 audit log hash chain."""
    logs = session.execute(
        select(AuditLog).order_by(AuditLog.created_at.asc(), AuditLog.id.asc())
    ).scalars().all()

    if not logs:
        return True, 0, None

    expected_prev = GENESIS_HASH
    for i, log in enumerate(logs):
        if log.prev_hash != expected_prev:
            return False, i, f"Chain broken at record {log.id}: prev_hash mismatch"
        expected_prev = log.payload_hash

    return True, len(logs), None
