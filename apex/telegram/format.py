"""Telegram message builder (Book IV Part 15 design system).

Every outgoing text renders here - no hardcoded strings in handlers.
The binding rules implemented: one concept per line with dot-leader
alignment, the restricted emoji set (decorative emoji are banned),
the fixed page template (title -> context -> summary -> metrics ->
actions), the fixed status vocabulary, formatted numbers, and
two-word button labels.
"""

from typing import Final

from apex.core.serialization import JsonValue
from apex.monitoring.records import KillSwitchLevel, OperationsStatus
from apex.portfolio.store import PositionRecord
from apex.research.store import PromotionRecord, ResearchJob

# The allowed emoji set (Part 15 principle 7).
E_CHART: Final[str] = "\U0001f4ca"      # bar chart
E_UP: Final[str] = "\U0001f4c8"         # upwards trend
E_WARN: Final[str] = "⚠"           # warning
E_ERROR: Final[str] = "❌"          # cross mark
E_OK: Final[str] = "✅"             # check mark
E_MONEY: Final[str] = "\U0001f4b0"      # money bag
E_BRAIN: Final[str] = "\U0001f9e0"      # brain
E_GEAR: Final[str] = "⚙"           # gear
E_FOLDER: Final[str] = "\U0001f4c1"     # folder
E_ANTENNA: Final[str] = "\U0001f4e1"    # antenna
E_HEART: Final[str] = "❤"          # heart
E_GREEN: Final[str] = "\U0001f7e2"      # green circle
E_YELLOW: Final[str] = "\U0001f7e1"     # yellow circle
E_RED: Final[str] = "\U0001f534"        # red circle
E_WHITE: Final[str] = "⚪"          # white circle

_LEADER_WIDTH: Final[int] = 22

_HEALTH_DOT: Final[dict[str, str]] = {
    "healthy": E_GREEN,
    "warning": E_YELLOW,
    "critical": E_RED,
    "offline": E_WHITE,
}

type Keyboard = dict[str, JsonValue]


def leader(label: str, value: str) -> str:
    """One dot-leader metric line (Part 15 principle 4)."""
    dots = max(_LEADER_WIDTH - len(label), 3)
    return f"{label} {'.' * dots} {value}"


def keyboard(rows: list[list[tuple[str, str]]]) -> Keyboard:
    """An inline keyboard from (label, callback_data) rows."""
    return {
        "inline_keyboard": [
            [{"text": label, "callback_data": data} for label, data in row]
            for row in rows
        ]
    }


def _pager_row(prefix: str, page: int, pages: int) -> list[tuple[str, str]]:
    """The Previous | n / m | Next pagination convention."""
    row: list[tuple[str, str]] = []
    if page > 0:
        row.append(("Previous", f"{prefix}.page.{page - 1}"))
    row.append((f"{page + 1} / {max(pages, 1)}", "noop"))
    if page + 1 < pages:
        row.append(("Next", f"{prefix}.page.{page + 1}"))
    return row


# --- Menus ---------------------------------------------------------------------------


def main_menu(role: str) -> tuple[str, Keyboard]:
    """The main menu (admin sees the full surface)."""
    lines = [f"{E_CHART} APEX Console", "", "Select a section."]
    rows: list[list[tuple[str, str]]] = [
        [("Status", "menu.status"), ("Portfolio", "menu.portfolio")],
        [("Positions", "menu.positions"), ("Reports", "menu.reports")],
        [("Health", "menu.health"), ("Help", "menu.help")],
    ]
    if role == "admin":
        lines.insert(1, "\U0001f6e1 ADMIN")
        rows.insert(2, [("Optimization", "menu.optimization"), ("Emergency", "menu.emergency")])
    return "\n".join(lines), keyboard(rows)


