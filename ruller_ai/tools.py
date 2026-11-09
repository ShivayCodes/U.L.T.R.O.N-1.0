"""Small registry for deterministic, permission-checked built-in tools."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Callable


logger = logging.getLogger("ruller_ai.tools")


class Permission(str, Enum):
    """Execution policy assigned to a tool."""

    SAFE = "SAFE"  # Read-only deterministic operation; may run automatically.
    LIMITED = "LIMITED"  # Requires explicit user confirmation.
    CONFIRM = "CONFIRM"  # Side effects require explicit confirmation per invocation.
    BLOCKED = "BLOCKED"  # Never executable.


class ToolError(ValueError):
    """Raised when a tool request is invalid or not permitted."""


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    permission: Permission
    input_schema: str
    side_effects: str
    handler: Callable[[str], str]


class ToolRegistry:
    """Allowlisted built-ins with permission checks and argument-free audit logs."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, tool: ToolSpec) -> None:
        key = tool.name.casefold()
        if not re.fullmatch(r"[a-z][a-z0-9_]*", key):
            raise ValueError("Tool names must contain only lowercase letters, digits, and underscores.")
        if key in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[key] = tool

    def list_tools(self) -> tuple[ToolSpec, ...]:
        return tuple(self._tools.values())

    def run(self, name: str, argument: str = "", *, confirmed: bool = False) -> str:
        """Run one registered tool after checking its permission classification."""
        tool = self._tools.get(name.casefold())
        if tool is None:
            logger.info("tool_execution name=%s permission=UNKNOWN outcome=denied", name[:64])
            raise ToolError(f"Unknown tool: {name}")
        if len(argument) > 300:
            logger.info("tool_execution name=%s permission=%s outcome=denied", tool.name, tool.permission.value)
            raise ToolError("Tool input must be 300 characters or fewer.")
        if tool.permission is Permission.BLOCKED:
            logger.info("tool_execution name=%s permission=%s outcome=denied", tool.name, tool.permission.value)
            raise ToolError("This tool is blocked by policy.")
        if tool.permission in {Permission.LIMITED, Permission.CONFIRM} and not confirmed:
            logger.info("tool_execution name=%s permission=%s outcome=confirmation_required", tool.name, tool.permission.value)
            raise ToolError("This tool requires explicit user confirmation.")

        try:
            result = tool.handler(argument)
        except ToolError:
            logger.info("tool_execution name=%s permission=%s outcome=invalid_input", tool.name, tool.permission.value)
            raise
        except Exception:
            # Do not log arguments or exception text; they may contain user data.
            logger.exception("tool_execution name=%s permission=%s outcome=error", tool.name, tool.permission.value)
            raise
        logger.info("tool_execution name=%s permission=%s outcome=success", tool.name, tool.permission.value)
        return result


def _local_time(argument: str) -> str:
    if argument.strip():
        raise ToolError("Usage: /time")
    return datetime.now().astimezone().strftime("Your local system time is %Y-%m-%d %H:%M:%S %Z.")


def _date(argument: str) -> str:
    value = argument.strip().casefold()
    today = date.today()
    if value in {"", "today"}:
        result = today
    elif value == "tomorrow":
        result = today + timedelta(days=1)
    elif value == "yesterday":
        result = today - timedelta(days=1)
    else:
        match = re.fullmatch(r"(?:in\s+)?(\d{1,6})\s+(day|days|week|weeks)(?:\s+from\s+now)?", value)
        ago = re.fullmatch(r"(\d{1,6})\s+(day|days|week|weeks)\s+ago", value)
        if not match and not ago:
            raise ToolError("Usage: /date [today|tomorrow|yesterday|in N days|N weeks ago]")
        parsed = match or ago
        assert parsed is not None
        amount = int(parsed.group(1))
        if parsed.group(2).startswith("week"):
            amount *= 7
        if amount > 365_000:
            raise ToolError("Date offset is too large (maximum 365000 days).")
        result = today + timedelta(days=-amount if ago else amount)
    return f"{result.isoformat()} ({result.strftime('%A')})"


