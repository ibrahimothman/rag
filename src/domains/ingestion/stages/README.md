### Stages interfaces
it's a contract for each stage, declaring the input, output, and failures **without committing to how it's implemented**

```mermaid
graph TD
    SourceFile -->|Extractor| ExtractedDocument
    ExtractedDocument -->|Chunker| ListOfChunks[list[Chunk]]
    ListOfChunks -->|Embedder| ListOfEmbeddedChunks[list[EmbeddedChunk]]
    ListOfEmbeddedChunks -->|Indexer| Store[written to store]
```
