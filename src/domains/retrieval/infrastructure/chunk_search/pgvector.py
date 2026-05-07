import stat
from src.domains.retrieval.stages.chunk_search import ChunkSearch
from dataclasses import dataclass
from src.domains.retrieval.domain.query import Query
from src.domains.retrieval.domain.chunk import ScoredChunk, Citation
from src.domains.retrieval.stages.chunk_search import ChunkSearchFailed
from src.domains.retrieval.domain.query import EmbeddedQuery

from psycopg.errors import (
    OperationalError,
    InterfaceError,
    UndefinedTable,
    UndefinedColumn,
    DataError
)
import psycopg
from psycopg.rows import dict_row
from pgvector.psycopg import register_vector

@dataclass(frozen=True)
class PgVectorChunkSearchConfig:
    db_url: str

class PgVectorChunkSearch(ChunkSearch):

    def __init__(self, config: PgVectorChunkSearchConfig):
        self._config = config

    def find_similar_chunks(
        self, 
        query: EmbeddedQuery, 
        limit: int
    ) -> list[ScoredChunk]:
        try:
            with psycopg.connect(self._config.db_url) as conn:
                
                with conn.cursor(row_factory=dict_row) as cur:
                    register_vector(conn)
                    sql_text = """
                        SELECT chunk_id, text, document_id, 1.0 - (embedding <=> %s::vector) AS score 
                        FROM chunks
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                        """
                    rows = cur.execute(sql_text, (query.vector, query.vector, limit)).fetchall()

            # infrastrucre - domain translation
            return [self._to_scored_chunk(row) for row in rows]
                    
        except (OperationalError, InterfaceError) as e:
            raise ChunkSearchFailed(f"Database connection error: {e}", permanent=False)
        except (UndefinedTable, UndefinedColumn) as e:
            raise ChunkSearchFailed(f"Database schema error: {e}", permanent=True)
        except DataError as e:
            raise ChunkSearchFailed(f"Data error: {e}", permanent=True)

    @staticmethod
    def _to_scored_chunk(row: dict) -> ScoredChunk:
        return ScoredChunk(
            chunk_id=row["chunk_id"],
            content=row["text"],
            score=row["score"],
            citation=Citation(
                document_id=row["document_id"],
                page=row.get("page", None)
            ),
            
        )



    