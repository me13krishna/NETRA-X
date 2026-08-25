# NETRA-X test onion service

A self-hosted, isolated Tor hidden service for testing Module 1 (the infra-misconfig matcher). **Never point Module 1, OnionScan, or any scanner at a real, live onion service — only at this one.**

## How to run it

**1. Start the local web server** (the thing the hidden service actually points to):
```
cd test-site
python -m http.server 8080 --bind 127.0.0.1
```
This alone plants **misconfig #1**: Python's built-in server sends an un-stripped `Server:` header (e.g. `BaseHTTP/0.6 Python/3.x`), exactly the kind of default-banner leak a real careless operator would expose.

**2. Start the dedicated Tor process** (separate from Tor Browser, using the same `tor.exe` binary — see comments in `torrc`):
```
"C:\Users\Vivek\Desktop\Tor Browser\Browser\TorBrowser\Tor\tor.exe" -f "C:\Users\Vivek\Desktop\NETRA-X\test-onion-service\torrc"
```
Leave this window running. On first successful start, your test `.onion` address appears in:
```
test-onion-service\hidden_service\hostname
```

**3. Verify it's up** — open Tor Browser (the normal one) and visit the `.onion` address from that `hostname` file. You should see the test storefront page.

## Misconfigurations planted so far

| # | What | Where |
|---|---|---|
| 1 | Un-stripped default server banner | Free, from using `python -m http.server` as the backend |
| 2 | Exposed status/diagnostic page | `/server-status.html` — synthetic stand-in for a real leaked monitoring endpoint |

## Still to add (part of MVP 3, when Module 1 is actually built)

- **Reused TLS certificate** — needs a second "clearnet" HTTPS test server sharing the same self-signed cert as this onion service, so the `crt.sh`-matching logic has something real to find. Build this alongside the certificate-transparency lookup code, not before — no point maintaining it unused.
- **Shared favicon** — same idea: a `favicon.ico` reused between this service and a clearnet test host, for the Shodan favicon-hash matcher to catch.

Both are cheap to add once Module 1's actual matching logic exists — deliberately deferred so this test harness doesn't carry unused complexity ahead of the code that consumes it.
