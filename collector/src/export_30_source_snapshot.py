from __future__ import annotations

from . import export_live_snapshot as live
from .sources.public_portals import PUBLIC_PORTAL_SOURCES, PUBLIC_SOURCE_TYPES


BASE_SOURCES = tuple(live.SOURCES)
NETWORK_SOURCES = (*BASE_SOURCES, *PUBLIC_PORTAL_SOURCES)


def _network_source_type(source_id: str) -> str:
    return PUBLIC_SOURCE_TYPES.get(source_id, live.source_type(source_id))


def validate_network() -> None:
    ids = [source.source_id for source in NETWORK_SOURCES]
    if len(ids) != 30:
        raise RuntimeError(f"Bid Finder source network must contain exactly 30 sources; found {len(ids)}")
    if len(set(ids)) != len(ids):
        duplicates = sorted({source_id for source_id in ids if ids.count(source_id) > 1})
        raise RuntimeError(f"Duplicate Bid Finder source ids: {', '.join(duplicates)}")


def main() -> int:
    validate_network()
    live.SOURCES = NETWORK_SOURCES
    live.source_type = _network_source_type
    print("Bid Finder 30-source network enabled:")
    for index, source in enumerate(NETWORK_SOURCES, start=1):
        print(f"  {index:02d}. {source.name} [{source.source_id}]")
    return live.main()


if __name__ == "__main__":
    raise SystemExit(main())
