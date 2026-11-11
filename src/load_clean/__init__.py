"""Notebook load-clean helpers."""


def load_ipython_extension(ipython):
    """Register the optional IPython extension on demand."""
    from .extension import load_ipython_extension as register

    return register(ipython)


__all__ = ["load_ipython_extension"]
