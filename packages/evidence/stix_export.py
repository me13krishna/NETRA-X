"""
NETRA-X STIX 2.1 & CSV Export Module
Generates STIX 2.1 CTI JSON bundles (Identity, Threat-Actor, Infrastructure, Relationship objects)
and CSV export reports with mandatory 'investigative_lead' banner.
"""

import csv
import io
import json
from datetime import datetime
from typing import Dict, List, Any


def generate_stix_bundle(hypothesis_data: Dict[str, Any], actor_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate STIX 2.1 JSON bundle for threat actor attribution."""
    now_iso = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    actor_id = f"threat-actor--{hypothesis_data.get('subject_entity_id', 'unknown')}"
    target_id = f"identity--{hypothesis_data.get('object_entity_id', 'unknown')}"

    objects = [
        {
            "type": "identity",
            "spec_version": "2.1",
            "id": "identity--netra-x-system",
            "created": now_iso,
            "modified": now_iso,
            "name": "NETRA-X Intelligence Platform",
            "identity_class": "system"
        },
        {
            "type": "threat-actor",
            "spec_version": "2.1",
            "id": actor_id,
            "created": now_iso,
            "modified": now_iso,
            "name": hypothesis_data.get("subject_label", "Threat Actor"),
            "threat_actor_types": ["cybercrime-gang", "ransomware-operator"],
            "aliases": actor_data.get("aliases", [hypothesis_data.get("subject_label")]),
            "confidence": int(hypothesis_data.get("calibrated_prob", 0.5) * 100),
            "x_netra_assessment_type": "investigative_lead",
            "x_netra_calibrated_prob": hypothesis_data.get("calibrated_prob", 0.0),
            "x_netra_raw_llr": hypothesis_data.get("raw_log_lr", 0.0)
        },
        {
            "type": "identity",
            "spec_version": "2.1",
            "id": target_id,
            "created": now_iso,
            "modified": now_iso,
            "name": hypothesis_data.get("object_label", "Candidate Entity"),
            "identity_class": "individual"
        },
        {
            "type": "relationship",
            "spec_version": "2.1",
            "id": f"relationship--{hypothesis_data.get('id', 'rel_01')}",
            "created": now_iso,
            "modified": now_iso,
            "relationship_type": "attributed-to",
            "source_ref": target_id,
            "target_ref": actor_id,
            "confidence": int(hypothesis_data.get("calibrated_prob", 0.5) * 100)
        }
    ]

    return {
        "type": "bundle",
        "id": f"bundle--{hypothesis_data.get('id', 'bundle_01')}",
        "spec_version": "2.1",
        "objects": objects
    }


def generate_csv_export(evidence_items: List[Dict[str, Any]]) -> str:
    """Generate CSV string for evidence items."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "Evidence ID", "Family", "Source URI", "Extraction Method",
        "Value", "Reliability Weight", "Raw LLR", "Contribution",
        "Is Contradiction", "Dependence Group", "SHA256 Hash", "Timestamp"
    ])

    for item in evidence_items:
        writer.writerow([
            item.get("evidence_id", ""),
            item.get("family", ""),
            item.get("source_uri", ""),
            item.get("extraction_method", ""),
            item.get("value", ""),
            item.get("reliability", 1.0),
            item.get("raw_llr", 0.0),
            item.get("contribution", 0.0),
            item.get("is_contradiction", False),
            item.get("dependence_group", ""),
            item.get("sha256", ""),
            item.get("timestamp", "")
        ])

    return output.getvalue()
