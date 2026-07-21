"""System-wide constants.

Constitution 3.7: business thresholds, weights and coefficients must come
from configuration, never from code. The constants below are *structural*
invariants of the platform itself (identifier formats, unit scales,
protocol limits), not tunable business parameters.
"""

import re
from typing import Final

# --- Project identity -------------------------------------------------------

PROJECT_NAME: Final[str] = "APEX"
PROJECT_FULL_NAME: Final[str] = "Autonomous Probabilistic Execution eXchange"

# --- Time scale (Book II 4.16: all timestamps are UTC) -----------------------

MILLISECONDS_PER_SECOND: Final[int] = 1_000
MICROSECONDS_PER_MILLISECOND: Final[int] = 1_000
NANOSECONDS_PER_MILLISECOND: Final[int] = 1_000_000
SECONDS_PER_MINUTE: Final[int] = 60
MINUTES_PER_HOUR: Final[int] = 60
HOURS_PER_DAY: Final[int] = 24
MILLISECONDS_PER_MINUTE: Final[int] = MILLISECONDS_PER_SECOND * SECONDS_PER_MINUTE
MILLISECONDS_PER_HOUR: Final[int] = MILLISECONDS_PER_MINUTE * MINUTES_PER_HOUR
MILLISECONDS_PER_DAY: Final[int] = MILLISECONDS_PER_HOUR * HOURS_PER_DAY

# --- Identifier formats (Book II 4.26: coded errors like "SIG-001") ----------

ERROR_CODE_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[A-Z]{3}-\d{3}$")
EVENT_TYPE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){1,4}$"
)
SYMBOL_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[A-Z0-9]{1,20}(-[A-Z0-9]{1,10})?$")

# --- Contract / schema versioning --------------------------------------------

CONTRACT_SCHEMA_VERSION: Final[int] = 1
CONFIG_SCHEMA_VERSION: Final[int] = 1

# --- Numerical guards (Constitution 3.26: numerical stability policy) --------

FLOAT_COMPARISON_TOLERANCE: Final[float] = 1e-12
MAX_DECIMAL_PLACES: Final[int] = 18

# --- Environment variable conventions ----------------------------------------

ENV_PREFIX: Final[str] = "APEX"
ENV_SEPARATOR: Final[str] = "__"
