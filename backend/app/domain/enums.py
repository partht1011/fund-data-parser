from enum import StrEnum


class ParserSource(StrEnum):
    LOCAL = "local"
    REMOTE = "remote"


class ValidationStatus(StrEnum):
    PASS = "pass"
    REVIEW = "review"


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class JobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"
