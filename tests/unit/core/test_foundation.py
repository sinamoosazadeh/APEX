"""Exceptions, results, validation, serialization, versioning, identity."""

import pytest
from apex.core.enums import StabilityLevel
from apex.core.exceptions import (
    ApexError,
    ConfigurationError,
    SerializationError,
    SignalError,
    ValidationError,
)
from apex.core.identity import IdProvider
from apex.core.result import Result
from apex.core.serialization import canonical_json, content_hash, to_canonical
from apex.core.time.timestamp import Timestamp
from apex.core.types import Probability
from apex.core.validation import ensure_in_range, ensure_symbol, safe_divide
from apex.core.versioning import SemanticVersion, stability, stability_of


class TestExceptions:
    def test_error_carries_code_and_details(self) -> None:
        error = SignalError("probability invalid", code="SIG-001", details={"value": 1.2})
        assert error.code == "SIG-001"
        assert error.to_dict()["details"] == {"value": 1.2}
        assert str(error) == "[SIG-001] probability invalid"

    def test_default_codes(self) -> None:
        assert ConfigurationError("x").code == "CFG-000"

    def test_malformed_code_rejected(self) -> None:
        with pytest.raises(ValueError, match="invalid error code"):
            ApexError("x", code="BAD_CODE")

    def test_hierarchy(self) -> None:
        assert issubclass(SignalError, ApexError)


class TestResult:
    def test_success(self) -> None:
        result = Result.success(42, duration_ms=1.5)
        assert result.ok and result.unwrap() == 42

    def test_failure_raises_on_unwrap(self) -> None:
        result: Result[int] = Result.failure(SignalError("no", code="SIG-002"))
        assert not result.ok
        with pytest.raises(SignalError):
            result.unwrap()

    def test_invariants_enforced(self) -> None:
        with pytest.raises(ValidationError):
            Result(ok=True, error=SignalError("x"))
        with pytest.raises(ValidationError):
            Result[int](ok=False)


class TestValidation:
    def test_range(self) -> None:
        ensure_in_range(0.5, 0.0, 1.0, "p")
        with pytest.raises(ValidationError):
            ensure_in_range(1.5, 0.0, 1.0, "p")

    def test_symbol_format(self) -> None:
        ensure_symbol("BTCUSDT")
        ensure_symbol("BTC-PERP")
        with pytest.raises(ValidationError):
            ensure_symbol("btcusdt")

    def test_safe_divide(self) -> None:
        assert safe_divide(10.0, 4.0, "ratio") == 2.5
        with pytest.raises(ValidationError):
            safe_divide(1.0, 0.0, "ratio")


class TestSerialization:
    def test_canonical_is_deterministic(self) -> None:
        left = canonical_json({"b": 2, "a": [1, 2], "t": Timestamp(epoch_ms=5)})
        right = canonical_json({"t": Timestamp(epoch_ms=5), "a": [1, 2], "b": 2})
        assert left == right

    def test_wrapper_types_serialize(self) -> None:
        assert to_canonical(Probability(0.5)) == {"value": 0.5}

    def test_nan_rejected(self) -> None:
        with pytest.raises(SerializationError):
            canonical_json({"x": float("nan")})

    def test_unsupported_type_rejected(self) -> None:
        with pytest.raises(SerializationError):
            canonical_json({"x": object()})

    def test_content_hash_stability(self) -> None:
        assert content_hash({"a": 1}) == content_hash({"a": 1})
        assert content_hash({"a": 1}) != content_hash({"a": 2})


class TestVersioning:
    def test_parse_and_compat(self) -> None:
        v1 = SemanticVersion.parse("1.4.2")
        assert str(v1) == "1.4.2"
        assert v1.is_compatible_with(SemanticVersion(1, 0, 0))
        assert not v1.is_compatible_with(SemanticVersion(2, 0, 0))

    def test_parse_rejects_garbage(self) -> None:
        with pytest.raises(ValidationError):
            SemanticVersion.parse("1.2")

    def test_stability_decorator(self) -> None:
        @stability(StabilityLevel.BETA)
        class Sample:
            pass

        assert stability_of(Sample) is StabilityLevel.BETA

    def test_default_stability_is_experimental(self) -> None:
        class Unmarked:
            pass

        assert stability_of(Unmarked) is StabilityLevel.EXPERIMENTAL


class TestIdentity:
    def test_deterministic_provider_reproduces_sequence(self) -> None:
        first = [IdProvider(seed=7).new_id() for _ in range(3)]
        second = [IdProvider(seed=7).new_id() for _ in range(3)]
        assert first == second

    def test_entropy_provider_differs(self) -> None:
        provider = IdProvider()
        assert provider.new_id() != provider.new_id()
        assert not provider.is_deterministic

    def test_derived_ids_are_stable(self) -> None:
        provider = IdProvider()
        assert provider.derive_id("feature:ict.fvg") == provider.derive_id("feature:ict.fvg")
