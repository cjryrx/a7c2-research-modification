"""Bind a Sony camera button to a compact function id by writing one AP property.

The package is split so that everything except :mod:`bind_button.session` is
pure Python with no USB dependency:

    properties.py  AP property read/write/save with strict length guards
    buttons.py     slot table, known compact function ids, receipt records
    session.py     USB session (pyusb + vendored PMCA auth), imported lazily
    cli.py         argparse front end
"""

__version__ = "0.1.0"
__all__ = ["__version__"]
