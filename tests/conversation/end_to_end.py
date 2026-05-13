from dotenv import load_dotenv
import os
import logging
from uuid import uuid4

from src.domains.conversation.composition import build_conversation, ConversationConfig
from src.domains.agent.composition import build_agent
from src.domains.retrieval.composition import build_retrieval, RetrievalConfig
from src.shared.gemini import GeminiProviderClient, GeminiProviderClientConfig
from src.domains.generation.composition import build_generation, GenerationConfig
from src.shared.event_subscribers import log_event
from src.domains.conversation.api import StartConversation, SendMessage
from src.domains.conversation.api import AssistantMessageDelivered


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("conversation_one")


def print_answer(event) -> None:
    """
    A subscriber to print the assistant message to stdout.
    """
    if not isinstance(event, AssistantMessageDelivered):
        return
    print(f"\n{'─' * 60}")
    print(f"Answer:\n\n{event.content}\n")
    print(f"Grounding quality : {event.grounding_quality}")
    if event.citations:
        print(f"Citations         : {len(event.citations)}")
        for c in event.citations:
            print(f"  [{c.marker}] doc={c.citation.document_id} page={c.citation.page_number}")
    print(f"{'─' * 60}\n")

def main():

    db_url = os.getenv("DB_URL")
     if not db_url:
        raise ValueError("DB_URL environment variable is required")
    
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY environment variable is required")
    
    generation_model = os.getenv("GENERATION_MODEL_ID")
    if not generation_model:
        raise ValueError("GENERATION_MODEL_ID environment variable is required")
   
    embedding_model = os.getenv("EMBEDDING_MODEL_ID")
    if not embedding_model:
        raise ValueError("EMBEDDING_MODEL_ID environment variable is required")
    
    embedding_size_str = os.getenv("EMBEDDING_SIZE")
    if not embedding_size_str:
        raise ValueError("EMBEDDING_SIZE environment variable is required")
    try:
        embedding_size = int(embedding_size_str)
    except ValueError:
        raise ValueError(f"EMBEDDING_SIZE must be a valid integer, got: {embedding_size_str}")
    
    gemini_provider_client = GeminiProviderClient(GeminiProviderClientConfig(
        api_key=gemini_api_key,
    ))
    
    retrieval_handler = build_retrieval(RetrievalConfig(
        db_url=db_url,
        embedding_model=embedding_model,
        embedding_size=embedding_size,
    ), gemini_provider_client, event_subscribers=[log_event])

    generation_handler = build_generation(GenerationConfig(
        model=generation_model,
    ), gemini_provider_client, event_subscribers=[log_event])
    
    agent_handler = build_agent(
        retrieval_handler=retrieval_handler,
        generation_handler=generation_handler,
    )
    conversation_handler = build_conversation(ConversationConfig(
        db_url=db_url,
    ), agent_handler, event_subscribers=[log_event, print_answer])    

    logger.info("Conversation handler built. Sending question...")
    question = "What are the relationships for context mapping?"

    conversation = conversation_handler.handle_start_conversation(StartConversation(
        user_id=uuid4(),
    ))

    conversation_handler.handle_send_message(SendMessage(
        conversation_id=conversation.id,
        content=question,
    ))
if __name__ == "__main__":
    main()    