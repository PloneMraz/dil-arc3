"""The runtime / requisition ring — where DIL meets the host.

Wires the loop as a long-lived daemon over a declared host, with state accruing
across cycles. The self is what occurs while it runs.
"""

from .absorption import AbsorptionReport, SourceAbsorption, measure_absorption
from .commit import (
    SystemSnapshot,
    decode_snapshot_value,
    encode_snapshot_value,
    restore_snapshot,
    take_snapshot,
)
from .daemon import Daemon, RequisitionReport, create_daemon
from .decisions import (
    DIVERSITY_WINDOW,
    MIN_DIVERSITY_SOURCES,
    MODE_B_SOURCE,
    REFLECTION_MECHANISM,
)
from .diversity import DiversityMonitor, create_diversity_monitor
from .host_source import HostSource, ScriptedSource, scripted_source
from .manifest import collect_manifest
from .peer import (
    PEER_REFLECTION_CHANNEL,
    PeerLog,
    PeerReflectingSource,
    ReadOnlyEventLog,
    peer_reflecting_source,
    read_only,
)
from .reflection import (
    CollisionCoordinate,
    ReflectionError,
    ReflectionReading,
    collision_coordinates,
    form_reading,
    reading_payload,
    reflection_signal,
    reflection_transducer,
)
from .requisition import (
    RejectedItem,
    RequisitionError,
    Requisitioned,
    requisition,
)

__all__ = [
    "DIVERSITY_WINDOW",
    "MIN_DIVERSITY_SOURCES",
    "MODE_B_SOURCE",
    "REFLECTION_MECHANISM",
    "PEER_REFLECTION_CHANNEL",
    "AbsorptionReport",
    "CollisionCoordinate",
    "Daemon",
    "DiversityMonitor",
    "HostSource",
    "PeerLog",
    "ReadOnlyEventLog",
    "PeerReflectingSource",
    "ReflectionError",
    "ReflectionReading",
    "RejectedItem",
    "Requisitioned",
    "RequisitionError",
    "RequisitionReport",
    "ScriptedSource",
    "SourceAbsorption",
    "SystemSnapshot",
    "collect_manifest",
    "collision_coordinates",
    "create_daemon",
    "create_diversity_monitor",
    "decode_snapshot_value",
    "encode_snapshot_value",
    "form_reading",
    "measure_absorption",
    "peer_reflecting_source",
    "read_only",
    "reading_payload",
    "reflection_signal",
    "reflection_transducer",
    "requisition",
    "restore_snapshot",
    "scripted_source",
    "take_snapshot",
]
