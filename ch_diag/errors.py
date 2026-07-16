"""Domain exceptions used by the autonomous ch_diag runtime."""


class ChDiagError(Exception):
    """Base error suitable for concise CLI reporting."""


class ContentIntegrityError(ChDiagError):
    """Protected content differs from the packaged vendor baseline."""


class ContentValidationError(ChDiagError):
    """Content pack is structurally invalid or unsafe."""


class ClickHouseConnectionError(ChDiagError):
    """ClickHouse connection or safety verification failed."""


class UnsupportedClickHouseVersion(ChDiagError):
    """No supported runtime contract exists for the connected server."""
