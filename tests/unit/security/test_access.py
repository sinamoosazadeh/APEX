"""Access policy: institutional defaults, overrides, deny by default."""

import pytest
from apex.core.exceptions import ConfigurationError, SecurityError
from apex.security.access import AccessPolicy, Role


class TestAccessPolicy:
    def test_defaults_follow_the_role_model(self) -> None:
        policy = AccessPolicy.defaults()
        assert policy.authorize(Role.ADMINISTRATOR, "secrets.write")
        assert not policy.authorize(Role.READ_ONLY, "secrets.write")
        assert policy.authorize(Role.OPERATOR, "kill.engage")
        assert policy.authorize(Role.AUTOMATION, "kill.engage")
        assert not policy.authorize(Role.AUTOMATION, "kill.release")
        assert policy.authorize(Role.READ_ONLY, "status.read")
        # Deny by default (25.4): unknown actions are forbidden for all.
        assert not policy.authorize(Role.ADMINISTRATOR, "unknown.action")

    def test_config_overrides_replace_per_action(self) -> None:
        policy = AccessPolicy.from_config(
            {"kill.release": ["administrator"], "custom.action": ["research"]}
        )
        assert not policy.authorize(Role.OPERATOR, "kill.release")
        assert policy.authorize(Role.ADMINISTRATOR, "kill.release")
        assert policy.authorize(Role.RESEARCH, "custom.action")
        assert "custom.action" in policy.actions()

    def test_invalid_overrides_are_rejected(self) -> None:
        with pytest.raises(ConfigurationError):
            AccessPolicy.from_config({"kill.release": "administrator"})
        with pytest.raises(ConfigurationError):
            AccessPolicy.from_config({"kill.release": ["emperor"]})

    def test_require_raises_coded(self) -> None:
        policy = AccessPolicy.defaults()
        policy.require(Role.ADMINISTRATOR, "secrets.write")
        with pytest.raises(SecurityError) as caught:
            policy.require(Role.READ_ONLY, "secrets.write")
        assert caught.value.code == "SEC-010"
