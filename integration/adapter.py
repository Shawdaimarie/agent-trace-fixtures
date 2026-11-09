"""Small-profile preflight followed by the real pinned Sentinel importer."""
from __future__ import annotations

import json
from tracecheck import inspect_trace


def adapt(raw: bytes, case_id: str):
    """Never dispatch rejected input. Missing-parent telemetry remains importable."""
    diagnostics = inspect_trace(raw)
    if set(diagnostics) - {'missing_parent'}:
        return diagnostics, None
    from sentinel.trace_import import TraceImportConfig, import_otel_document
    result = import_otel_document(json.loads(raw), source_bytes=raw,
                                  config=TraceImportConfig(case_id=case_id))
    return diagnostics, result