def ops_status(status: OperationsStatus) -> tuple[str, Keyboard]:
    """The unified operations center screen (Book II 26.29)."""
    budget = status.error_budget
    lines = [
        f"{E_ANTENNA} Status",
        "",
        leader("Health", _dot(status.overall_health.value)),
        leader("Kill Switch", _switch_label(status.kill_switch)),
        leader("Open Incidents", str(status.incidents_open)),
        leader("Equity", status.equity),
        leader("Drawdown", f"{status.drawdown:.2%}"),
        leader("Open Positions", str(status.open_positions)),
        leader("Closed Trades", str(status.closed_trades)),
        leader("Win Rate", f"{status.win_rate:.2%}"),
        leader("Net R", f"{status.r_sum:.2f}"),
        leader("Jobs Pending", str(status.jobs_pending)),
        leader("Shadow", str(status.promotions_shadow)),
        leader("Await Approval", str(status.promotions_pending_approval)),
        leader("Error Rate", f"{budget.error_rate:.2%} / {budget.budget:.2%}"),
        leader("Budget", "EXHAUSTED" if budget.exhausted else "OK"),
    ]
    if status.alerts_recent:
        lines.extend(["", "Recent alerts:"])
        lines.extend(
            f"{E_WARN} [{alert.severity.value}] {alert.message} (x{alert.count})"
            for alert in status.alerts_recent[:3]
        )
    rows = [
        [("Refresh", "menu.status"), ("Health", "menu.health")],
        [("Back", "menu.main")],
    ]
    return "\n".join(lines), keyboard(rows)


def portfolio_view(status: OperationsStatus) -> tuple[str, Keyboard]:
    """The portfolio dashboard headline figures."""
    lines = [
        f"{E_MONEY} Portfolio",
        "",
        leader("Equity", status.equity),
        leader("Cash", status.cash),
        leader("Drawdown", f"{status.drawdown:.2%}"),
        leader("Open Positions", str(status.open_positions)),
        leader("Closed Trades", str(status.closed_trades)),
        leader("Win Rate", f"{status.win_rate:.2%}"),
        leader("Net R", f"{status.r_sum:.2f}"),
    ]
    rows = [
        [("Positions", "menu.positions"), ("Reports", "menu.reports")],
        [("Back", "menu.main")],
    ]
    return "\n".join(lines), keyboard(rows)


