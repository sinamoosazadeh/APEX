# apex.domain — Shared Kernel

Book II 29.5. The immutable objects every engine speaks in: `Money`, `Bar`
(with the `require_closed()` non-repainting gate), `Tick`, `Signal` (full
5.5 contract with geometry validation), `Order`, `Trade`, `Feature`,
`ProbabilityAssessment` (distribution must sum to 1), `RiskAssessment`,
`Position`, `PortfolioSnapshot`, `StateSnapshot`.

Entities extend `BaseObject`: UUID identity, lineage versioning via
`evolve()`, semantic equality, stable content hashes. Bars/ticks are pure
data contracts with natural keys.

Tests: `tests/unit/domain/`.
