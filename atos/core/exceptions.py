"""ATOS custom exception hierarchy."""


class ATOSError(Exception):
    """Base exception for all ATOS errors."""


class ConfigError(ATOSError):
    """Missing or invalid configuration."""


class BrokerError(ATOSError):
    """Dhan API / broker errors."""


class OrderError(BrokerError):
    """Order placement or modification failed."""


class DataError(ATOSError):
    """Data fetch, parse, or storage errors."""


class BhavCopyError(DataError):
    """NSE bhav copy download or parsing failed."""


class AIError(ATOSError):
    """Claude API or response parsing errors."""


class KillswitchActiveError(ATOSError):
    """Raised when an action is blocked by the killswitch."""


class RiskLimitError(ATOSError):
    """Trade rejected due to risk limit breach."""
