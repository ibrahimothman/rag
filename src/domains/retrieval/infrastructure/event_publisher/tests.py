import pytest
from .in_memory import InMemoryEventPublisher
from dataclasses import dataclass


@dataclass(frozen=True)
class MockEvent:
    payload: str

def test_publishes_to_all_subscribers():
    recieved_a= []
    recieved_b= []
    
    publisher = InMemoryEventPublisher(subscribers=[
        lambda event: recieved_a.append(event),
        lambda event: recieved_b.append(event),
    ])

    event = MockEvent(payload="test event")
    publisher.publish(event)

    assert recieved_a == [event]
    assert recieved_b == [event]

def test_no_subscribers_does_not_fail():
    publisher = InMemoryEventPublisher()
    event = MockEvent(payload="test event")
    publisher.publish(event)

def test_subscriber_failure_propagates():    
    def failing_subscriber(event) -> None:
        raise Exception("test failure")

    publisher = InMemoryEventPublisher(subscribers=[failing_subscriber])
    event = MockEvent(payload="test event")
    with pytest.raises(Exception, match="test failure"):
        publisher.publish(event)

def test_dynamic_subscription():        
    publisher = InMemoryEventPublisher()
    recieved = []
    event = MockEvent(payload="test event")
    publisher.subscribe(lambda event: recieved.append(event))
    publisher.publish(event)
    assert recieved == [event]