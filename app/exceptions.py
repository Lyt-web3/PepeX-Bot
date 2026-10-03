class PepexError(Exception):
    """Base error for the application."""


class WalletValidationError(PepexError):
    pass


class WalletNotAssociatedError(PepexError):
    pass


class MarketValidationError(PepexError):
    pass


class HyperliquidAPIError(PepexError):
    pass
