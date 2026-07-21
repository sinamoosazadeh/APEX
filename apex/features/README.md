# apex.features — Feature Platform

Book II ch. 7/17, Phase 4. The AICE migration home:

- `registry.py` — every feature is declared (name, family, version,
  default params) before it can be computed; the pipeline rejects
  undeclared emissions.
- `pipeline.py` — the sanctioned path: load confirmed bars → run pure
  engines → validate against the registry → persist idempotently →
  publish catalog events.
- `calculations.py` — shared Pine-faithful primitives: Wilder ATR,
  SMA-seeded EMA, strict pivot tracking, rolling extremes.
- `structure/` — the first migrated family (AICE Book VI, structure
  block): strict-pivot swings, BOS/CHoCH state machine, break quality
  with decay, displacement, dealing range (premium/discount/OTE),
  sweeps, equal highs/lows. 19 features, faithful to the Pine source.
- `liquidity/` — the second family: confidence pools decayed per bar
  and bumped by equal extremes at three pivot scales (exact AICE
  ternary priority), resting-liquidity composites, external-extreme
  proximity, sweep efficiency, stop hunts, inducement. 16 features.

The store lives in `apex/storage/features.py`, anchored to
(exchange, symbol, timeframe, bar open time).

Run it: `python -m apex features --symbol BTCUSDT --timeframe 1h`

Tests: `tests/unit/features/`.
