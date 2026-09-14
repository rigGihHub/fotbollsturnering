"""CupNavi API package bootstrap."""

from .schema_repair import ensure_runtime_schema

# The production database has lived through several CupNavi generations. Repair
# only the additive columns the current admin API requires before routes begin
# serving requests. Real schema corruption still raises and stops startup.
ensure_runtime_schema()
