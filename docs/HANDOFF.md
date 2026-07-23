# APEX Continuation Handoff (Phases 12-15)

You are taking over the APEX project mid-build. Previous agents built
phases 0-11 across earlier threads; you continue from the next pending
phase exactly as if you were them. Do not restart, re-plan, or
re-derive anything already built. This file is the complete bootstrap:
together with `docs/PHASES.md` and `manifest.yaml` (both authoritative
at the current head of `main`), it carries everything a fresh thread
needs.

## The project

APEX - "Autonomous Probabilistic Execution eXchange": an
institutional-grade, deterministic, non-repainting Python 3.13+ crypto
trading platform for the Toobit exchange, re-engineered from the AICE
Pine Script v6 indicator, following 16 phases (0-15) defined in the
specification books under `docs/specs/`:

- `01_architecture.md` - Book I (system design; chapters marked `فصل N`)
- `02_aice_reverse.md` - Book II (implementation spec, the migration bible)
- `03_constitution.md` - Book III (binding engineering constitution)
- `04_telegram_bot.md` - Book IV (Telegram console blueprint)
- `05_optimization.md` - Book V (optimizer blueprint, `## Part N` markers)
- `06_aice_pine.md` - Book VI (the full AICE Pine source - parity target)
- `07_toobit_api.md` - Book VII (Toobit REST/WS API reference)
- `08_master_prompt.md` - Book VIII (original master prompt)

Everything is in this repository. Never ask the user to re-upload
specs. Read them surgically (grep for `فصل N` / `## Part N` markers,
then targeted line ranges) - never whole books.

## First actions in a fresh thread

1. `git clone https://github.com/sinamoosazadeh/APEX.git`
2. `pip install uv` if absent (lands in `~/.local/bin` - add to PATH),
   then `uv sync` (provisions its own Python 3.13+; use `uv run` for
   every gate; `python3` for helper scripts).
3. Read `docs/PHASES.md` and `manifest.yaml` fully - they are the
   project state. The "Next up" section defines your phase.
4. Verify the gates locally before building anything:
   `uv run ruff check apex tests` (clean), `uv run mypy` (strict,
   clean), `uv run pytest -p no:cacheprovider` (all pass; note the
   project's addopts hide the summary under `-q` piping - grep for
   "passed"), `uv run python -m apex --check` (all plugins healthy).
5. Begin the next phase per the ritual below.

## Standing working rules (established by the user - never re-ask)

1. Proceed autonomously in blueprint order. Complete the current phase
   FULLY - including rewiring its documented deferrals when their
   prerequisites land - before starting a new one. Never ask which
   subsection to build next. The only stop is the GitHub push approval.
2. Conflict priority: Constitution (Book III) -> Book I -> Book II ->
   AICE logic. Binding rules: Python 3.13+, mypy strict, frozen
   dataclasses with slots, no TODOs/placeholders/fake logic, no
   repainting (confirmed bars only), determinism (seeded randomness;
   injected Clock - `datetime.now()` only inside
   `apex/core/time/clock.py`), everything-is-config, coded errors
   (ABC-123 pattern; grep used codes before allocating), `Result[T]`,
   files <=800 lines where practical, functions <=50 lines, downward-only
   dependencies (layer order: core < domain < contracts < storage <
   security < features < probability < decision < portfolio <
   optimization < execution < research < monitoring < telegram; only
   `apex/__main__.py` composes across layers), no bare asserts in
   production code
   (type-narrowing asserts after explicit checks are established
   precedent).
3. Per-phase ritual: extract spec surgically -> plan in the thread's
   Working Doc -> build -> tests -> gates (ruff / mypy strict / pytest /
   `python -m apex --check`) -> live validation on real Toobit data ->
   update `docs/PHASES.md` (phase row + gate results + next-up) +
   `manifest.yaml` (version, phases_complete, module versions,
   registries) + version bump (`pyproject.toml` AND
   `apex/__init__.py`) + **update the "state at handoff" block at the
   bottom of this file** -> git commit locally -> stage push payloads ->
   ask the user's approval ONCE (one card listing the staged files) ->
   push -> PR main->develop -> merge -> verify CI green on both
   branches -> sync local (`git fetch && git reset --hard origin/main`)
   -> report.
