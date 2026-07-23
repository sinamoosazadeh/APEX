"""Telegram console credentials (Book IV; env until Phase 13).

The bot token and the chat allowlists come from the environment -
``TELEGRAM_BOT_TOKEN``, ``TELEGRAM_ADMIN_CHAT_IDS`` and
``TELEGRAM_VIEWER_CHAT_IDS`` (comma-separated integers) - exactly the
interim pattern the trading credentials use until the secrets
platform lands. The token never leaves this object: never logged,
never persisted, never surfaced in errors.

Roles implement Book IV Part 1's current-version scheme: two tiers.
``admin`` (Book IV "Administrator") reaches every surface including
the Emergency Center and the Optimization Center; ``viewer`` (Book IV
"Public User") reads status, portfolio, reports and health. The
four-tier schemes of Parts 9/14 belong to the Phase 13 security
platform.
"""

import os
from typing import Final

from apex.core.exceptions import TelegramError

_TOKEN_ENV: Final[str] = "TELEGRAM_BOT_TOKEN"
_ADMINS_ENV: Final[str] = "TELEGRAM_ADMIN_CHAT_IDS"
_VIEWERS_ENV: Final[str] = "TELEGRAM_VIEWER_CHAT_IDS"

ROLE_ADMIN: Final[str] = "admin"
ROLE_VIEWER: Final[str] = "viewer"


def _parse_chat_ids(raw: str, *, variable: str) -> frozenset[int]:
    """Comma-separated chat ids; whitespace tolerated."""
    ids: set[int] = set()
    for piece in raw.split(","):
        text = piece.strip()
        if not text:
            continue
        try:
            ids.add(int(text))
        except ValueError as error:
            raise TelegramError(
                f"{variable} must be comma-separated integers",
                code="TGM-001",
                details={"fragment": text},
            ) from error
    return frozenset(ids)


class TelegramCredentials:
    """Bot token and chat allowlists; the token never leaves."""

    __slots__ = ("_admin_chat_ids", "_token", "_viewer_chat_ids")

    def __init__(
        self,
        *,
        token: str,
        admin_chat_ids: frozenset[int],
        viewer_chat_ids: frozenset[int] = frozenset(),
    ) -> None:
        if not token:
            raise TelegramError("empty Telegram bot token", code="TGM-002")
        if not admin_chat_ids:
            raise TelegramError(
                f"at least one admin chat id is required ({_ADMINS_ENV})",
                code="TGM-003",
            )
        self._token = token
        self._admin_chat_ids = admin_chat_ids
        self._viewer_chat_ids = viewer_chat_ids

    @classmethod
    def from_environment(cls) -> "TelegramCredentials | None":
        """Read env credentials; None when the console is unavailable."""
        token = os.environ.get(_TOKEN_ENV, "")
        if not token:
            return None
        admins = _parse_chat_ids(
            os.environ.get(_ADMINS_ENV, ""), variable=_ADMINS_ENV
        )
        viewers = _parse_chat_ids(
            os.environ.get(_VIEWERS_ENV, ""), variable=_VIEWERS_ENV
        )
        return cls(token=token, admin_chat_ids=admins, viewer_chat_ids=viewers)

    @property
    def token(self) -> str:
        """The bot token (transport use only - never log this)."""
        return self._token

    @property
    def admin_chat_ids(self) -> frozenset[int]:
        """Chats holding the admin role."""
        return self._admin_chat_ids

    def role_for(self, chat_id: int) -> str | None:
        """The chat's role; None when the chat is not allowlisted."""
        if chat_id in self._admin_chat_ids:
            return ROLE_ADMIN
        if chat_id in self._viewer_chat_ids:
            return ROLE_VIEWER
        return None

    def __repr__(self) -> str:
        return "TelegramCredentials(token=***, admin_chat_ids=***)"
