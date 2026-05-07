import pytest
from .plain_text import PlainTextExtractor
from ...stages.extractor import SourceFile, ExtractionFailed
import tempfile
import os

def test_extracts_utf8_text():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
        temp_file.write("Hello, world!".encode("utf-8"))
        path = temp_file.name
        temp_file.close()
   
    extractor = PlainTextExtractor()
    source_file = SourceFile(location=path, mime_type="text/plain")

    document = extractor.extract(source_file)
    assert document.text == "Hello, world!"


def test_supports_known_mime_types():
    extractor = PlainTextExtractor()
    assert extractor.supports("text/plain")
    assert not extractor.supports("application/pdf")


def test_missing_file_is_permanent_failure():
    extractor = PlainTextExtractor()
    source_file = SourceFile(location="non_existent.txt", mime_type="text/plain")
    with pytest.raises(ExtractionFailed) as e:
        extractor.extract(source_file)
    assert e.value.permanent == True

def test_invalid_utf8_is_permanent_failure():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
        temp_file.write("Hello, world!".encode("utf-16"))
        path = temp_file.name
        temp_file.close()
   
    extractor = PlainTextExtractor()
    source_file = SourceFile(location=path, mime_type="text/plain")
    with pytest.raises(ExtractionFailed) as e:
        extractor.extract(source_file)
    assert e.value.permanent == True


