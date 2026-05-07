import logging
logger = logging.getLogger("ingestion.events")

def log_event(event: object) -> None:
    logger.info(f"{type(event).__name__}: {event}")

