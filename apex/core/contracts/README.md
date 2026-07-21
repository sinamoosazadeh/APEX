# apex.core.contracts — Infrastructure Interfaces

Contracts that depend only on Core concepts: `IClock`, `ILogger`,
`IEventBus`, `IStorage`, `IRepository[T]`, `IHealthCheck`, `IModule`.
Engine contracts typed against Domain live in `apex/contracts`.

All interfaces are `typing.Protocol` types carrying a declared stability
level (Book II 5.36).
