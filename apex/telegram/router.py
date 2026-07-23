"""Callback routing, sessions and the confirmation gate (Book IV).

Validation order per Part 12: Permission -> State -> Callback ->
Application. Callback data uses the dotted ``module.action.target``
convention (Part 2) - free-form callback strings do not exist. Every
user holds an independent session (10-minute timeout, Part 5);
dangerous actions arm a nonce-guarded pending confirmation that a
second click must match within its TTL (principle 3: no dangerous
action without confirmation). Unknown callbacks are logged and
ignored - never a crash, never a silent acceptance.
"""

import uuid
from dataclasses import dataclass, field
from typing import Final

from apex.core.time.clock import Clock
from apex.telegram.credentials import ROLE_ADMIN

# Actions a viewer may reach; everything else requires admin.
_VIEWER_PREFIXES: Final[tuple[str, ...]] = (
    "menu.main",
    "menu.status",
    "menu.portfolio",
    "menu.positions",
    "menu.reports",
    "menu.health",
    "menu.help",
    "positions.page.",
    "noop",
)

# Actions that require the two-step confirmation gate.
_DANGEROUS_PREFIXES: Final[tuple[str, ...]] = (
    "emergency.pause",
    "emergency.resume",
    "emergency.disable_entries",
    "emergency.safe_mode",
    "emergency.cancel_orders",
    "promotion.approve.",
    "promotion.reject.",
    "rollback.",
)

DECISION_DENIED: Final[str] = "denied"
DECISION_CONFIRM: Final[str] = "confirm"
DECISION_EXECUTE: Final[str] = "execute"
DECISION_CANCELLED: Final[str] = "cancelled"
DECISION_IGNORED: Final[str] = "ignored"


@dataclass(slots=True)
class Session:
    """One chat's console state."""

    chat_id: int
    role: str
    updated_ms: int
    pending_action: str | None = None
    pending_nonce: str | None = None
    pending_expires_ms: int = 0
    navigation: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True, kw_only=True)
class RouteDecision:
    """The router's verdict for one callback."""

    kind: str
    action: str = ""
    nonce: str = ""


class SessionManager:
    """Per-chat sessions with the configured inactivity timeout."""

    def __init__(self, *, clock: Clock, timeout_ms: int) -> None:
        self._clock = clock
        self._timeout_ms = timeout_ms
        self._sessions: dict[int, Session] = {}

    def session(self, chat_id: int, role: str) -> Session:
        """The chat's session; expired sessions reset cleanly."""
        now_ms = self._clock.now().epoch_ms
        existing = self._sessions.get(chat_id)
        if existing is not None and now_ms - existing.updated_ms <= self._timeout_ms:
            existing.updated_ms = now_ms
            existing.role = role
            return existing
        fresh = Session(chat_id=chat_id, role=role, updated_ms=now_ms)
        self._sessions[chat_id] = fresh
        return fresh


class CallbackRouter:
    """Permission checks and the confirmation state machine."""

    def __init__(self, *, clock: Clock, confirm_ttl_ms: int) -> None:
        self._clock = clock
        self._confirm_ttl_ms = confirm_ttl_ms

    @staticmethod
    def permitted(role: str, action: str) -> bool:
        """Whether the role may invoke the action (Permission stage)."""
        if role == ROLE_ADMIN:
            return True
        return any(action.startswith(prefix) for prefix in _VIEWER_PREFIXES)

    @staticmethod
    def dangerous(action: str) -> bool:
        """Whether the action requires double confirmation."""
        return any(action.startswith(prefix) for prefix in _DANGEROUS_PREFIXES)

    def route(self, session: Session, action: str) -> RouteDecision:
        """Validate one callback: permission, state, then dispatch."""
        if not self.permitted(session.role, action):
            return RouteDecision(kind=DECISION_DENIED)
        now_ms = self._clock.now().epoch_ms
        if action.startswith("confirm."):
            return self._resolve_confirmation(session, action, now_ms)
        if action.startswith("cancel."):
            session.pending_action = None
            session.pending_nonce = None
            return RouteDecision(kind=DECISION_CANCELLED)
        if self.dangerous(action):
            nonce = uuid.uuid4().hex[:12]
            session.pending_action = action
            session.pending_nonce = nonce
            session.pending_expires_ms = now_ms + self._confirm_ttl_ms
            return RouteDecision(kind=DECISION_CONFIRM, action=action, nonce=nonce)
        return RouteDecision(kind=DECISION_EXECUTE, action=action)

    def _resolve_confirmation(
        self, session: Session, action: str, now_ms: int
    ) -> RouteDecision:
        """The State stage: the nonce must match and be fresh."""
        nonce = action.removeprefix("confirm.")
        if (
            session.pending_action is None
            or session.pending_nonce != nonce
            or now_ms > session.pending_expires_ms
        ):
            session.pending_action = None
            session.pending_nonce = None
            return RouteDecision(kind=DECISION_IGNORED)
        confirmed = session.pending_action
        session.pending_action = None
        session.pending_nonce = None
        return RouteDecision(kind=DECISION_EXECUTE, action=confirmed)
