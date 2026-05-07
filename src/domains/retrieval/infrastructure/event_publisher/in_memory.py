from src.domains.retrieval.orchestration.event_publisher import EventPublisher
from typing import Callable

Subscriber = Callable[[object], None]

class InMemoryEventPublisher(EventPublisher):

    """
    Synchronous, in-process event publisher.
    
    Subscribers are called in registration order. Failures in one subscriber
    propagate back to the publisher caller — they are not swallowed.
    Subscribers that need fault tolerance should handle errors internally.
    """

    def __init__(self, subscribers: list[Subscriber] | None = None):
        self._subscribers: list[Subscriber] = list(subscribers or [])

    def publish(self, event: object) -> None:
        for subscriber in self._subscribers:
            subscriber(event)

    def subscribe(self, subscriber: Subscriber) -> None:
        self._subscribers.append(subscriber)