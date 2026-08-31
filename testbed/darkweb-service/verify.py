"""
Verify the testbed against NETRA-X's own probe.

A testbed nobody checks drifts: someone rewords the status page, or tightens an
nginx directive, and the misconfiguration the demo depends on quietly stops
existing. This runs the real OnionProbeEngine and ExtractionEngine against the
running containers and asserts each planted leak is still detected.

Run it from the repository root (so the packages import) or via `make verify`:

    python testbed/darkweb-service/verify.py

Exits non-zero if any leak has gone missing, so it can gate a demo or CI.

It talks to the localhost bindings rather than over Tor. The misconfigurations
are properties of the HTTP responses, not of the transport, so putting Tor in
the path would test Tor rather than the probe -- and would make this unusable
without a running Tor client.
"""

import sys
import urllib.error
import urllib.request

ONION_HOST = "http://127.0.0.1:8081"
CLEARNET_HOST = "http://127.0.0.1:8082"

GREEN, RED, DIM, RESET = "\033[32m", "\033[31m", "\033[90m", "\033[0m"

results: list[tuple[bool, str, str]] = []


def check(ok: bool, name: str, detail: str = "") -> bool:
    results.append((ok, name, detail))
    mark = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
    print(f"  [{mark}] {name}")
    if detail:
        print(f"         {DIM}{detail}{RESET}")
    return ok


def fetch(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "netrax-testbed-verify/1"})
    with urllib.request.urlopen(req, timeout=6) as r:
        return r.read(), dict(r.headers)


def main() -> int:
    try:
        from workers.collection.onion_probe import OnionProbeEngine
        from workers.extraction import ExtractionEngine
    except ImportError as e:
        print(f"{RED}Cannot import the NETRA-X workers: {e}{RESET}")
        print("Run from the repository root, with the venv active.")
        return 2

    print("\nNETRA-X testbed verification")
    print("=" * 62)

    try:
        index_body, index_headers = fetch(ONION_HOST + "/")
        status_body, _ = fetch(ONION_HOST + "/server-status")
        onion_icon, _ = fetch(ONION_HOST + "/favicon.ico")
        clear_icon, _ = fetch(CLEARNET_HOST + "/favicon.ico")
    except (urllib.error.URLError, OSError) as e:
        print(f"{RED}Testbed is not reachable: {e}{RESET}")
        print("Start it first:  make up")
        return 2

    html = index_body.decode("utf-8", "replace")
    status_html = status_body.decode("utf-8", "replace")

    # ---- LEAK 1: the favicon pivot -------------------------------------
    print(f"\n{DIM}LEAK 1 - shared favicon (the clearnet pivot){RESET}")
    onion_fav = OnionProbeEngine.inspect_favicon(onion_icon)
    clear_fav = OnionProbeEngine.inspect_favicon(clear_icon)
    check(
        onion_icon == clear_icon,
        "favicon bytes are identical across both hosts",
        f"{len(onion_icon)} bytes",
    )
    check(
        onion_fav["mmh3_hash"] == clear_fav["mmh3_hash"],
        "mmh3 hashes match, so the pivot resolves",
        f"mmh3={onion_fav['mmh3_hash']}  {onion_fav['shodan_query']}",
    )

    # ---- LEAK 2: status page -------------------------------------------
    print(f"\n{DIM}LEAK 2 - exposed status page{RESET}")
    st = OnionProbeEngine.inspect_server_status(status_html)
    check(st["server_status_exposed"], "probe flags the status page as exposed",
          f"leak_type={st['leak_type']}")
    check("vendor-edge-01.internal" in status_html,
          "status page leaks the internal hostname",
          "vendor-edge-01.internal")
    check("vesper-supply.example" in status_html,
          "VHost column ties a clearnet hostname to the same box",
          "corroborates the favicon pivot independently")

    # ---- LEAKS 3-5: headers --------------------------------------------
    print(f"\n{DIM}LEAKS 3-5 - response headers{RESET}")
    hdrs = OnionProbeEngine.inspect_headers(index_headers)
    check(hdrs["server_banner"] not in ("Unknown", ""),
          "Server banner is present rather than stripped",
          hdrs["server_banner"])
    check(hdrs["x_powered_by"] not in ("Unknown", ""),
          "X-Powered-By discloses the stack",
          hdrs["x_powered_by"])
    check(bool(hdrs["via_proxy"]),
          "Via header leaks an internal host",
          hdrs["via_proxy"])

    # ---- LEAK 6: extractable identifiers --------------------------------
    print(f"\n{DIM}LEAK 6 - identifiers extractable from the page body{RESET}")
    ent = ExtractionEngine.extract_entities(html)
    for key, label in [
        ("pgp_fingerprints", "PGP fingerprint"),
        ("btc_addresses", "BTC address"),
        ("eth_addresses", "ETH address"),
        ("emails", "email"),
        ("handles", "handle"),
    ]:
        found = ent.get(key) or []
        check(bool(found), f"{label} extracted",
              ", ".join(str(v)[:44] for v in found[:3]))

    # ---- summary --------------------------------------------------------
    passed = sum(1 for ok, _, _ in results if ok)
    total = len(results)
    print("\n" + "=" * 62)
    if passed == total:
        print(f"{GREEN}All {total} checks passed - the testbed is intact.{RESET}\n")
        return 0
    print(f"{RED}{total - passed} of {total} checks failed.{RESET}")
    for ok, name, _ in results:
        if not ok:
            print(f"  {RED}-{RESET} {name}")
    print("\nA failure here means the testbed and the probe have drifted apart:")
    print("either the planted leak was removed, or the probe stopped detecting it.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
