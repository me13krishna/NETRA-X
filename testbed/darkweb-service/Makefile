# NETRA-X dark-web testbed.
# Run from testbed/darkweb-service/.

COMPOSE := docker compose
REPO_ROOT := ../..

.PHONY: help up down logs onion verify clean

help:
	@echo "NETRA-X testbed:"
	@echo "  make up      Start tor + the hidden service + the clearnet twin"
	@echo "  make onion   Print the generated .onion address"
	@echo "  make verify  Run NETRA-X's own probe and assert every leak is found"
	@echo "  make logs    Follow container logs"
	@echo "  make down    Stop and remove containers"
	@echo "  make clean   Also destroy the hidden-service key (new address next run)"

up:
	$(COMPOSE) up -d
	@echo ""
	@echo "  hidden-service content : http://localhost:8081"
	@echo "  clearnet twin          : http://localhost:8082"
	@echo ""
	@echo "  Tor needs a moment to publish the descriptor; then: make onion"

onion:
	@$(COMPOSE) exec -T tor cat /var/lib/tor/hidden_service/hostname 2>/dev/null \
		|| echo "Not ready yet -- tor is still generating the key. Try again shortly."

# Runs from the repo root so the packages import, and prefers the project venv
# so it behaves the same whether or not one is already activated.
verify:
	@cd $(REPO_ROOT) && \
	if [ -x .venv/Scripts/python.exe ]; then .venv/Scripts/python.exe testbed/darkweb-service/verify.py; \
	elif [ -x .venv/bin/python ]; then .venv/bin/python testbed/darkweb-service/verify.py; \
	else python testbed/darkweb-service/verify.py; fi

logs:
	$(COMPOSE) logs -f

down:
	$(COMPOSE) down

# Destroys the volume holding the hidden-service key, so the next `up`
# publishes a different .onion address.
clean:
	$(COMPOSE) down -v
