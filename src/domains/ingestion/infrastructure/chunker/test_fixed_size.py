import pytest
from .fixed_size import FixedSizeChunker, FixedSizeChunkerConfig
from ...stages.extractor import ExtractedDocument
from uuid import uuid4

def test_chunks_have_expected_overlap():
    text = "a" * 1000 + "b" * 1000 + "c" * 1000
    document = ExtractedDocument(
        id= uuid4(),
        text=text,
    )

    chunker = FixedSizeChunker(FixedSizeChunkerConfig(chunk_size=1000, overlap_size=200))
    
    chunks = chunker.chunk(document)

    assert len(chunks) > 1
    assert all(c.source_document_id == document.id for c in chunks)
    assert chunks[1].metadata["char_start"] == 800 # 1000 - 200 overlap
    assert chunks[0].text[-200:] == chunks[1].text[:200] # overlap matches


def test_empty_text_returns_empty_list():
    document = ExtractedDocument(
        id= uuid4(),
        text="",
    )
    chunker = FixedSizeChunker(FixedSizeChunkerConfig(chunk_size=1000, overlap_size=200))
    chunks = chunker.chunk(document)
    assert len(chunks) == 0


def test_overlap_must_be_smaller_than_chunk_size():
    with pytest.raises(ValueError):
        FixedSizeChunker(FixedSizeChunkerConfig(chunk_size=1000, overlap_size=1001))
