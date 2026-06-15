import pytest

from se_agent.tools.base import ToolError, apply_defaults, validate


def _schema():
    return {
        "type": "object",
        "properties": {
            "operation": {"type": "string", "enum": ["a", "b"]},
            "top": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
        },
        "required": ["operation"],
        "additionalProperties": False,
    }


def test_defaults_applied():
    args = apply_defaults(_schema(), {"operation": "a"})
    assert args["top"] == 10


def test_valid_args_pass():
    validate(_schema(), {"operation": "a", "top": 5})


def test_missing_required_rejected():
    with pytest.raises(ToolError) as exc:
        validate(_schema(), {"top": 5})
    assert exc.value.code == "validation"


def test_enum_violation_rejected():
    with pytest.raises(ToolError):
        validate(_schema(), {"operation": "z"})


def test_additional_property_rejected():
    with pytest.raises(ToolError):
        validate(_schema(), {"operation": "a", "extra": 1})


def test_out_of_range_rejected():
    with pytest.raises(ToolError):
        validate(_schema(), {"operation": "a", "top": 999})


def test_bool_not_accepted_as_integer():
    with pytest.raises(ToolError):
        validate(_schema(), {"operation": "a", "top": True})