_UNIT_ALIASES = {
    "mm": ("length", Decimal("0.001")), "millimeter": ("length", Decimal("0.001")), "millimeters": ("length", Decimal("0.001")),
    "cm": ("length", Decimal("0.01")), "centimeter": ("length", Decimal("0.01")), "centimeters": ("length", Decimal("0.01")),
    "m": ("length", Decimal("1")), "meter": ("length", Decimal("1")), "meters": ("length", Decimal("1")),
    "km": ("length", Decimal("1000")), "kilometer": ("length", Decimal("1000")), "kilometers": ("length", Decimal("1000")),
    "in": ("length", Decimal("0.0254")), "inch": ("length", Decimal("0.0254")), "inches": ("length", Decimal("0.0254")),
    "ft": ("length", Decimal("0.3048")), "foot": ("length", Decimal("0.3048")), "feet": ("length", Decimal("0.3048")),
    "mi": ("length", Decimal("1609.344")), "mile": ("length", Decimal("1609.344")), "miles": ("length", Decimal("1609.344")),
    "mg": ("mass", Decimal("0.001")), "milligram": ("mass", Decimal("0.001")), "milligrams": ("mass", Decimal("0.001")),
    "g": ("mass", Decimal("1")), "gram": ("mass", Decimal("1")), "grams": ("mass", Decimal("1")),
    "kg": ("mass", Decimal("1000")), "kilogram": ("mass", Decimal("1000")), "kilograms": ("mass", Decimal("1000")),
    "oz": ("mass", Decimal("28.349523125")), "ounce": ("mass", Decimal("28.349523125")), "ounces": ("mass", Decimal("28.349523125")),
    "lb": ("mass", Decimal("453.59237")), "lbs": ("mass", Decimal("453.59237")), "pound": ("mass", Decimal("453.59237")), "pounds": ("mass", Decimal("453.59237")),
    "ms": ("time", Decimal("0.001")), "millisecond": ("time", Decimal("0.001")), "milliseconds": ("time", Decimal("0.001")),
    "s": ("time", Decimal("1")), "sec": ("time", Decimal("1")), "second": ("time", Decimal("1")), "seconds": ("time", Decimal("1")),
    "min": ("time", Decimal("60")), "minute": ("time", Decimal("60")), "minutes": ("time", Decimal("60")),
    "h": ("time", Decimal("3600")), "hr": ("time", Decimal("3600")), "hour": ("time", Decimal("3600")), "hours": ("time", Decimal("3600")),
    "d": ("time", Decimal("86400")), "day": ("time", Decimal("86400")), "days": ("time", Decimal("86400")),
}
_TEMPERATURES = {"c": "c", "°c": "c", "celsius": "c", "f": "f", "°f": "f", "fahrenheit": "f", "k": "k", "kelvin": "k"}
_NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
_CONVERT_RE = re.compile(rf"^\s*({_NUMBER})\s+([a-zA-Z°]+)\s+(?:to|in)\s+([a-zA-Z°]+)\s*$", re.IGNORECASE)


def _format_decimal(value: Decimal) -> str:
    # Decimal's fixed-precision formatting rounds repeating conversions. Keep
    # the first 18 fractional digits instead, matching the documented output
    # precision consistently across Python versions.
    rendered = format(value, "f")
    if "." in rendered:
        whole, fraction = rendered.split(".", 1)
        rendered = whole + ("." + fraction[:18].rstrip("0") if fraction[:18].rstrip("0") else "")
    return rendered or "0"


def _convert(argument: str) -> str:
    match = _CONVERT_RE.fullmatch(argument)
    if not match:
        raise ToolError("Usage: /convert AMOUNT UNIT to UNIT (for example: /convert 10 km to miles)")
    raw_amount, source_raw, target_raw = match.groups()
    try:
        amount = Decimal(raw_amount)
    except InvalidOperation as exc:
        raise ToolError("Enter a valid numeric amount.") from exc
    if not amount.is_finite() or abs(amount) > Decimal("1e100"):
        raise ToolError("Amount must be finite and no larger than 1e100 in magnitude.")

    source, target = source_raw.casefold(), target_raw.casefold()
    if source in _TEMPERATURES and target in _TEMPERATURES:
        source_kind, target_kind = _TEMPERATURES[source], _TEMPERATURES[target]
        if source_kind == "c":
            celsius = amount
        elif source_kind == "f":
            celsius = (amount - Decimal(32)) * Decimal(5) / Decimal(9)
        else:
            celsius = amount - Decimal("273.15")
        if target_kind == "c":
            converted = celsius
        elif target_kind == "f":
            converted = celsius * Decimal(9) / Decimal(5) + Decimal(32)
        else:
            converted = celsius + Decimal("273.15")
    else:
        source_unit, target_unit = _UNIT_ALIASES.get(source), _UNIT_ALIASES.get(target)
        if not source_unit or not target_unit:
            raise ToolError("Unsupported unit. Supported groups: length, mass, time, and temperature.")
        if source_unit[0] != target_unit[0]:
            raise ToolError("Units must belong to the same category.")
        converted = amount * source_unit[1] / target_unit[1]

    return f"{_format_decimal(amount)} {source_raw} = {_format_decimal(converted)} {target_raw}"


def create_builtin_registry() -> ToolRegistry:
    """Create the fixed, deterministic, read-only built-in tool set."""
    registry = ToolRegistry()
    registry.register(ToolSpec("time", "Show the local system time.", Permission.SAFE, "No arguments", "Reads local clock; no data changes.", _local_time))
    registry.register(ToolSpec("date", "Show today's date or a relative date.", Permission.SAFE, "today|tomorrow|yesterday|N days/weeks", "Reads local clock; no data changes.", _date))
    registry.register(ToolSpec("convert", "Convert common length, mass, time, and temperature units.", Permission.SAFE, "AMOUNT UNIT to UNIT", "Deterministic calculation; no data changes.", _convert))
    return registry
