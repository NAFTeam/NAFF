from naff import InteractionContext, PrefixedContext, HybridContext, SendableContext
from typeguard import check_type

__all__ = ()


def test_sendable_context() -> None:
    check_type("prefixed_context", PrefixedContext, SendableContext)
    check_type("interaction_context", InteractionContext, SendableContext)
    check_type("hybrid_context", HybridContext, SendableContext)
