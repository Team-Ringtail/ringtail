# Frontend TODO

Current frontend lives inside `main.jac` as `cl def:pub app`.

## Reliability

- [ ] Add explicit loading/error states for each async action (paste, benchmark, repo).
- [ ] Surface server validation errors directly in UI (not only generic messages).
- [ ] Add per-request debug panel (route + payload + response snippet).

## UX

- [ ] Split large sections into internal helper blocks while preserving Jac compatibility.
- [ ] Add copy-to-clipboard for optimized code/results.
- [ ] Add compact run-history panel backed by `get_recent_jobs`.

## GitHub / Repo Tab

- [ ] Improve guidance when OAuth/App config is missing.
- [ ] Show current auth mode/install status from `get_auth_readiness` inline.
- [ ] Add "preflight check" action that calls `get_config_doctor` before submit.

## Benchmark Tab

- [ ] Add benchmark presets for top_k/per_file_k.
- [ ] Add clearer mapping from progress stage -> backend operation.
- [ ] Add retry/resume helpers when demo jobs are interrupted.
