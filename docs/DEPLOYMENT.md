# APEX Deployment Runbook (Phase 14)

Book II 29.20/29.25 and Book V part 7: how APEX installs, runs
supervised, backs up, restores and updates on the target device
(Termux/mobile) or any Linux host. The platform is restart-safe by
design - every store is durable SQLite, events archive append-only,
and the kernel recovers state on boot (13.20) - so the OS wrapper is
the supervisor.

## 1. Install (Termux)

```bash
bash deploy/termux/install.sh
```

Manual equivalent: `pkg install python git python-cryptography termux-api`,
`pip install uv`, clone the repository, `uv sync`. On a Linux server the
distribution's Python >= 3.13 plus `pip install uv` suffices; the
`cryptography` wheel installs normally there.

Book V part 7 device budgets: **RAM < 500 MB, background CPU < 50%**.
The defaults in `config/` respect them (bounded windows, streaming
optimization, sequential job drain).

## 2. Provision secrets (Phase 13 security)

The vault master key is the single root secret and only ever lives in
the environment (13.7):

```bash
export APEX_MASTER_KEY="<long random master key>"   # add to ~/.bashrc
VALUE="<key>"    uv run apex secrets set --name toobit_api_key --from-env VALUE
VALUE="<secret>" uv run apex secrets set --name toobit_api_secret --from-env VALUE
# Optional Telegram console:
VALUE="<token>"  uv run apex secrets set --name telegram_bot_token --from-env VALUE
VALUE="<ids>"    uv run apex secrets set --name telegram_admin_chat_ids --from-env VALUE
uv run apex secrets seal          # signs the config hash (13.10)
uv run apex secure-check --live   # must PASS before live trading (13.11)
```

Secret values never travel through argv; rotation:
`NEW=<key> uv run apex secrets rotate --from-env NEW` (then update
`APEX_MASTER_KEY`).

## 3. Run supervised (29.20)

```bash
bash deploy/termux/apex-service.sh
```

The wrapper holds a wake lock, runs due scheduled jobs, starts the
monitored operational loop (`apex run --seconds 0`), and on ANY exit
backs off exponentially and relaunches - watchdog + auto-recovery at
the OS boundary. Start on device boot by copying
`deploy/termux/boot-apex.sh` into `~/.termux/boot/` (Termux:Boot app).

Live trading additionally requires `run_mode: live` in
`config/system.yaml`; the loop refuses to start live when the secure
preflight fails (SEC-040).

## 4. Recurring jobs (Book V part 7)

`config/scheduler.yaml` drives the long-horizon lifecycle (sync,
snapshot, study, optimize, backup); `config/device.yaml` carries the
pressure guards. Under load or low disk, due jobs DEFER - never run
partially:

```bash
uv run apex schedule          # status + pressure
uv run apex schedule --run    # execute what is due
```

Stamps persist in the key/value store, so restarts never double-run.

## 5. Backup and restore (13.19/13.20; 25.30)

```bash
uv run apex backup                       # consistent, checksummed archive
uv run apex restore --archive backups/apex-backup-<ts>.tar.gz --force
```

Backups copy SQLite through the backup API (never a torn WAL copy),
include the vault and optimizer artifacts, embed a checksum manifest
and self-verify after writing. Restore verifies EVERY member before a
single byte lands and refuses to overwrite existing state without
`--force`. **Stop the service before restoring.** Retention prunes to
`device.backup.retention` archives.

## 6. Release packaging (29.25)

```bash
uv run apex package
```

Produces `dist/apex-<version>.manifest.json` (per-file SHA256, manifest
hash, HMAC signature under the vault signing key) and the
byte-deterministic `dist/apex-<version>.tar.gz`. A release ships only
when the acceptance gates hold (29.26): tests green, no critical
alerts, docs updated, optimizer/research honest.

## 7. Update flow

```bash
git pull
uv sync
uv run pytest -p no:cacheprovider
uv run apex secure-check        # config hash changed? re-seal:
uv run apex secrets seal
```

## 8. Disaster recovery (25.30)

Failure detection (monitor/alerts) -> restore the newest verified
backup -> `apex secure-check` (integrity + chain + seal) -> `apex
monitor` health verification -> resume the service. The event archive
and audit ledger make every step reconstructible.
