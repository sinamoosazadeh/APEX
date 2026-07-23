"""Message builder: dot leaders, pagination, vocabulary, keyboards."""

from apex.core.enums import HealthState, Timeframe
from apex.core.time.timestamp import Timestamp
from apex.monitoring.records import (
    AlertRecord,
    AlertSeverity,
    KillSwitchLevel,
    OperationsStatus,
    SloStatus,
)
from apex.research.store import PromotionRecord, ResearchJob
from apex.telegram import format as views

from tests.conftest import T0


def ops(**overrides: object) -> OperationsStatus:
    base: dict[str, object] = {
        "as_of": T0,
        "overall_health": HealthState.HEALTHY,
        "components": (),
        "heartbeats": (),
        "kill_switch": KillSwitchLevel.NONE,
        "kill_switch_reason": "",
        "alerts_recent": (),
        "incidents_open": 0,
        "error_budget": SloStatus(
            name="platform",
            window_ms=1_000,
            operations=10,
            errors=0,
            error_rate=0.0,
            budget=0.05,
            exhausted=False,
        ),
        "equity": "10000",
        "cash": "10000",
        "drawdown": 0.01,
        "open_positions": 1,
        "closed_trades": 4,
        "win_rate": 0.5,
        "r_sum": 1.5,
        "jobs_pending": 2,
        "jobs_running": 0,
        "promotions_shadow": 1,
        "promotions_pending_approval": 1,
        "snapshots_stored": 3,
    }
    base.update(overrides)
    return OperationsStatus(**base)  # type: ignore[arg-type]


def _buttons(keyboard: views.Keyboard) -> list[dict[str, str]]:
    """Flatten an inline keyboard into its button dicts (typed)."""
    rows = keyboard["inline_keyboard"]
    assert isinstance(rows, list)
    buttons: list[dict[str, str]] = []
    for row in rows:
        assert isinstance(row, list)
        for button in row:
            assert isinstance(button, dict)
            buttons.append({str(k): str(v) for k, v in button.items()})
    return buttons


def _callbacks(keyboard: views.Keyboard) -> set[str]:
    return {button["callback_data"] for button in _buttons(keyboard)}


def _labels(keyboard: views.Keyboard) -> set[str]:
    return {button["text"] for button in _buttons(keyboard)}


class TestLeaders:
    def test_dot_leader_alignment(self) -> None:
        line = views.leader("Equity", "10000")
        assert line.startswith("Equity ")
        assert "..." in line
        assert line.endswith(" 10000")

    def test_keyboard_shape(self) -> None:
        built = views.keyboard([[("Back", "menu.main")]])
        assert built == {
            "inline_keyboard": [[{"text": "Back", "callback_data": "menu.main"}]]
        }


class TestScreens:
    def test_status_screen_carries_headline_figures(self) -> None:
        alert = AlertRecord(
            alert_id=1,
            severity=AlertSeverity.HIGH,
            category="portfolio",
            message="drawdown",
            dedup_key="k",
            count=3,
            first_at=T0,
            last_at=T0,
            incident_id=None,
        )
        text, keyboard = views.ops_status(ops(alerts_recent=(alert,)))
        assert "Status" in text
        assert "10000" in text
        assert "(x3)" in text  # dedup count surfaces
        assert _buttons(keyboard)

    def test_main_menu_gates_admin_rows(self) -> None:
        admin_text, admin_kb = views.main_menu("admin")
        viewer_text, viewer_kb = views.main_menu("viewer")
        assert "ADMIN" in admin_text
        assert "ADMIN" not in viewer_text
        admin_labels = _labels(admin_kb)
        viewer_labels = _labels(viewer_kb)
        assert "Emergency" in admin_labels
        assert "Emergency" not in viewer_labels

    def test_queue_page_uses_fixed_vocabulary(self) -> None:
        job = ResearchJob(
            job_id=1,
            symbol="BTCUSDT",
            timeframe=Timeframe.H1,
            kind="signal",
            priority=0,
            status="pending",
            attempts=0,
            seed=7,
            window_bars=480,
            created_at=T0,
            completed_at=None,
            result=None,
        )
        text, _ = views.queue_page([job], page=0, page_size=5)
        assert "[Pending]" in text

    def test_promotions_page_approve_buttons_admin_and_passed_only(self) -> None:
        passed = _promotion(1, "passed")
        shadow = _promotion(2, "shadow")
        text, admin_kb = views.promotions_page(
            [passed, shadow], page=0, page_size=5, admin=True
        )
        assert "#1" in text and "#2" in text
        callbacks = _callbacks(admin_kb)
        assert "promotion.approve.1" in callbacks
        assert "promotion.approve.2" not in callbacks
        _, viewer_kb = views.promotions_page(
            [passed], page=0, page_size=5, admin=False
        )
        viewer_callbacks = _callbacks(viewer_kb)
        assert "promotion.approve.1" not in viewer_callbacks

    def test_pagination_row(self) -> None:
        records = [_promotion(index, "shadow") for index in range(7)]
        _, keyboard = views.promotions_page(
            records, page=0, page_size=5, admin=False
        )
        callbacks = _callbacks(keyboard)
        assert "promotions.page.1" in callbacks

    def test_emergency_and_confirm_views(self) -> None:
        text, emergency_kb = views.emergency_view(KillSwitchLevel.SAFE_MODE, "operator")
        assert "SAFE_MODE" in text
        assert "emergency.safe_mode" in _callbacks(emergency_kb)
        confirm_text, confirm_kb = views.confirm_view("Pause Trading", "abc123")
        assert "Please confirm." in confirm_text
        assert _callbacks(confirm_kb) == {"confirm.abc123", "cancel.abc123"}


def _promotion(promotion_id: int, status: str) -> PromotionRecord:
    return PromotionRecord(
        promotion_id=promotion_id,
        symbol="BTCUSDT",
        timeframe=Timeframe.H1,
        kind="signal",
        artifact_path="/tmp/a.json",
        baseline_artifact=None,
        status=status,
        registered_at=Timestamp(epoch_ms=T0.epoch_ms),
        evaluated_at=None,
        decided_at=None,
        decided_by=None,
        report=None,
    )
