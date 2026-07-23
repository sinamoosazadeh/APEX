"""Telegram console service (Book IV; Book V part 7 Telegram menu).

The control layer, exactly and only that (the Golden Rule at Book IV
line 1224): no trading logic, no decisions, no risk math - every
button forwards to the owning platform service and renders its
answer. Inbound: long-polled commands and callbacks routed through
permission -> state -> callback -> application. Outbound: proactive
notifications driven by bus events (alerts by severity, executions,
fired signals, promotion transitions, kill-switch changes) - the
engines are never polled (Book IV line 985).

A console failure never stops trading: the service runs beside the
operational loop and its errors stay inside this layer.
"""

import asyncio
from dataclasses import dataclass
from typing import Final

from apex.core.contracts.interfaces import IEventBus
from apex.core.enums import Timeframe
from apex.core.events.event import Event
from apex.core.exceptions import ApexError, TelegramError
from apex.core.logging import StructuredLogger
from apex.core.serialization import JsonValue
from apex.core.time.clock import Clock
from apex.decision.events import DecisionEvent
from apex.execution.events import ExecutionEvent
from apex.monitoring.events import MonitoringEvent
from apex.monitoring.records import AlertSeverity, KillSwitchLevel
from apex.monitoring.service import MonitoringService
from apex.portfolio.store import SqlitePortfolioRepository
from apex.research.events import ResearchEvent
from apex.research.service import KIND_SIGNAL, ResearchService
from apex.telegram import format as views
from apex.telegram.client import TelegramBotClient
from apex.telegram.config import TelegramSettings
from apex.telegram.credentials import TelegramCredentials
from apex.telegram.router import (
    DECISION_CANCELLED,
    DECISION_CONFIRM,
    DECISION_DENIED,
    DECISION_EXECUTE,
    CallbackRouter,
    Session,
    SessionManager,
)

_SOURCE: Final[str] = "apex.telegram.service"
_MAX_POLL_FAILURES: Final[int] = 5

_COMMANDS: Final[dict[str, str]] = {
    "/start": "menu.main",
    "/menu": "menu.main",
    "/status": "menu.status",
    "/portfolio": "menu.portfolio",
    "/reports": "menu.reports",
    "/health": "menu.health",
    "/help": "menu.help",
    "/optimizer": "menu.optimization",
    "/emergency": "menu.emergency",
}

_ACTION_LABELS: Final[dict[str, str]] = {
    "emergency.pause": "Pause Trading",
    "emergency.resume": "Resume Trading",
    "emergency.disable_entries": "Disable New Entries",
    "emergency.safe_mode": "Safe Mode",
    "emergency.cancel_orders": "Cancel All Orders",
}


@dataclass(frozen=True, slots=True, kw_only=True)
class ConsoleStats:
    """Outcome of one console session."""

    updates: int
    commands: int
    callbacks: int
    notifications: int
    denied: int


@dataclass(slots=True)
class _ConsoleState:
    """Mutable counters for one console session."""

    updates: int = 0
    commands: int = 0
    callbacks: int = 0
    notifications: int = 0
    denied: int = 0
    offset: int = 0
    poll_failures: int = 0


