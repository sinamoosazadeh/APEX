# config — Configuration Set

Twelve schema-gated YAML files (Book II 3.6, 5.18). `system.yaml` and
`logging.yaml` are consumed and deep-validated by the kernel today; the ten
phase-owned files are shape+`schema_version`-gated until their phases ship
deep schemas. The platform refuses to boot on any violation.

Scalar env overrides: `APEX__<FILE>__<KEY>[__<NESTED>]`, e.g.
`APEX__LOGGING__LEVEL=debug`. Secrets never live here (Phase 13 owns them).
