"""Telegram credentials: env parsing, roles, masking."""

import pytest
from apex.core.exceptions import TelegramError
from apex.telegram.credentials import ROLE_ADMIN, ROLE_VIEWER, TelegramCredentials


class TestFromEnvironment:
    def test_missing_token_disables_console(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        assert TelegramCredentials.from_environment() is None

    def test_parses_token_and_chat_lists(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
        monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_IDS", "11, 22")
        monkeypatch.setenv("TELEGRAM_VIEWER_CHAT_IDS", "33")
        credentials = TelegramCredentials.from_environment()
        assert credentials is not None
        assert credentials.role_for(11) == ROLE_ADMIN
        assert credentials.role_for(22) == ROLE_ADMIN
        assert credentials.role_for(33) == ROLE_VIEWER
        assert credentials.role_for(44) is None

    def test_bad_chat_id_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
        monkeypatch.setenv("TELEGRAM_ADMIN_CHAT_IDS", "eleven")
        with pytest.raises(TelegramError) as excinfo:
            TelegramCredentials.from_environment()
        assert excinfo.value.code == "TGM-001"


class TestInvariants:
    def test_empty_token_rejected(self) -> None:
        with pytest.raises(TelegramError) as excinfo:
            TelegramCredentials(token="", admin_chat_ids=frozenset({1}))
        assert excinfo.value.code == "TGM-002"

    def test_admins_required(self) -> None:
        with pytest.raises(TelegramError) as excinfo:
            TelegramCredentials(token="123:abc", admin_chat_ids=frozenset())
        assert excinfo.value.code == "TGM-003"

    def test_repr_masks_secrets(self) -> None:
        credentials = TelegramCredentials(
            token="123:secret", admin_chat_ids=frozenset({987654})
        )
        assert "secret" not in repr(credentials)
        assert "987654" not in repr(credentials)
        assert "token=***" in repr(credentials)
