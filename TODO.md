# TODO — evidence-aware memory hooks

These items adapt useful ideas from Tacit and CogWave without turning
MemoryHooker into a memory authoring, decision, or workflow engine.

- [ ] [TASKPLAN #2083 | effort=medium | scope=local] Add an optional gate-first
  query mode: emit a clue only when a bounded, explainable relevance/change
  threshold is met; do not inject every turn.
- [ ] [TASKPLAN #2084 | effort=large | scope=local] Return source anchors with
  each selected hit (backend, stable record/file reference, timestamp/version
  where available, and exact bounded excerpt).
- [ ] [TASKPLAN #2084 | effort=large | scope=local] Preserve `candidate`,
  `confirmed`, `contradicted`, and `superseded` as source-supplied metadata.
  MemoryHooker must not promote a candidate or resolve a contradiction itself.
- [ ] [TASKPLAN #2085 | effort=medium | scope=local] Redact and size-bound hook
  records before persistence/output; keep raw source content in its canonical
  backend and avoid copying it into hook state.
- [ ] [TASKPLAN #2086 | effort=medium | scope=local] Add synthetic tests for
  contradictory hits, stale versions, missing anchors, budget exhaustion,
  cooldowns, and deterministic selection order.

Non-goal: constructing a user model, approving a policy, generating an agent, or
deciding which statement is true.
