# apex.core — Foundation Layer

Infrastructure primitives only; zero trading logic (Book II 4.2). Everything
else in APEX is built on this package, and nothing here imports any other
APEX layer.

Modules: constants, enums, exceptions (coded `ABC-123` hierarchy), identity
(seedable `IdProvider`), `time/` (UTC `Timestamp`, injected `Clock`),
metadata (trace/correlation envelope), validation, serialization (canonical
JSON + SHA-256 hashing), types (concept value types), result (`Result[T]`),
base (`BaseObject` with lineage/versioning), context, versioning (semver +
stability levels), logging (structured JSON), config (schema-gated loader),
`contracts/` (infra interfaces), `events/` (event platform).

Tests: `tests/unit/core/`.
