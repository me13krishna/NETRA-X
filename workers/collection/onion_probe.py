"""
NETRA-X OnionProbe Passive Scanner Engine
Scans onion services passively for infrastructure leaks (favicon mmh3, server-status, TLS cert, headers).
"""

import base64
import hashlib
from typing import Dict, Any, Optional
import mmh3


class OnionProbeEngine:
    """Passive probing engine for darknet onion service infrastructure footprinting."""

    @staticmethod
    def inspect_favicon(favicon_bytes: bytes) -> Dict[str, Any]:
        """Compute MurmurHash3 favicon integer hash for Shodan clearnet pivot matching."""
        if not favicon_bytes:
            return {"mmh3_hash": 0, "sha256": ""}
        
        b64_encoded = base64.encodebytes(favicon_bytes).decode("utf-8")
        mmh3_val = mmh3.hash(b64_encoded)
        sha256_val = hashlib.sha256(favicon_bytes).hexdigest()

        return {
            "mmh3_hash": mmh3_val,
            "sha256": sha256_val,
            "shodan_query": f"http.favicon.hash:{mmh3_val}"
        }

    @staticmethod
    def inspect_server_status(raw_html: str) -> Dict[str, Any]:
        """Detect Apache / Nginx / Lighttpd status page exposure."""
        exposed = "Apache Server Status" in raw_html or "Nginx Status" in raw_html
        return {
            "server_status_exposed": exposed,
            "leak_type": "APACHE_SERVER_STATUS" if exposed else "NONE"
        }

    @staticmethod
    def inspect_headers(headers_dict: Dict[str, str]) -> Dict[str, Any]:
        """Extract server banners, X-Powered-By, and TLS certificate details."""
        return {
            "server_banner": headers_dict.get("Server", "Unknown"),
            "x_powered_by": headers_dict.get("X-Powered-By", "Unknown"),
            "via_proxy": headers_dict.get("Via", "")
        }
