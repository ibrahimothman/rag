Gemini Embedder 2026-04-26.

Classification verified against Gemini API docs on 2026-04-26:

  HTTP  Code                  Classification
  ----  --------------------  ---------------
  400   INVALID_ARGUMENT      Permanent
  400   FAILED_PRECONDITION   Permanent
  403   PERMISSION_DENIED     Permanent
  404   NOT_FOUND             Permanent
  429   RESOURCE_EXHAUSTED    Transient
  500   INTERNAL              Transient
  503   UNAVAILABLE           Transient
  504   DEADLINE_EXCEEDED     Transient
  --    network/transport     Transient
