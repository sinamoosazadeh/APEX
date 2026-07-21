# apex.contracts — Engine Contracts

Interfaces for the engine platforms of Phases 3-10, typed against Domain
objects: `IExchange` (anti-corruption boundary, Book II 5.37),
`IFeatureEngine`, `IProbabilityEngine`, `IRiskEngine`, `IExecutionEngine`,
`IOptimizer` (Book II 5.20). Contract-first per Book II 29.6: these exist
before any engine implementation.
