"""Role model and access policy (Book II 25.8/25.9; Book I 13.14).

The seven institutional roles and a deny-by-default action policy
(25.4 Secure By Default): an action absent from the policy is
forbidden for everyone. The defaults are config-overridable per
action through security.yaml's ``policy`` section. The interactive
surfaces map onto these roles - the Telegram admin allowlist acts as
ADMINISTRATOR, its viewer allowlist as READ_ONLY, the local CLI as
OPERATOR, and automatic responses (alert auto-engage, the promotion
guard) as AUTOMATION.
"""

from enum import Enum, unique
from typing import Final

from apex.core.config import ConfigSection
from apex.core.exceptions import ConfigurationError, SecurityError


@unique
class Role(Enum):
    """The institutional role set (Book II 25.9)."""

    ADMINISTRATOR = "administrator"
    RESEARCH = "research"
    OPERATOR = "operator"
    EXECUTION = "execution"
    READ_ONLY = "read_only"
    AUTOMATION = "automation"
    MONITORING = "monitoring"


_ALL_ROLES: Final[frozenset[Role]] = frozenset(Role)
_DEFAULT_POLICY: Final[dict[str, frozenset[Role]]] = {
    "secrets.write": frozenset({Role.ADMINISTRATOR}),
    "secrets.rotate": frozenset({Role.ADMINISTRATOR}),
    "config.seal": frozenset({Role.ADMINISTRATOR}),
    "kill.engage": frozenset({Role.ADMINISTRATOR, Role.OPERATOR, Role.AUTOMATION}),
    "kill.release": frozenset({Role.ADMINISTRATOR, Role.OPERATOR}),
    "promotion.approve": frozenset({Role.ADMINISTRATOR, Role.OPERATOR}),
    "promotion.reject": frozenset({Role.ADMINISTRATOR, Role.OPERATOR}),
    "research.rollback": frozenset({Role.ADMINISTRATOR, Role.OPERATOR}),
    "queue.pause": frozenset({Role.ADMINISTRATOR, Role.OPERATOR}),
    "queue.resume": frozenset({Role.ADMINISTRATOR, Role.OPERATOR}),
    "live.trade": frozenset({Role.ADMINISTRATOR, Role.OPERATOR, Role.EXECUTION}),
    "audit.read": frozenset(
        {Role.ADMINISTRATOR, Role.OPERATOR, Role.RESEARCH, Role.MONITORING,
         Role.READ_ONLY}
    ),
    "status.read": _ALL_ROLES,
}


class AccessPolicy:
    """Deny-by-default action -> roles policy."""

    __slots__ = ("_grants",)

    def __init__(self, grants: dict[str, frozenset[Role]]) -> None:
        self._grants = grants

    @classmethod
    def defaults(cls) -> "AccessPolicy":
        """The built-in institutional policy."""
        return cls(dict(_DEFAULT_POLICY))

    @classmethod
    def from_config(cls, section: ConfigSection) -> "AccessPolicy":
        """Defaults overlaid with per-action overrides from config."""
        grants = dict(_DEFAULT_POLICY)
        values = {role.value: role for role in Role}
        for action, raw in section.items():
            if not isinstance(raw, list):
                raise ConfigurationError(
                    f"security.policy.{action} must be a list of roles",
                    code="CFG-043",
                    details={"found": repr(raw)},
                )
            roles: set[Role] = set()
            for name in raw:
                if not isinstance(name, str) or name not in values:
                    raise ConfigurationError(
                        f"security.policy.{action} carries an unknown role",
                        code="CFG-043",
                        details={"found": repr(name)},
                    )
                roles.add(values[name])
            grants[str(action)] = frozenset(roles)
        return cls(grants)

    def actions(self) -> tuple[str, ...]:
        """Every governed action."""
        return tuple(sorted(self._grants))

    def authorize(self, role: Role, action: str) -> bool:
        """Whether the role may perform the action (deny by default)."""
        return role in self._grants.get(action, frozenset())

    def require(self, role: Role, action: str) -> None:
        """Raise unless authorized (25.8)."""
        if not self.authorize(role, action):
            raise SecurityError(
                "role is not authorized for this action",
                code="SEC-010",
                details={"role": role.value, "action": action},
            )
