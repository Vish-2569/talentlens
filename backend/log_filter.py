"""Logging filter — redacts GEMINI_API_KEY from all log records."""
from __future__ import annotations

import logging


class GeminiKeyFilter(logging.Filter):
    """Replaces the raw API key with REDACTED in every log message and args."""
    _key: str = ""

    @classmethod
    def configure(cls, key: str) -> None:
        cls._key = key

    def filter(self, record: logging.LogRecord) -> bool:
        if not self._key:
            return True
        record.msg = str(record.msg).replace(self._key, "REDACTED")
        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(
                    str(a).replace(self._key, "REDACTED") if isinstance(a, str) else a
                    for a in record.args
                )
            elif isinstance(record.args, dict):
                record.args = {
                    k: str(v).replace(self._key, "REDACTED") if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
        return True


_filter = GeminiKeyFilter()


def install(key: str) -> None:
    """Install the redaction filter on the root logger and all its current handlers."""
    GeminiKeyFilter.configure(key)
    root = logging.getLogger()
    if _filter not in root.filters:
        root.addFilter(_filter)
    for hdlr in root.handlers:
        if _filter not in hdlr.filters:
            hdlr.addFilter(_filter)
