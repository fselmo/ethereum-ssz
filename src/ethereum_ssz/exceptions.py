"""SSZ encoding and decoding exceptions."""


class EncodingError(Exception):
    """Raised when encoding fails."""

    pass


class DecodingError(Exception):
    """Raised when decoding fails."""

    pass
