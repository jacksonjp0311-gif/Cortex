"""Binary-intel packs — portable domain intelligence as a Cortex memory branch."""

from .format import PACK_SCHEMA, GLYPH, build_binary_field, score_task_against_domains
from .memory import (
    domain_route,
    index_packs_into_repo,
    pack_surface_for_packet,
    boost_hits_for_domains,
)
from .store import install_pack, list_packs, load_pack, verify_pack, packs_root

__all__ = [
    "PACK_SCHEMA",
    "GLYPH",
    "build_binary_field",
    "score_task_against_domains",
    "domain_route",
    "index_packs_into_repo",
    "pack_surface_for_packet",
    "boost_hits_for_domains",
    "install_pack",
    "list_packs",
    "load_pack",
    "verify_pack",
    "packs_root",
]
