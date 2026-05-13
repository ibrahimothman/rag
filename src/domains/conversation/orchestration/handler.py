from src.domains.conversation.orchestration.conversation_repository import ConversationRepository, ConversationNotFoundError
from src.domains.conversation.orchestration.event_publisher import EventPublisher
from src.domains.conversation.api.commands import StartConversation, SendMessage
from src.domains.conversation.domain import Conversation, UserMessage, AssistantMessage
from src.domains.conversation.api.events import (
    ConversationStarted,
    UserMessageReceived,
    AnswerProcessing,
    AssistantMessageDelivered,
    ConversationHistoryUpdated,
    ProcessingFailed
)

from src.domains.agent.orchestration.handler import AgentHandler
from src.domains.agent.api.commands import ProcessQuestion

class ConversationHandler:

    def __init__(
        self, 
        conversation_repository: ConversationRepository,
        event_publisher: EventPublisher,
        agent: AgentHandler
    ):
        self._conversations = conversation_repository
        self._events= event_publisher
        self._agent = agent

    def handle_start_conversation(self, command: StartConversation) -> Conversation:

        conversation = Conversation.start(command.user_id)
        self._conversations.save(conversation)
        self._events.publish(ConversationStarted(conversation.id, command.user_id))

        return conversation

    def handle_send_message(self, command: SendMessage) -> None:

        try:
            conversation = self._conversations.get(command.conversation_id)
        except ConversationNotFoundError as e:
            self._events.publish(ProcessingFailed(
                conversation_id=command.conversation_id,
                message_id=command.message_id,
                reason="Conversation not found"
            ))
            return

        user_message = conversation.add_user_message(command.content)
        self._conversations.add_message(conversation.id, user_message)

        self._events.publish(UserMessageReceived(conversation.id, user_message.id, user_message.content))
        self._events.publish(AnswerProcessing(conversation.id, user_message.id))

        answer = self._agent.handle_process_question(
            ProcessQuestion(
                request_id=user_message.id, 
                question=user_message.content
            ))

        if answer is None:
            self._events.publish(
                ProcessingFailed(
                    conversation_id=conversation.id, 
                    message_id=user_message.id, 
                    reason="Agent could not produce an answer"
                ))
            return

        assistant_message = conversation.add_assistant_message(
            content=answer.full_response,
            citations=answer.citations,
            grounding_quality=answer.grounding_quality
        )
        self._conversations.add_message(conversation.id, assistant_message)

        self._events.publish(
            AssistantMessageDelivered(
                conversation_id=conversation.id, 
                message_id=assistant_message.id, 
                content=answer.full_response,
                citations=answer.citations, 
                grounding_quality=answer.grounding_quality
            ))

        self._events.publish(
            ConversationHistoryUpdated(
                conversation_id=conversation.id, 
                turn_count=conversation.turn_count, 
                messages=tuple(conversation.messages)
            ))



        