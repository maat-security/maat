"""Password manager import adapters.

Each importer exposes a single parse(filepath) function that returns
structural account metadata only — never password or secret values.
See _shared.py for the common account dict shape and the reuse/age
helpers every importer builds on.
"""
