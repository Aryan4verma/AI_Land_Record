"""Logging setup. Never log secrets, tokens, passwords, or document content."""
import contextvars
import logging

request_id_ctx = contextvars.ContextVar("request_id", default="-")

_configured = False


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


def setup_logging(level: str = "INFO") -> None:
    global _configured
    if _configured:
        return
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s",
    )
    for handler in logging.root.handlers:
        handler.addFilter(_RequestIdFilter())
    _configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
