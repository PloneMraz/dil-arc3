"""The eight layers T1–T8 (protocol §6.3), in dependency order.

T1 confirms the activity-environment. T2 draws the self/environment line, where
the self crystallizes. T3 ingests channels, T4 binds context, T5 builds
expectation — the layer where resistance becomes information. T6 models the
Other, T7 registers absence, and T8 abstracts across entities and closes the
loop back to T1.
"""

from .t1 import ROOT_FRAME, T1, create_t1
from .t2 import (
    Emission,
    ObservedChange,
    T2,
    T2Input,
    T2Output,
    TaggedChange,
    create_t2,
)
from .t3 import ChannelTransducer, T3, T3Input, T3Output, create_t3, default_transducer
from .t4 import (
    STRANGER,
    BoundInfo,
    ContextResolver,
    T4,
    T4Input,
    T4Output,
    create_t4,
    default_resolver,
)
from .t5 import T5, T5Input, T5Output, T5Result, create_t5
from .t6 import IndependenceEvidence, T6, T6Input, T6Output, create_t6
from .t7 import (
    AbsenceReading,
    ExpectedEntity,
    T7,
    T7Input,
    T7Output,
    create_t7,
)
from .t8 import ObservedInteraction, T8, T8Input, T8Output, create_t8

__all__ = [
    "ROOT_FRAME",
    "STRANGER",
    "AbsenceReading",
    "BoundInfo",
    "ChannelTransducer",
    "ContextResolver",
    "Emission",
    "ExpectedEntity",
    "IndependenceEvidence",
    "ObservedChange",
    "ObservedInteraction",
    "T1",
    "T2",
    "T2Input",
    "T2Output",
    "T3",
    "T3Input",
    "T3Output",
    "T4",
    "T4Input",
    "T4Output",
    "T5",
    "T5Input",
    "T5Output",
    "T5Result",
    "T6",
    "T6Input",
    "T6Output",
    "T7",
    "T7Input",
    "T7Output",
    "T8",
    "T8Input",
    "T8Output",
    "TaggedChange",
    "create_t1",
    "create_t2",
    "create_t3",
    "create_t4",
    "create_t5",
    "create_t6",
    "create_t7",
    "create_t8",
    "default_resolver",
    "default_transducer",
]
