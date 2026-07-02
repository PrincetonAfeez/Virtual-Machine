"""Canonical value formatting for PVM output."""


def format_value(value: object) -> str:
    """Render a VM value for display.

    Booleans use the lowercase spelling from the assembly language; integers
    render as decimal strings. Only ``int`` and ``bool`` are valid VM values.
    """
    if type(value) is bool:
        return "true" if value else "false"
    if type(value) is int:
        return str(value)
    raise TypeError(f"cannot format {type(value).__name__} for display")
