"""Engine contracts (Book II 29.6: interfaces before implementations).

These interfaces are typed against Domain objects, so they live above
Domain and below the engines that implement them - preserving the
downward-only dependency rule (Book II 3.25):

    engines -> contracts -> domain -> core

Every engine built in Phases 3-10 implements one of these contracts;
no engine may be reached except through them (Book II 5.38).
"""

from apex.contracts.engines import (
    IExchange,
    IExecutionEngine,
    IFeatureEngine,
    IMarketDataGateway,
    IOptimizer,
    IProbabilityEngine,
    IRiskEngine,
)

__all__ = [
    "IExchange",
    "IExecutionEngine",
    "IFeatureEngine",
    "IMarketDataGateway",
    "IOptimizer",
    "IProbabilityEngine",
    "IRiskEngine",
]
