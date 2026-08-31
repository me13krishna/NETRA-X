# Dark-web test service

A self-hosted Tor v3 hidden service with **deliberately planted misconfigurations**, so
NETRA-X's infrastructure module has a real, live target to detect against instead of a
fixture.

It runs entirely on your own machine, in its own Docker network, serving content this
team wrote. That is the whole point: it makes the infra-misconfig capability
demonstrable without ever touching a real hidden service.

---

## The rule this exists to respect

**Point the scanner at this and nothing else.**

The project's guardrails are explicit that the infrastructure module is only ever run
against the team's own isolated instance. A scanner aimed at somebody else's hidden
service is a different activity with a different legal character, regardless of intent.
This testbed exists so there is never a reason to do that.

Everything served here is fabricated. The handles, keys, wallets and addresses in the
content are synthetic strings generated for this repository — they do not belong to
anyone, and the BTC/ETH addresses are documentation examples, not live wallets.

---

## What is planted, and what finds it

Each leak below is matched to the specific check in
[`workers/collection/onion_probe.py`](../../workers/collection/onion_probe.py) that
detects it. If you change the probe, change these too — a testbed that no longer
matches its scanner tests nothing.

| # | Planted leak | Detected by | Signal produced |
|---|---|---|---|
| 1 | **Shared favicon** — byte-identical `favicon.ico` on the hidden service and on a clearnet host | `inspect_favicon()` | `mmh3 = 297738526`, giving `http.favicon.hash:297738526` as a Shodan pivot to the clearnet twin |
| 2 | **Exposed status page** at `/server-status` containing the literal string `Apache Server Status` | `inspect_server_status()` | `server_status_exposed = true`, `leak_type = APACHE_SERVER_STATUS` |
| 3 | **Un-stripped `Server` banner** — nginx announces its version rather than hiding it | `inspect_headers()` | `server_banner`, tying the onion to a specific build |
| 4 | **`X-Powered-By` header** left in place | `inspect_headers()` | `x_powered_by`, narrowing the stack |
| 5 | **`Via` proxy header** leaking an internal hostname | `inspect_headers()` | `via_proxy`, exposing infrastructure behind the service |
| 6 | **Extractable identifiers** in the page body — PGP fingerprint, BTC/ETH addresses, handles, contact email | `workers/extraction/extractor.py` | Feeds `POST /api/v1/evidence` end to end |

Leak 1 is the interesting one. The others say *what* the server is; the shared favicon
says *where else the operator runs*, which is the actual de-anonymisation step.

---

## Running it

### Without Docker (fastest, and enough for the infra demo)

Every planted leak is a property of the HTTP *response*, not of the transport,
so the probe cannot tell a container from a local server. This needs nothing
installed:

```bash
python testbed/darkweb-service/serve_local.py     # terminal 1
python testbed/darkweb-service/verify.py          # terminal 2
```

What you give up: no real `.onion` address and no exercise of Tor itself. For
the infra-misconfig capability that costs nothing, because the module inspects
what the service returns. For anything about Tor behaviour, use Docker.

### With Docker (the full article)

Requires Docker with Compose v2.

```bash
cd testbed/darkweb-service
make up            # start tor + the hidden service + the clearnet twin
make onion         # print the generated .onion address
make verify        # run NETRA-X's own probe against it and assert every leak is found
make logs          # follow tor + nginx
make down          # stop and remove containers
make clean         # also destroy the hidden-service key (new address next time)
```

`make up` generates a fresh v3 onion address on first run and keeps it in a Docker
volume, so the address is stable across restarts until you `make clean`.

### Reaching it

The hidden service is reachable over Tor at the address `make onion` prints. For quick
iteration without a Tor client, both sites are also bound to localhost:

- Hidden-service content: <http://localhost:8081>
- Clearnet twin: <http://localhost:8082>

`make verify` uses the localhost bindings, so it works without a Tor client attached.
That is deliberate — the misconfigurations are properties of the HTTP responses, not of
the transport, so testing them does not require Tor to be in the path.

---

## Why a clearnet twin

The pivot only means something if there is somewhere to pivot *to*. The twin plays the
role of the operator's public-facing site: same favicon, different hostname, no attempt
to hide. It is what a Shodan favicon-hash query would surface in the real workflow, and
without it leak 1 has no second half.

---

## Layout

```
testbed/darkweb-service/
├── docker-compose.yml     tor + two nginx hosts on an isolated network
├── torrc                  hidden service definition
├── nginx/
│   ├── onion.conf         the leaky config -- banners on, status page served
│   └── clearnet.conf      the twin
├── site/                  hidden-service content (+ the shared favicon)
├── clearnet-twin/         public-facing content (+ the same favicon bytes)
├── verify.py              runs onion_probe against both and asserts detection
└── Makefile
```

## A note on the hidden-service key

Tor generates a private key that *is* the onion address. It lives in a Docker volume and
is excluded from git. Committing it would publish the identity of the service and let
anyone impersonate it — harmless for a throwaway test address, a bad habit to build.
