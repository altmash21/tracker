class OCRException(Exception):
    """Raised when OCR extraction fails."""


class AmountNotFoundException(Exception):
    """Raised when no bill amount can be extracted."""


class AICategoriaztionException(Exception):
    """Raised when AI categorization fails."""


# Backwards-compatible alias with the correct spelling.
AICategorizationException = AICategoriaztionException