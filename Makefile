.PHONY: install test lint demo check

install:
	python3 -m pip install -e ".[dev]"

test:
	python3 -m pytest

lint:
	python3 -m ruff check .

demo:
	python3 -m mcp_server.demo

check:
	python3 -m mcp_server.server --check
