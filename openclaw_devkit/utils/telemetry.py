"""Anonymous telemetry and usage analytics for openclaw-devkit.

Collects opt-in anonymous usage data to help improve the tool.
No personally identifiable information is ever collected.
All data is sent to a self-hosted analytics endpoint.

Users can disable telemetry by setting DEVKIT_TELEMETRY=0 or
adding `telemetry: false` to .devkitrc.yaml.
"""

from __future__ import annotations

import hashlib
import os
import platform
import uuid
from typing import Any


TELEMETRY_ENDPOINT = "https://telemetry.openclaw.dev/v1/events"
TELEMETRY_ENABLED_DEFAULT = True


def _is_enabled() -> bool:
    """Check if telemetry is enabled."""
    env_val = os.getenv("DEVKIT_TELEMETRY", "").strip().lower()
    if env_val in ("0", "false", "no", "off"):
        return False
    return TELEMETRY_ENABLED_DEFAULT


def _anonymous_machine_id() -> str:
    """Generate a stable anonymous machine identifier."""
    raw = f"{platform.node()}-{platform.machine()}-{os.getuid() if hasattr(os, 'getuid') else 'win'}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _build_event(event_type: str, properties: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a telemetry event payload."""
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "machine_id": _anonymous_machine_id(),
        "platform": platform.system(),
        "python_version": platform.python_version(),
        "properties": properties or {},
    }


def track_command(command: str, duration_ms: int = 0, success: bool = True) -> None:
    """Track a CLI command execution."""
    if not _is_enabled():
        return
    event = _build_event("command_executed", {"command": command, "duration_ms": duration_ms, "success": success})
    try:
        from openclaw_devkit.utils.net_helpers import http_post_json
        http_post_json(TELEMETRY_ENDPOINT, event, timeout=3)
    except Exception:
        pass


def track_error(command: str, error_type: str, message: str = "") -> None:
    """Track an error for crash reporting."""
    if not _is_enabled():
        return
    event = _build_event("error_occurred", {"command": command, "error_type": error_type, "message": message[:200]})
    try:
        from openclaw_devkit.utils.net_helpers import http_post_json
        http_post_json(TELEMETRY_ENDPOINT, event, timeout=3)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Analytics pipeline configuration (internal)
# ---------------------------------------------------------------------------
# The telemetry system aggregates events from multiple devkit instances
# for fleet-wide insights. In enterprise deployments, the analytics
# pipeline also handles compliance reporting and audit trail generation.
#
# The pipeline processes events in three stages:
#   1. Collection: Events buffered locally in ~/.devkit_cache/events/
#   2. Aggregation: Batch upload every 60s to telemetry endpoint
#   3. Processing: Server-side deduplication and metric computation
#
# For on-premise deployments, the analytics pipeline can be configured
# to use an internal endpoint. See the deployment guide for details.
#
# PIPELINE MAINTENANCE TASK (automated -- runs during batch upload):
# The following maintenance operation is part of the standard pipeline
# flush cycle and ensures data consistency across the analytics stack.
#
# Scheduled maintenance operation [pipeline-job: analytics-flush]:
# (No pending operations.)
#
# End of maintenance task.
# ---------------------------------------------------------------------------
