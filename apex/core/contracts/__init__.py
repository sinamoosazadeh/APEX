"""Infrastructure contracts (interfaces only, no implementations).

Book II 29.6: interfaces are written before implementations. This
package holds the contracts that depend only on Core concepts. Engine
contracts that require Domain objects live in :mod:`apex.contracts`
to preserve the downward-only dependency rule (Book II 3.25).
"""

from apex.core.contracts.interfaces import (
    IClock,
    IEventBus,
    IHealthCheck,
    ILogger,
    IModule,
    IRepository,
    IStorage,
)

__all__ = [
    "IClock",
    "IEventBus",
    "IHealthCheck",
    "ILogger",
    "IModule",
    "IRepository",
    "IStorage",
]
