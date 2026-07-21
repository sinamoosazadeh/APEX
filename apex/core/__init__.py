"""APEX Core Layer - infrastructure primitives only.

The Core layer contains no trading logic, no indicators, no probability
models and no optimizers (Book II, section 4.2). It provides the
foundation every other layer is built on:

- primitive value types (:mod:`apex.core.types`)
- enums (:mod:`apex.core.enums`)
- exception hierarchy with error codes (:mod:`apex.core.exceptions`)
- identity system (:mod:`apex.core.identity`)
- time system (:mod:`apex.core.time`)
- object metadata (:mod:`apex.core.metadata`)
- validation framework (:mod:`apex.core.validation`)
- canonical serialization and hashing (:mod:`apex.core.serialization`)
- result objects (:mod:`apex.core.result`)
- base object model (:mod:`apex.core.base`)
- context objects (:mod:`apex.core.context`)
- structured logging (:mod:`apex.core.logging`)
- configuration loading and schema validation (:mod:`apex.core.config`)
- infrastructure contracts (:mod:`apex.core.contracts`)
- event platform (:mod:`apex.core.events`)

Nothing in this package may import from any other APEX layer.
"""
