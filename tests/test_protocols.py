from naff import InteractionContext, PrefixedContext, SendableContext
from typeguard import check_type


def test_sendable_context() -> None:
    check_type('prefixed_context', PrefixedContext, SendableContext)
    check_type('interaction_context', InteractionContext, SendableContext)
