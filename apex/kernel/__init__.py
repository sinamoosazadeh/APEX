"""APEX Kernel - the platform's internal operating system (Book II 3.5).

Owns startup and shutdown (Book II 29.21/29.22), dependency injection,
module lifecycle and health aggregation. Contains no trading logic.
"""

from apex.kernel.container import ServiceContainer
from apex.kernel.health import HealthMonitor, HealthReport
from apex.kernel.kernel import Kernel, KernelStatus
from apex.kernel.modules import ModuleRegistry

__all__ = [
    "HealthMonitor",
    "HealthReport",
    "Kernel",
    "KernelStatus",
    "ModuleRegistry",
    "ServiceContainer",
]