def positions_page(
    records: list[PositionRecord], *, page: int, page_size: int
) -> tuple[str, Keyboard]:
    """One page of open positions."""
    pages = max((len(records) + page_size - 1) // page_size, 1)
    page = min(max(page, 0), pages - 1)
    window = records[page * page_size : (page + 1) * page_size]
    lines = [f"{E_UP} Open Positions ({len(records)})", ""]
    if not window:
        lines.append("No open positions.")
    for record in window:
        lines.extend(
            [
                f"{record.symbol} {record.timeframe.value} {record.direction.upper()}",
                leader("  Entry", str(record.entry)),
                leader("  Stop", str(record.stop)),
                leader("  Target", str(record.target)),
                leader("  Quantity", str(record.quantity)),
                "",
            ]
        )
    rows = [_pager_row("positions", page, pages), [("Back", "menu.main")]]
    return "\n".join(lines).rstrip(), keyboard(rows)


def optimization_home(
    status: OperationsStatus, *, queue_paused: bool
) -> tuple[str, Keyboard]:
    """The Optimization Center (Book V part 7 Telegram menu)."""
    lines = [
        f"{E_BRAIN} Optimization",
        "",
        leader("Queue", "PAUSED" if queue_paused else "RUNNING"),
        leader("Jobs Pending", str(status.jobs_pending)),
        leader("Jobs Running", str(status.jobs_running)),
        leader("Shadow", str(status.promotions_shadow)),
        leader("Await Approval", str(status.promotions_pending_approval)),
    ]
    pause_label = ("Resume Queue", "optimization.resume") if queue_paused else (
        "Pause Queue", "optimization.pause"
    )
    rows = [
        [("Show Queue", "optimization.queue"), ("Promotions", "optimization.promotions")],
        [pause_label, ("Rollback", "optimization.rollback")],
        [("Back", "menu.main")],
    ]
    return "\n".join(lines), keyboard(rows)


def queue_page(
    jobs: list[ResearchJob], *, page: int, page_size: int
) -> tuple[str, Keyboard]:
    """One page of the optimization queue."""
    pages = max((len(jobs) + page_size - 1) // page_size, 1)
    page = min(max(page, 0), pages - 1)
    window = jobs[page * page_size : (page + 1) * page_size]
    lines = [f"{E_FOLDER} Queue ({len(jobs)})", ""]
    if not window:
        lines.append("Queue is empty.")
    lines.extend(
        f"#{job.job_id} {job.symbol} {job.timeframe.value} {job.kind} "
        f"[{_status_word(job.status)}] attempts {job.attempts}"
        for job in window
    )
    rows = [_pager_row("queue", page, pages), [("Back", "menu.optimization")]]
    return "\n".join(lines), keyboard(rows)


def promotions_page(
    records: list[PromotionRecord], *, page: int, page_size: int, admin: bool
) -> tuple[str, Keyboard]:
    """One page of the promotion pipeline with approval actions."""
    pages = max((len(records) + page_size - 1) // page_size, 1)
    page = min(max(page, 0), pages - 1)
    window = records[page * page_size : (page + 1) * page_size]
    lines = [f"{E_BRAIN} Promotions ({len(records)})", ""]
    if not window:
        lines.append("No promotions registered.")
    rows: list[list[tuple[str, str]]] = []
    for record in window:
        lines.append(
            f"#{record.promotion_id} {record.symbol} {record.timeframe.value} "
            f"{record.kind} [{_status_word(record.status)}]"
        )
        if admin and record.status == "passed":
            rows.append(
                [
                    ("Approve", f"promotion.approve.{record.promotion_id}"),
                    ("Reject", f"promotion.reject.{record.promotion_id}"),
                ]
            )
    rows.append(_pager_row("promotions", page, pages))
    rows.append([("Back", "menu.optimization")])
    return "\n".join(lines), keyboard(rows)


def rollback_menu(series: list[tuple[str, str]]) -> tuple[str, Keyboard]:
    """Pick a series to roll back to its previous artifact."""
    lines = [f"{E_GEAR} Rollback", "", "Select a series."]
    rows = [
        [(f"{symbol} {timeframe}", f"rollback.{symbol}.{timeframe}")]
        for symbol, timeframe in series
    ]
    rows.append([("Back", "menu.optimization")])
    return "\n".join(lines), keyboard(rows)


def emergency_view(level: KillSwitchLevel, reason: str) -> tuple[str, Keyboard]:
    """The Emergency Center (Book IV 7.9)."""
    lines = [
        f"{E_WARN} Emergency",
        "",
        leader("Kill Switch", _switch_label(level)),
    ]
    if reason:
        lines.append(leader("Reason", reason))
    rows = [
        [("Pause Trading", "emergency.pause"), ("Resume Trading", "emergency.resume")],
        [("Disable Entries", "emergency.disable_entries")],
        [("Safe Mode", "emergency.safe_mode"), ("Cancel Orders", "emergency.cancel_orders")],
        [("Back", "menu.main")],
    ]
    return "\n".join(lines), keyboard(rows)


def confirm_view(action_label: str, nonce: str) -> tuple[str, Keyboard]:
    """The two-step confirmation gate (Book IV principle 3)."""
    lines = [
        f"{E_WARN} Warning",
        f"This will execute: {action_label}.",
        "Please confirm.",
    ]
    rows = [[("Confirm", f"confirm.{nonce}"), ("Cancel", f"cancel.{nonce}")]]
    return "\n".join(lines), keyboard(rows)


def reports_view(status: OperationsStatus) -> tuple[str, Keyboard]:
    """The performance report headline (closed-trade statistics)."""
    lines = [
        f"{E_FOLDER} Performance",
        "",
        leader("Closed Trades", str(status.closed_trades)),
        leader("Win Rate", f"{status.win_rate:.2%}"),
        leader("Net R", f"{status.r_sum:.2f}"),
        leader("Equity", status.equity),
        leader("Drawdown", f"{status.drawdown:.2%}"),
        leader("Snapshots", str(status.snapshots_stored)),
    ]
    rows = [[("Back", "menu.main")]]
    return "\n".join(lines), keyboard(rows)


def health_view(status: OperationsStatus) -> tuple[str, Keyboard]:
    """Per-module health and heartbeat freshness."""
    lines = [f"{E_HEART} Health", ""]
    lines.extend(
        f"{_dot(component.state.value)} {component.component}"
        for component in status.components
    )
    if status.heartbeats:
        lines.extend(["", "Heartbeats:"])
        lines.extend(
            leader(beat.component, f"{beat.age_ms // 1000}s"
                   + (" STALE" if beat.stale else ""))
            for beat in status.heartbeats
        )
    rows = [[("Refresh", "menu.health")], [("Back", "menu.main")]]
    return "\n".join(lines), keyboard(rows)


def help_view(role: str) -> tuple[str, Keyboard]:
    """Command reference."""
    lines = [
        f"{E_CHART} Help",
        "",
        "/menu - main menu",
        "/status - operations status",
        "/portfolio - portfolio dashboard",
        "/reports - performance report",
        "/health - module health",
    ]
    if role == "admin":
        lines.extend(
            [
                "/optimizer - optimization center",
                "/emergency - emergency center",
            ]
        )
    rows = [[("Back", "menu.main")]]
    return "\n".join(lines), keyboard(rows)


def denied_view() -> str:
    """The unauthorized reply."""
    return f"{E_ERROR} Error\nReason: not authorized\nSuggested Action: contact the operator"


def done_view(message: str) -> str:
    """The standard success format."""
    return f"{E_OK} Completed\n{message}"


def failed_view(reason: str, suggestion: str) -> str:
    """The standard error format."""
    return (
        f"{E_ERROR} Error\nReason: {reason}\n"
        f"Suggested Action: {suggestion}"
    )


# --- Notifications --------------------------------------------------------------------


def alert_notification(payload: dict[str, JsonValue]) -> str:
    """Push text for one monitoring alert."""
    severity = str(payload.get("severity", ""))
    message = str(payload.get("message", ""))
    return f"{E_WARN} Alert [{severity}]\n{message}"


def kill_switch_notification(payload: dict[str, JsonValue]) -> str:
    """Push text for one kill-switch transition."""
    level = str(payload.get("level", ""))
    reason = str(payload.get("reason", ""))
    actor = str(payload.get("actor", ""))
    return f"{E_WARN} Kill Switch\n{leader('Level', level)}\n" + "\n".join(
        [leader("Reason", reason), leader("Actor", actor)]
    )


def fill_notification(payload: dict[str, JsonValue]) -> str:
    """Push text for one execution outcome."""
    status = str(payload.get("status", ""))
    symbol = str(payload.get("symbol", ""))
    mode = str(payload.get("mode", ""))
    price = payload.get("fill_price")
    body = [
        f"{E_OK} Execution {_status_word(status)}",
        leader("Symbol", symbol),
        leader("Mode", mode),
    ]
    if price is not None:
        body.append(leader("Fill", str(price)))
    return "\n".join(body)


def signal_notification(payload: dict[str, JsonValue]) -> str:
    """Push text for one fired signal."""
    symbol = str(payload.get("symbol", ""))
    timeframe = str(payload.get("timeframe", ""))
    direction = str(payload.get("direction", ""))
    probability = payload.get("probability")
    body = [
        f"{E_UP} Signal",
        leader("Symbol", symbol),
        leader("Timeframe", timeframe),
        leader("Direction", direction.upper()),
    ]
    if isinstance(probability, (int, float)):
        body.append(leader("Probability", f"{float(probability):.2%}"))
    return "\n".join(body)


def promotion_notification(payload: dict[str, JsonValue]) -> str:
    """Push text for one promotion pipeline transition."""
    symbol = str(payload.get("symbol", ""))
    timeframe = str(payload.get("timeframe", ""))
    status = str(payload.get("status", payload.get("kind", "")))
    return "\n".join(
        [
            f"{E_BRAIN} Promotion",
            leader("Series", f"{symbol} {timeframe}"),
            leader("Status", _status_word(status)),
        ]
    )


# --- Vocabulary -----------------------------------------------------------------------


def _dot(health: str) -> str:
    return f"{_HEALTH_DOT.get(health, E_WHITE)} {health.upper()}"


def _switch_label(level: KillSwitchLevel) -> str:
    if level is KillSwitchLevel.NONE:
        return f"{E_GREEN} OFF"
    return f"{E_RED} {level.value.upper()}"


_STATUS_WORDS: Final[dict[str, str]] = {
    "pending": "Pending",
    "waiting": "Waiting",
    "running": "Running",
    "completed": "Completed",
    "failed": "Failed",
    "canceled": "Canceled",
    "shadow": "Running",
    "passed": "Waiting",
    "promoted": "Completed",
    "rejected": "Canceled",
    "rolled_back": "Canceled",
    "filled": "Completed",
    "unfilled": "Pending",
}


def _status_word(status: str) -> str:
    """The fixed status vocabulary (synonyms are banned)."""
    return _STATUS_WORDS.get(status, status.capitalize() if status else "-")
