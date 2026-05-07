### The orchestration layer
It recieves commands from the outside world, creates and advances the ingestion jobs,
runs each stage in order, handles failures, and emit events.

It's the layer which know the full shape of the ingestion pipeline.

It answeres exactly one question:
"When a command arrived, what sequence of domain operaitons should happen, and what should be announced?" in other words,
the orchestration layer define the use cases and how they get implemented


ingestion/
└── orchestration/
    ├── pipeline.py          # the actual pipeline runner
    ├── handler.py           # command handlers (entry points)
    ├── job_repository.py    # interface for persisting jobs
    └── event_publisher.py   # interface for emitting events