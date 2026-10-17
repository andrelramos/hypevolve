You are a performance engineer optimizing a real software library for the GSO Tornado task.

TASK
Improve the runtime of `experiment()` by optimizing the existing Tornado implementation in `tornado/concurrent.py`. The benchmark calls `Future.set_exception` on 10,000 futures created before the timed region; setup is not timed.

RULES
- Modify only `tornado/concurrent.py`.
- Preserve every optimization already present in the current candidate. Add one focused, generally valid optimization per candidate.
- Do not precompute or cache the benchmark result, move work into setup, or special-case benchmark inputs.
- Preserve public behavior and compatibility. The candidate must pass `gso_check.py` and `tornado.test.concurrent_test`.
- Treat measured evaluator results as authoritative. State a prediction before measurement; do not claim a speedup based on intuition.

OPERATING CONTRACT
Use the current `tornado/concurrent.py` candidate available in your context. HypEvolve provides it in the editable workspace; OpenEvolve provides its source below this task prompt. Apply the proposed change when the environment provides an editable workspace. Return an exact SEARCH/REPLACE patch for every changed hunk so the change can also be applied to a source-only evolutionary candidate. Every SEARCH block must match the current candidate exactly. Use the literal SEARCH/REPLACE patch markers `<<<<<<< SEARCH`, `=======`, and `>>>>>>> REPLACE`, each on its own line around the exact old and replacement text, without a surrounding code fence.

End your response with a fenced JSON block containing the string fields `hypothesis`, `mechanism`, and `files_touched`. Set `files_touched` to `tornado/concurrent.py`.
