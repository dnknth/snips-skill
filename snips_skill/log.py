import logging
from collections.abc import Callable

from colors import cyan, green, magenta, red, yellow

from .intent import IntentPayload

__all__ = ("LoggingMixin",)


class LoggingMixin:
    "Logging for Snips events"

    INDENT = 10
    log: logging.Logger

    def coloured_log(
        self, level: int, format: str, *args, color: Callable | None = None
    ) -> None:
        if color and self.tty_log:
            args = map(color, args)
        self.log.log(level, format, *args)

    def tabular_log(
        self,
        level: int,
        key: str,
        value,
        color: Callable | None = None,
        width: int = INDENT,
    ):
        label = f"{key:<{width}}"
        self.coloured_log(level, "%s %s", label, str(value), color=color)

    def log_intent(self, payload: IntentPayload, level: int = logging.DEBUG) -> None:
        "Log an intent message"
        self.tabular_log(
            level,
            "intent",
            f"{red(payload.intent.intent_name, style='bold')}, confidence: {payload.intent.confidence_score:.1f}",
            color=green,
        )
        for k in ("site_id", "input"):
            self.tabular_log(level, k, getattr(payload, k), color=cyan)
        for name, slot in payload.slot_values.items():
            self.tabular_log(level, name, slot.value, color=magenta)
        if payload.custom_data:
            self.tabular_log(level, "data", payload.custom_data, color=yellow)

    def log_response(self, response: str, level: int = logging.DEBUG) -> None:
        "Log an action response"
        if response:
            self.tabular_log(level, "answer", red(response, style="bold"), color=green)