class TelegramConsoleService:
    """Long-polls the Bot API and renders the console surfaces."""

    def __init__(
        self,
        *,
        settings: TelegramSettings,
        credentials: TelegramCredentials | None,
        client: TelegramBotClient | None,
        monitoring: MonitoringService,
        research: ResearchService,
        portfolio_repository: SqlitePortfolioRepository,
        portfolio_id: str,
        series: tuple[tuple[str, Timeframe], ...],
        bus: IEventBus,
        clock: Clock,
        logger: StructuredLogger,
    ) -> None:
        self._settings = settings
        self._credentials = credentials
        self._client = client
        self._monitoring = monitoring
        self._research = research
        self._portfolio = portfolio_repository
        self._portfolio_id = portfolio_id
        self._series = series
        self._bus = bus
        self._clock = clock
        self._logger = logger
        self._sessions = SessionManager(
            clock=clock, timeout_ms=settings.session_timeout_ms
        )
        self._router = CallbackRouter(
            clock=clock, confirm_ttl_ms=settings.confirm_ttl_ms
        )
        self._stop = asyncio.Event()
        self._state = _ConsoleState()
        self._active = False
        self._subscribed = False

    @property
    def available(self) -> bool:
        """Whether the console can run (enabled + credentials)."""
        return (
            self._settings.enabled
            and self._credentials is not None
            and self._client is not None
        )

    def request_stop(self) -> None:
        """Ask the console to finish after the current poll."""
        self._stop.set()

    # --- Session ---------------------------------------------------------------------

    async def run(self, *, seconds: int) -> ConsoleStats:
        """Long-poll until stop or deadline; 0 runs indefinitely."""
        if not self.available:
            raise TelegramError(
                "telegram console unavailable: set TELEGRAM_BOT_TOKEN and "
                "TELEGRAM_ADMIN_CHAT_IDS and enable telegram.console",
                code="TGM-004",
            )
        client = self._require_client()
        self._state = _ConsoleState()
        self._stop.clear()
        self._subscribe_once()
        await client.open()
        self._active = True
        try:
            me = await client.get_me()
            self._logger.info(
                "telegram_console_started",
                bot=str(me.get("username", "?")),
            )
            await self._poll_until_done(seconds)
        finally:
            self._active = False
            await client.close()
        return ConsoleStats(
            updates=self._state.updates,
            commands=self._state.commands,
            callbacks=self._state.callbacks,
            notifications=self._state.notifications,
            denied=self._state.denied,
        )

    async def _poll_until_done(self, seconds: int) -> None:
        client = self._require_client()
        deadline_ms = (
            self._clock.now().epoch_ms + seconds * 1_000 if seconds > 0 else None
        )
        while not self._stop.is_set():
            if deadline_ms is not None and self._clock.now().epoch_ms >= deadline_ms:
                break
            try:
                updates = await client.get_updates(offset=self._state.offset)
            except TelegramError as error:
                self._state.poll_failures += 1
                self._logger.failure("telegram_poll_failed", error)
                if self._state.poll_failures >= _MAX_POLL_FAILURES:
                    raise
                await asyncio.sleep(1.0)
                continue
            self._state.poll_failures = 0
            for update in updates:
                update_id = update.get("update_id")
                if isinstance(update_id, int):
                    self._state.offset = max(self._state.offset, update_id + 1)
                await self._handle_update(update)

    def _require_client(self) -> TelegramBotClient:
        if self._client is None:
            raise TelegramError("telegram client is not configured", code="TGM-005")
        return self._client

    def _require_credentials(self) -> TelegramCredentials:
        if self._credentials is None:
            raise TelegramError(
                "telegram credentials are not configured", code="TGM-006"
            )
        return self._credentials

    # --- Update handling --------------------------------------------------------------

    async def _handle_update(self, update: dict[str, JsonValue]) -> None:
        self._state.updates += 1
        message = update.get("message")
        callback = update.get("callback_query")
        if isinstance(message, dict):
            await self._handle_message(message)
        elif isinstance(callback, dict):
            await self._handle_callback(callback)

    async def _handle_message(self, message: dict[str, JsonValue]) -> None:
        chat = message.get("chat")
        chat_id = chat.get("id") if isinstance(chat, dict) else None
        text = message.get("text")
        if not isinstance(chat_id, int) or not isinstance(text, str):
            return
        role = self._require_credentials().role_for(chat_id)
        command = text.split()[0].split("@")[0] if text.split() else ""
        if role is None:
            self._state.denied += 1
            self._logger.warning("telegram_denied", chat_id=chat_id, command=command)
            await self._require_client().send_message(chat_id, views.denied_view())
            return
        action = _COMMANDS.get(command)
        self._state.commands += 1
        self._logger.info(
            "telegram_command", chat_id=chat_id, command=command, role=role
        )
        session = self._sessions.session(chat_id, role)
        if action is None or not self._router.permitted(role, action):
            action = "menu.help"
        text_out, keyboard = await self._screen(action, session)
        await self._require_client().send_message(
            chat_id, text_out, keyboard=keyboard
        )

    async def _handle_callback(self, callback: dict[str, JsonValue]) -> None:
        query_id = str(callback.get("id", ""))
        data = callback.get("data")
        message = callback.get("message")
        chat_id, message_id = self._callback_anchor(message)
        client = self._require_client()
        if not isinstance(data, str) or chat_id is None or message_id is None:
            await client.answer_callback(query_id)
            return
        role = self._require_credentials().role_for(chat_id)
        if role is None:
            self._state.denied += 1
            await client.answer_callback(query_id, text="Not authorized")
            return
        self._state.callbacks += 1
        session = self._sessions.session(chat_id, role)
        self._logger.info(
            "telegram_callback", chat_id=chat_id, action=data, role=role
        )
        await client.answer_callback(query_id)
        if data == "noop":
            return
        await self._route_callback(session, data, chat_id, message_id)

    @staticmethod
    def _callback_anchor(
        message: JsonValue | None,
    ) -> tuple[int | None, int | None]:
        if not isinstance(message, dict):
            return None, None
        chat = message.get("chat")
        chat_id = chat.get("id") if isinstance(chat, dict) else None
        message_id = message.get("message_id")
        return (
            chat_id if isinstance(chat_id, int) else None,
            message_id if isinstance(message_id, int) else None,
        )

    async def _route_callback(
        self, session: Session, data: str, chat_id: int, message_id: int
    ) -> None:
        client = self._require_client()
        decision = self._router.route(session, data)
        if decision.kind == DECISION_DENIED:
            self._state.denied += 1
            self._logger.warning("telegram_denied", chat_id=chat_id, action=data)
            await client.edit_message(chat_id, message_id, views.denied_view())
            return
        if decision.kind == DECISION_CONFIRM:
            label = _ACTION_LABELS.get(
                decision.action, decision.action.replace(".", " ")
            )
            text, keyboard = views.confirm_view(label, decision.nonce)
            await client.edit_message(chat_id, message_id, text, keyboard=keyboard)
            return
        if decision.kind == DECISION_CANCELLED:
            text, keyboard = views.main_menu(session.role)
            await client.edit_message(chat_id, message_id, text, keyboard=keyboard)
            return
        if decision.kind != DECISION_EXECUTE:
            return
        if self._router.dangerous(decision.action):
            text, keyboard = await self._execute_dangerous(decision.action, session)
        else:
            text, keyboard = await self._screen(decision.action, session)
        await client.edit_message(chat_id, message_id, text, keyboard=keyboard)

    # --- Screens ---------------------------------------------------------------------

    async def _screen(
        self, action: str, session: Session
    ) -> tuple[str, views.Keyboard]:
        """Render one read-only surface."""
        if action == "menu.help":
            return views.help_view(session.role)
        if action in ("menu.status", "menu.portfolio", "menu.reports", "menu.health"):
            return await self._ops_screen(action)
        if action == "menu.positions" or action.startswith("positions.page."):
            return await self._positions_screen(action)
        if action.startswith(("menu.optimization", "optimization.", "queue.page.",
                              "promotions.page.")):
            return await self._optimization_screen(action, session)
        if action == "menu.emergency":
            return await self._emergency_screen()
        return views.main_menu(session.role)

    async def _ops_screen(self, action: str) -> tuple[str, views.Keyboard]:
        """The surfaces rendered off the unified operations feed."""
        ops = await self._monitoring.ops_status()
        if action == "menu.status":
            return views.ops_status(ops)
        if action == "menu.portfolio":
            return views.portfolio_view(ops)
        if action == "menu.reports":
            return views.reports_view(ops)
        return views.health_view(ops)

    async def _optimization_screen(
        self, action: str, session: Session
    ) -> tuple[str, views.Keyboard]:
        """The Optimization Center surfaces (Book V part 7 menu)."""
        if action == "optimization.queue" or action.startswith("queue.page."):
            return await self._queue_screen(action)
        if action == "optimization.promotions" or action.startswith(
            "promotions.page."
        ):
            return await self._promotions_screen(action, session)
        if action == "optimization.rollback":
            return views.rollback_menu(
                [(symbol, timeframe.value) for symbol, timeframe in self._series]
            )
        if action == "optimization.pause":
            await self._research.pause_queue()
        elif action == "optimization.resume":
            await self._research.resume_queue()
        return views.optimization_home(
            await self._monitoring.ops_status(),
            queue_paused=await self._research.queue_paused(),
        )

    async def _positions_screen(self, action: str) -> tuple[str, views.Keyboard]:
        page = _page_of(action)
        records = await self._portfolio.get_positions(
            self._portfolio_id, status="open"
        )
        return views.positions_page(
            records, page=page, page_size=self._settings.page_size
        )

    async def _queue_screen(self, action: str) -> tuple[str, views.Keyboard]:
        page = _page_of(action)
        jobs = [
            job
            for job in await self._research.jobs()
            if job.status in ("pending", "running")
        ]
        return views.queue_page(jobs, page=page, page_size=self._settings.page_size)

    async def _promotions_screen(
        self, action: str, session: Session
    ) -> tuple[str, views.Keyboard]:
        page = _page_of(action)
        records = await self._research.promotions()
        return views.promotions_page(
            records,
            page=page,
            page_size=self._settings.page_size,
            admin=session.role == "admin",
        )

    async def _emergency_screen(self) -> tuple[str, views.Keyboard]:
        record = await self._monitoring.kill_switch.current()
        level = record.level if record else KillSwitchLevel.NONE
        reason = record.reason if record else ""
        return views.emergency_view(level, reason)

    # --- Dangerous actions --------------------------------------------------------------

    async def _execute_dangerous(
        self, action: str, session: Session
    ) -> tuple[str, views.Keyboard]:
        """Application stage for confirmed dangerous actions."""
        actor = f"telegram:{session.chat_id}"
        back = views.keyboard([[("Back", "menu.main")]])
        try:
            message = await self._apply_dangerous(action, actor)
        except ApexError as error:
            self._logger.failure("telegram_action_failed", error, action=action)
            return views.failed_view(error.code, "check platform logs"), back
        return views.done_view(message), back

    async def _apply_dangerous(self, action: str, actor: str) -> str:
        switch = self._monitoring.kill_switch
        if action == "emergency.pause":
            await switch.engage(
                KillSwitchLevel.PAUSED, reason="operator pause", actor=actor
            )
            return "trading paused"
        if action == "emergency.resume":
            await switch.release(reason="operator resume", actor=actor)
            return "trading resumed"
        if action == "emergency.disable_entries":
            await switch.engage(
                KillSwitchLevel.ENTRIES_DISABLED,
                reason="operator entries off",
                actor=actor,
            )
            return "new entries disabled"
        if action == "emergency.safe_mode":
            await switch.engage(
                KillSwitchLevel.SAFE_MODE, reason="operator safe mode", actor=actor
            )
            return "safe mode engaged"
        if action == "emergency.cancel_orders":
            canceled = await switch.cancel_resting_orders()
            return f"{canceled} resting orders canceled"
        if action.startswith("promotion.approve."):
            return await self._approve_promotion(action, actor)
        if action.startswith("promotion.reject."):
            promotion_id = int(action.rsplit(".", 1)[1])
            outcome = await self._research.reject_promotion(promotion_id, actor=actor)
            return f"promotion {promotion_id} rejected: {outcome.unwrap()}"
        if action.startswith("rollback."):
            _, symbol, timeframe_raw = action.split(".", 2)
            restored = await self._research.rollback(
                symbol, Timeframe(timeframe_raw), KIND_SIGNAL
            )
            if restored is None:
                raise TelegramError(
                    "no previous version to roll back to", code="TGM-020"
                )
            return f"rolled back to {restored}"
        raise TelegramError(
            "unknown dangerous action", code="TGM-021", details={"action": action}
        )

    async def _approve_promotion(self, action: str, actor: str) -> str:
        """Approval consults the error budget first (Book II 26.28)."""
        if not await self._monitoring.slo.promotion_permitted():
            raise TelegramError(
                "error budget exhausted: optimizer deploys are blocked",
                code="TGM-022",
            )
        promotion_id = int(action.rsplit(".", 1)[1])
        outcome = await self._research.promote(promotion_id, actor=actor)
        return f"promotion {promotion_id} activated: {outcome.unwrap()}"

    # --- Notifications ------------------------------------------------------------------

    def _subscribe_once(self) -> None:
        if self._subscribed:
            return
        for event_type in self._notification_topics():
            self._bus.subscribe(event_type, self._on_event)
        self._subscribed = True

    @staticmethod
    def _notification_topics() -> tuple[str, ...]:
        return (
            MonitoringEvent.ALERT_RAISED.value,
            MonitoringEvent.KILL_SWITCH_CHANGED.value,
            ExecutionEvent.FILLED.value,
            ExecutionEvent.REJECTED.value,
            DecisionEvent.SIGNAL_FIRED.value,
            ResearchEvent.PROMOTION_EVALUATED.value,
            ResearchEvent.PROMOTED.value,
            ResearchEvent.PROMOTION_REJECTED.value,
            ResearchEvent.ROLLED_BACK.value,
        )

    async def _on_event(self, event: Event) -> None:
        """Bus handler: push one notification to the admin chats."""
        if not self._active:
            return
        text = self._notification_text(event)
        if text is None:
            return
        client = self._require_client()
        for chat_id in sorted(self._require_credentials().admin_chat_ids):
            try:
                await client.send_message(chat_id, text)
                self._state.notifications += 1
            except TelegramError as error:
                self._logger.failure("telegram_notify_failed", error)

    def _notification_text(self, event: Event) -> str | None:
        payload = dict(event.payload)
        if event.event_type == MonitoringEvent.ALERT_RAISED.value:
            severity = AlertSeverity(str(payload.get("severity", "information")))
            if severity.rank < self._settings.notify_min_severity.rank:
                return None
            return views.alert_notification(payload)
        if event.event_type == MonitoringEvent.KILL_SWITCH_CHANGED.value:
            return views.kill_switch_notification(payload)
        if event.event_type in (
            ExecutionEvent.FILLED.value,
            ExecutionEvent.REJECTED.value,
        ):
            return views.fill_notification(payload) if self._settings.notify_fills else None
        if event.event_type == DecisionEvent.SIGNAL_FIRED.value:
            return (
                views.signal_notification(payload)
                if self._settings.notify_signals
                else None
            )
        return (
            views.promotion_notification(payload)
            if self._settings.notify_promotions
            else None
        )


def _page_of(action: str) -> int:
    """The page index encoded in a ``*.page.N`` callback."""
    if ".page." not in action:
        return 0
    tail = action.rsplit(".", 1)[1]
    return int(tail) if tail.isdigit() else 0
