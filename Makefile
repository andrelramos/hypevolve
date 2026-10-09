.PHONY: test typecheck contracts lint

test:
	uv run --extra dev python -m pytest -q

typecheck:
	uv run --extra dev pyright

contracts:
	uv run --extra dev crosshair check hypevolve/contracts.py

lint: typecheck contracts
