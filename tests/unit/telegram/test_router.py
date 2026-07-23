"""Router: permissions, confirmation state machine, session timeout."""

from apex.core.time.clock import ManualClock
from apex.telegram.router import (
    DECISION_CANCELLED,
    DECISION_CONFIRM,
    DECISION_DENIED,
    DECISION_EXECUTE,
    DECISION_IGNORED,
    CallbackRouter,
    SessionManager,
)

from tests.conftest import T0


def manager(clock: ManualClock) -> SessionManager:
    return SessionManager(clock=clock, timeout_ms=600_000)


def router(clock: ManualClock) -> CallbackRouter:
    return CallbackRouter(clock=clock, confirm_ttl_ms=60_000)


class TestPermissions:
    def test_viewer_reaches_read_surfaces_only(self) -> None:
        assert CallbackRouter.permitted("viewer", "menu.status")
        assert CallbackRouter.permitted("viewer", "positions.page.2")
        assert not CallbackRouter.permitted("viewer", "menu.optimization")
        assert not CallbackRouter.permitted("viewer", "emergency.pause")
        assert not CallbackRouter.permitted("viewer", "promotion.approve.1")

    def test_admin_reaches_everything(self) -> None:
        assert CallbackRouter.permitted("admin", "emergency.safe_mode")
        assert CallbackRouter.permitted("admin", "rollback.BTCUSDT.1h")

    def test_denied_decision_for_viewer_on_admin_action(self) -> None:
        clock = ManualClock(T0)
        session = manager(clock).session(1, "viewer")
        decision = router(clock).route(session, "emergency.pause")
        assert decision.kind == DECISION_DENIED


class TestConfirmation:
    def test_dangerous_action_arms_nonce_then_executes(self) -> None:
        clock = ManualClock(T0)
        session = manager(clock).session(1, "admin")
        routes = router(clock)
        armed = routes.route(session, "emergency.pause")
        assert armed.kind == DECISION_CONFIRM
        assert armed.nonce
        confirmed = routes.route(session, f"confirm.{armed.nonce}")
        assert confirmed.kind == DECISION_EXECUTE
        assert confirmed.action == "emergency.pause"
        # The nonce is single-use.
        replay = routes.route(session, f"confirm.{armed.nonce}")
        assert replay.kind == DECISION_IGNORED

    def test_wrong_nonce_is_ignored(self) -> None:
        clock = ManualClock(T0)
        session = manager(clock).session(1, "admin")
        routes = router(clock)
        routes.route(session, "emergency.safe_mode")
        decision = routes.route(session, "confirm.deadbeef")
        assert decision.kind == DECISION_IGNORED
        # The pending action was cleared defensively.
        assert session.pending_action is None

    def test_expired_nonce_is_ignored(self) -> None:
        clock = ManualClock(T0)
        session = manager(clock).session(1, "admin")
        routes = router(clock)
        armed = routes.route(session, "promotion.approve.3")
        clock.advance_ms(120_000)  # beyond the 60s TTL
        decision = routes.route(session, f"confirm.{armed.nonce}")
        assert decision.kind == DECISION_IGNORED

    def test_cancel_clears_pending(self) -> None:
        clock = ManualClock(T0)
        session = manager(clock).session(1, "admin")
        routes = router(clock)
        armed = routes.route(session, "emergency.cancel_orders")
        decision = routes.route(session, f"cancel.{armed.nonce}")
        assert decision.kind == DECISION_CANCELLED
        assert session.pending_action is None

    def test_read_only_actions_execute_directly(self) -> None:
        clock = ManualClock(T0)
        session = manager(clock).session(1, "admin")
        decision = router(clock).route(session, "menu.status")
        assert decision.kind == DECISION_EXECUTE
        assert decision.action == "menu.status"


class TestSessions:
    def test_session_survives_within_timeout(self) -> None:
        clock = ManualClock(T0)
        sessions = manager(clock)
        first = sessions.session(1, "admin")
        first.pending_action = "emergency.pause"
        clock.advance_ms(1_000)
        again = sessions.session(1, "admin")
        assert again is first
        assert again.pending_action == "emergency.pause"

    def test_session_resets_after_timeout(self) -> None:
        clock = ManualClock(T0)
        sessions = manager(clock)
        first = sessions.session(1, "admin")
        first.pending_action = "emergency.pause"
        clock.advance_ms(700_000)  # beyond the 10-minute timeout
        fresh = sessions.session(1, "admin")
        assert fresh is not first
        assert fresh.pending_action is None
