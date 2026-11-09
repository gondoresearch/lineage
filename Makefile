# Run lineage from source: the backend (uvicorn) and the GUI (Vite dev server).
#
#   make install   install the backend and frontend dependencies (once)
#   make build     build the GUI for production into frontend/dist; the backend then also
#                  serves it at http://127.0.0.1:$(BACKEND_PORT), without the Vite dev server
#   make start     start both in the background
#   make stop      stop both
#   make restart   stop, then start
#   make status    show whether each one is running
#   make docs      build the documentation into site/ (make docs-install once first)
#   make docs-serve  serve the documentation at http://127.0.0.1:$(DOCS_PORT), reloading on edits
#   make screenshots retake the documentation screenshots (needs Playwright and Chromium)
#
# Override any of these on the command line, e.g. `make start DATA_DIR=/tmp/lineage-test`.
DATA_DIR     ?= ./data
BACKEND_PORT ?= 8000
GUI_PORT     ?= 5173
DOCS_PORT    ?= 8001

RUN_DIR := .run
VENV    := .venv
BACKEND_PID := $(RUN_DIR)/backend.pid
GUI_PID     := $(RUN_DIR)/gui.pid

SHELL := /bin/bash

# Is the process in pid file $(1) running?
running = [ -f $(1) ] && kill -0 $$(cat $(1)) 2>/dev/null

.PHONY: install build docs-install docs docs-serve screenshots start stop restart status start-backend start-gui stop-backend stop-gui

install:
	[ -d $(VENV) ] || python3 -m venv $(VENV)
	$(VENV)/bin/pip install -e "./backend[test]"
	cd frontend && npm install

build:
	@[ -x frontend/node_modules/.bin/vite ] || { echo "No frontend/node_modules: run 'make install' first."; exit 1; }
	cd frontend && npm run build

docs-install:
	$(VENV)/bin/pip install -r docs/requirements.txt

docs:
	@[ -x $(VENV)/bin/mkdocs ] || { echo "No $(VENV)/bin/mkdocs: run 'make docs-install' first."; exit 1; }
	$(VENV)/bin/mkdocs build --strict

docs-serve:
	@[ -x $(VENV)/bin/mkdocs ] || { echo "No $(VENV)/bin/mkdocs: run 'make docs-install' first."; exit 1; }
	$(VENV)/bin/mkdocs serve --dev-addr 127.0.0.1:$(DOCS_PORT)

screenshots: build
	@$(VENV)/bin/python -c "import playwright" 2>/dev/null || { echo "Playwright is missing: $(VENV)/bin/pip install playwright"; exit 1; }
	$(VENV)/bin/python docs/screenshots.py

start: start-backend start-gui
	@echo "GUI:     http://localhost:$(GUI_PORT)"
	@echo "Backend: http://127.0.0.1:$(BACKEND_PORT)   (data: $(DATA_DIR))"
	@echo "Logs:    $(RUN_DIR)/backend.log, $(RUN_DIR)/gui.log"

# Each one runs in its own session (setsid) so `stop` can end it with all its children.
start-backend:
	@mkdir -p $(RUN_DIR)
	@if $(call running,$(BACKEND_PID)); then echo "Backend already running (pid $$(cat $(BACKEND_PID)))."; exit 0; fi; \
	[ -x $(VENV)/bin/uvicorn ] || { echo "No $(VENV)/bin/uvicorn: run 'make install' first."; exit 1; }; \
	DATA_DIR="$(DATA_DIR)" setsid $(VENV)/bin/uvicorn --factory backend.app:create_app \
		--host 127.0.0.1 --port $(BACKEND_PORT) > $(RUN_DIR)/backend.log 2>&1 < /dev/null & \
	echo $$! > $(BACKEND_PID); \
	for i in $$(seq 50); do \
		curl -s -o /dev/null http://127.0.0.1:$(BACKEND_PORT)/api/version && { echo "Backend started (pid $$(cat $(BACKEND_PID)))."; exit 0; }; \
		$(call running,$(BACKEND_PID)) || break; \
		sleep 0.2; \
	done; \
	echo "Backend did not start; see $(RUN_DIR)/backend.log:"; tail -n 20 $(RUN_DIR)/backend.log; exit 1

start-gui:
	@mkdir -p $(RUN_DIR)
	@if $(call running,$(GUI_PID)); then echo "GUI already running (pid $$(cat $(GUI_PID)))."; exit 0; fi; \
	[ -x frontend/node_modules/.bin/vite ] || { echo "No frontend/node_modules: run 'make install' first."; exit 1; }; \
	(cd frontend && API_URL=http://127.0.0.1:$(BACKEND_PORT) exec setsid node_modules/.bin/vite \
		--port $(GUI_PORT) --strictPort) > $(RUN_DIR)/gui.log 2>&1 < /dev/null & \
	echo $$! > $(GUI_PID); \
	for i in $$(seq 50); do \
		curl -s -o /dev/null http://localhost:$(GUI_PORT)/ && { echo "GUI started (pid $$(cat $(GUI_PID)))."; exit 0; }; \
		$(call running,$(GUI_PID)) || break; \
		sleep 0.2; \
	done; \
	echo "GUI did not start; see $(RUN_DIR)/gui.log:"; tail -n 20 $(RUN_DIR)/gui.log; exit 1

stop: stop-gui stop-backend

# Ends the whole process group; waits up to 5 s, then forces it.
define stop_one
	@if $(call running,$(1)); then \
		pid=$$(cat $(1)); kill -TERM -- -$$pid 2>/dev/null || kill -TERM $$pid; \
		for i in $$(seq 25); do kill -0 $$pid 2>/dev/null || break; sleep 0.2; done; \
		kill -0 $$pid 2>/dev/null && kill -KILL -- -$$pid 2>/dev/null; \
		echo "$(2) stopped."; \
	else echo "$(2) not running."; fi; \
	rm -f $(1)
endef

stop-backend:
	$(call stop_one,$(BACKEND_PID),Backend)

stop-gui:
	$(call stop_one,$(GUI_PID),GUI)

restart: stop start

status:
	@if $(call running,$(BACKEND_PID)); then echo "Backend: running (pid $$(cat $(BACKEND_PID)), port $(BACKEND_PORT))"; else echo "Backend: stopped"; fi
	@if $(call running,$(GUI_PID)); then echo "GUI:     running (pid $$(cat $(GUI_PID)), port $(GUI_PORT))"; else echo "GUI:     stopped"; fi