4. Commit messages end with:
   `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`
5. Start each phase in a FRESH thread (context-budget discipline: a
   thread near its window ceiling costs several times more per step).
   Keep working notes in the thread's Working Doc so compaction never
   loses state.

## GitHub push protocol (learned the hard way - do exactly this)

- `github__push_files` fails with 403 (no Git database permission).
  Instead: for each changed file, call `github__create_or_update_file`
  sequentially with a paramsFile JSON written to /tmp
  (`{owner: "sinamoosazadeh", repo: "APEX", branch: "main", path,
  message: "<commit msg> [i/N] <path>\n\nCo-Authored-By: ...",
  content, and "sha" for UPDATES}`). Fetch SHAs beforehand from the
  public tree API:
  `curl https://api.github.com/repos/sinamoosazadeh/APEX/git/trees/main?recursive=1`.
- **Content encoding (the Phase 12 corruption)**: `content` in the
  paramsFile must be the RAW file text - never base64-encode it
  yourself (the integration encodes internally; double-encoding lands
  base64 garbage on the branch, which is exactly how the first
  Phase 12 push corrupted all 42 files it delivered before dying at
  [42/65]). The post-push `git hash-object` byte-integrity check is
  MANDATORY before opening the PR - it catches this class of
  corruption immediately. If you ever find base64 blobs on main,
  decode them in place (`base64.b64decode`) - the content round-trips.
- The API rejects empty files - give empty `__init__.py` files a
  docstring.
- Workflow files (`.github/workflows/`) cannot be pushed via the
  integration - hand them to the user to add via the GitHub web UI.
- After pushing: verify byte integrity (`git hash-object` per file vs
  the fresh tree API SHAs), then `github__create_pull_request`
  main->develop + `github__merge_pull_request`, then check CI via
  `https://api.github.com/repos/sinamoosazadeh/APEX/actions/runs` -
  both branches must be success.
- Never delegate uploads to subagents - do them in the main thread.

## Sandbox quirks (environment, not APEX bugs)

- The sandbox egress proxy CA lacks the Authority-Key-Identifier
  extension, so Python 3.13+ strict X.509 makes the PRODUCTION Toobit
  client fail ONLY inside the sandbox (CERTIFICATE_VERIFY_FAILED on
  `apex ingest/sync`). For live-data validation, write a throwaway
  /tmp script that patches `ssl.create_default_context` to strip
  `ssl.VERIFY_X509_STRICT`, boots the Kernel, resolves
  `BarIngestionPipeline` and ingests 520 bars per series for
  BTCUSDT/ETHUSDT x 1h/4h. NEVER weaken TLS in production code.
- Then validate live:
  `uv run python -m apex features|probability|decide|portfolio|execute|research|optimize-signal|optimize-risk|orchestrate ... --symbol BTCUSDT --timeframe 1h --bars 519`.
- Production gates fire ~0 signals on 13 days of quiet data (honest
  AICE selectivity). To exercise trade-dependent mechanics live, use a
  relaxed in-memory kernel fold (threshold 0.52, contributors 2,
  cooldown 6, timing immediate, expectancy off) feeding production
  engines - in memory or isolated tmp stores only, never the runtime
  stores.

## Remaining phases (scope pointers; PHASES.md "Next up" is authoritative)

- **Phase 12 - Monitoring + Telegram console**: COMPLETE (see the
  PHASES.md row).
- **Phase 13 - Security platform**: COMPLETE (see the PHASES.md row).
- **Phase 14 - Deployment**: packaging, runtime layout, service
  lifecycle for the target device (Termux/mobile per Book V part 7
  resource notes), backup/restore - Book II deployment chapters.
- **Phase 15 - Production Validation**: the full acceptance pass -
  deep-history optimizer acceptance runs, end-to-end paper operation,
  every quality gate, final documentation.

## Deferral map (rewire when prerequisites land; also listed per-row in PHASES.md)

- Phase 12: DONE - listenKey user-data fills, shadow mode + the full
  promotion pipeline, Telegram menus and kill-switch surfaces all
  landed. Kill-switch position FLATTENING joins Phase 13 (the security
  response), alongside:
