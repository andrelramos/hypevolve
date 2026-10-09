# Repository agent instructions

## State safety and correctness

- Use `icontract` for preconditions, postconditions, and invariants at boundaries that create, transition, or persist execution state.
- A contract must express an observable property without side effects; do not duplicate type validation already covered by annotations.
- Do not introduce session states outside `queued`, `running`, `completed`, and `failed`. A completed or failed execution must never return to `running`.
- Run `make lint` before delivering Python changes. This gate uses UV, runs strict Pyright, and runs `crosshair check hypevolve/contracts.py` to find symbolic contract violations.
- All new or modified code under `hypevolve/` must be fully typed. Do not use `Any`, `# type: ignore`, or casts to silence Pyright without a local, verifiable justification.

## Code navigation

If `.codegraph/` exists at the repository root, run `codegraph explore` before grep/find to locate or understand symbols.

## Language policy

- All repository code and newly added repository text must be written in English.
- Every text added to the project website must be translated for all supported site languages: Portuguese, English, Spanish, Chinese, and Japanese.