- Phase 13: DONE - the vault-first credential chain, kill-switch
  FLATTENED response, audit ledger, signing and secure preflight all
  landed. The vault MASTER key still arrives via the APEX_MASTER_KEY
  environment variable (the model's documented root); OS-keyring
  storage on the Termux target belongs to Phase 14 deployment.
- Backlog (schedule where their phase fits): automatic
  hypothesis/pattern/strategy discovery + synthetic markets + ablation
  (research corpus), Kalman filter, crypto dominance context,
  multi-exchange backfill, funding/OI enrichment, SOR + book-depth
  engines (TWAP/VWAP/POV/iceberg/impact/fill-probability), latency
  budgets, bracket ladder legs as venue algo orders.

## Facts that save time

- `uv` lives at `~/.local/bin/uv` after pip install; the venv Python
  reports 3.14.x (>=3.13 requirement satisfied).
- pytest count at handoff: 561; boot: 12 plugins / 13 modules healthy.
- `config.section(name)` exposes EVERY config file's raw mapping
  (deep-validated files included) since Phase 10.
- Learned per-file push commits mean local and remote histories
  diverge after a push - always `git fetch && git reset --hard
  origin/main` after CI is green.
- Error-code families in use: CFG, DAT, DEC, EVT, EXE, FEA, KRN, MKT,
  MON, OPT, PRT, RES, RSK, SER, SIG, STO, TGM, VAL - grep before
  allocating.
- Module versioning: bump only touched modules (semver), project
  version 0.1x.0 per phase.
- The kernel/portfolio/execution/research CLIs and the runtime
  injector are wired end to end - `apex decide` consults research for
  active artifacts + learning state automatically.

## State at handoff (update this block at every phase close)

- Version 0.15.0; phases 0-13 complete; Phase 14 (Deployment) is next.
- 561 tests passing; ruff + mypy strict clean (288 files); 12 plugins /
  13 modules boot healthy.
- Security platform live: vault (APEX_MASTER_KEY -> scrypt -> Fernet;
  canonical secret names in apex/security/vault.py), hash-chained
  audit ledger, HMAC artifact/config signing (research injector
  verifies sha256 + signature on stamped artifacts), access policy,
  secure preflight gating `apex run --live` (SEC-040), kill-switch
  FLATTENED response (venue reduce-only closes + ledger close at the
  emergency mark). CLI: secrets/audit/kill/secure-check.
- Phase 13 close validation: paper preflight PASSED sealed; live
  preflight refused honestly without credentials (exit 1); kill drill
  entries_disabled -> flattened -> release; audit chain VALID over the
  8-entry operator trail.

## Previous state (Phase 12 close)

- Version 0.14.0; phases 0-12 complete.
- 536 tests passing; ruff + mypy strict clean (269 files); 11 plugins /
  12 modules boot healthy.
- Phase 12 recovery note: the original Phase 12 push (an earlier
  account) base64-corrupted all 42 files it delivered and died at
  [42/65]; this state decodes those 42 in place (byte-perfect
  round-trip) and rebuilds the never-pushed seam (~15 files: the
  research promotion store/service/events API, Monitoring/Telegram
  error classes, the listenKey client trio + PUT transport, the
  kernel's ModuleRegistry DI registration, telemetry/system config
  wiring, plugin promotion settings, boot/config test expectations).
- Trading: toobit `trading: true` (signed v2 client + listenKey user
  stream); paper execution is the run-mode default; live requires
  run_mode live + env credentials.
- Live validation (Phase 12 close): fresh 520-bar ingests x 4 series;
  full pipeline on today's market; `apex monitor` unified status +
  snapshot (12/12 healthy); `apex run --seconds 15` held a live WS
  loop session cleanly; `apex telegram` honest TGM-004 without
  credentials; orchestrator drained 2 real jobs with honest rejections
  (nothing shadow-registered on thin history). The promotion lifecycle
  (shadow -> evaluate -> approve/reject -> guard rollback; durable
  queue pause) is proven end-to-end through the booted platform in the
  suite. Deep-history acceptance belongs to Phase 15.
