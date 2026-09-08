"""
app/services/telemetry.py

Production Telemetry, Tracing, and Zero-PHI Telemetry Architecture.
Provides:
1. Environment-aware tracing configuration (LangSmith / local collector).
2. Strict PHI/PII redaction and sanitization before telemetry span emission.
3. Workflow latency, token counting, and status tracking.
4. Non-blocking in-memory telemetry buffer for live observability and testing.
5. Invariance: Telemetry never delays emergency safety escalation.
"""

import os
import re
import time
import logging
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
from datetime import datetime, timezone

logger = logging.getLogger("caregraph.telemetry")

# Environment configurations
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "caregraph-ai")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "")
TELEMETRY_ENABLED = os.getenv("TELEMETRY_ENABLED", "true").lower() == "true"

# Sensitive keywords and patterns to scrub
SENSITIVE_KEY_PATTERNS = [
    "password", "secret", "token", "key", "auth", "jwt",
    "notes", "raw_message", "user_message", "prompt",
    "prescription", "diagnosis", "ssn", "dob"
]

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")


def redact_phi(value: Any) -> Any:
    """
    Recursively scrubs PHI, PII, raw clinical free-text, and credentials from telemetry data.
    """
    if value is None:
        return None
    if isinstance(value, str):
        # 1. Scrub email and phone patterns
        sanitized = EMAIL_REGEX.sub("[REDACTED_EMAIL]", value)
        sanitized = PHONE_REGEX.sub("[REDACTED_PHONE]", sanitized)
        # 2. Check for token-like strings
        if len(sanitized) > 80 and not (" " in sanitized or "/" in sanitized):
            return "[REDACTED_TOKEN]"
        return sanitized
    elif isinstance(value, dict):
        sanitized_dict = {}
        for k, v in value.items():
            k_lower = str(k).lower()
            if any(p in k_lower for p in SENSITIVE_KEY_PATTERNS):
                if isinstance(v, str):
                    sanitized_dict[k] = f"[REDACTED_TEXT: len={len(v)}]"
                else:
                    sanitized_dict[k] = "[REDACTED_SENSITIVE]"
            else:
                sanitized_dict[k] = redact_phi(v)
        return sanitized_dict
    elif isinstance(value, (list, tuple, set)):
        return [redact_phi(item) for item in value]
    else:
        return value


class TelemetrySpan:
    """Represents a sanitized execution span in a multi-agent workflow."""

    def __init__(self, name: str, span_type: str = "custom", attributes: Optional[Dict[str, Any]] = None):
        self.name = name
        self.span_type = span_type
        self.start_time: float = time.time()
        self.end_time: Optional[float] = None
        self.duration_ms: float = 0.0
        self.status: str = "SUCCESS"  # SUCCESS, ERROR, SAFETY_ESCALATED
        self.attributes: Dict[str, Any] = redact_phi(attributes or {})

    def finish(self, status: str = "SUCCESS", extra_attributes: Optional[Dict[str, Any]] = None):
        self.end_time = time.time()
        self.duration_ms = round((self.end_time - self.start_time) * 1000, 2)
        self.status = status
        if extra_attributes:
            sanitized_extras = redact_phi(extra_attributes)
            self.attributes.update(sanitized_extras)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "span_type": self.span_type,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "attributes": self.attributes
        }


class TelemetryCollector:
    """
    In-memory ring buffer collector for workflow spans and metrics.
    Ensures zero external dependency requirement for test suites.
    """

    def __init__(self, max_traces: int = 200):
        self.max_traces = max_traces
        self.traces: List[Dict[str, Any]] = []

    def record_span(self, span: TelemetrySpan):
        if not TELEMETRY_ENABLED:
            return
        span_dict = span.to_dict()
        self.traces.append(span_dict)
        if len(self.traces) > self.max_traces:
            self.traces.pop(0)

    def record_workflow_event(
        self,
        session_id: str,
        user_id: int,
        intent: str,
        selected_agent: str,
        latency_ms: float,
        status: str = "SUCCESS",
        safety_escalated: bool = False,
        token_usage: Optional[Dict[str, int]] = None,
        tool_name: Optional[str] = None,
        actor_role: str = "patient"
    ) -> Dict[str, Any]:
        """Records an aggregated workflow-level telemetry record with strict sanitization."""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": str(session_id),
            "user_id": int(user_id),
            "actor_role": str(actor_role),
            "intent": str(intent),
            "selected_agent": str(selected_agent),
            "latency_ms": round(float(latency_ms), 2),
            "status": "SAFETY_ESCALATED" if safety_escalated else str(status),
            "safety_escalated": bool(safety_escalated),
            "tool_name": tool_name,
            "token_usage": token_usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        }
        sanitized = redact_phi(record)
        self.traces.append(sanitized)
        if len(self.traces) > self.max_traces:
            self.traces.pop(0)

        # Bridge to Prometheus Metrics
        try:
            from app.services import observability
            observability.record_node_execution(
                node_name=selected_agent,
                status=status.lower(),
                latency_seconds=max(0.001, latency_ms / 1000.0)
            )
            observability.record_intent_classification(detected_intent=intent)
            if safety_escalated:
                observability.record_safety_escalation(escalation_type="red_flag", risk_level="emergency")
            if tool_name:
                observability.record_tool_execution(tool_name=tool_name, status=status.lower())
        except Exception as obs_err:
            logger.debug(f"Observability bridge error: {obs_err}")

        return sanitized

    def get_summary(self) -> Dict[str, Any]:
        """Calculates real-time operational metrics across recorded telemetry events."""
        if not self.traces:
            return {
                "total_events": 0,
                "avg_latency_ms": 0.0,
                "safety_escalations": 0,
                "error_rate": 0.0,
                "intents_breakdown": {},
                "agents_breakdown": {}
            }

        total = len(self.traces)
        latencies = [t.get("duration_ms", t.get("latency_ms", 0.0)) for t in self.traces]
        avg_latency = round(sum(latencies) / total, 2) if total > 0 else 0.0
        safety_count = sum(1 for t in self.traces if t.get("safety_escalated") or t.get("status") == "SAFETY_ESCALATED")
        errors = sum(1 for t in self.traces if t.get("status") == "ERROR")

        intents: Dict[str, int] = {}
        agents: Dict[str, int] = {}
        for t in self.traces:
            i = t.get("attributes", {}).get("intent", t.get("intent", "unknown"))
            a = t.get("attributes", {}).get("selected_agent", t.get("selected_agent", "unknown"))
            intents[i] = intents.get(i, 0) + 1
            agents[a] = agents.get(a, 0) + 1

        return {
            "total_events": total,
            "avg_latency_ms": avg_latency,
            "safety_escalations": safety_count,
            "error_rate": round(errors / total, 4) if total > 0 else 0.0,
            "intents_breakdown": intents,
            "agents_breakdown": agents
        }

    def clear(self):
        self.traces.clear()


# Global telemetry singleton
global_telemetry = TelemetryCollector()


# --- Phase 9 Milestone 4: Model Pricing & Cost Accounting ---

MODEL_PRICING_TABLE: Dict[str, Dict[str, float]] = {
    "llama-3.1-8b-instant": {
        "prompt_per_1m": 0.05,
        "completion_per_1m": 0.08,
        "category": "fast_tier"
    },
    "llama-3.3-70b-versatile": {
        "prompt_per_1m": 0.59,
        "completion_per_1m": 0.79,
        "category": "strong_tier"
    },
    "mixtral-8x7b-32768": {
        "prompt_per_1m": 0.24,
        "completion_per_1m": 0.24,
        "category": "standard_tier"
    },
    "mock-model": {
        "prompt_per_1m": 0.00,
        "completion_per_1m": 0.00,
        "category": "mock_tier"
    }
}


def calculate_token_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Calculates exact token cost in USD based on published model pricing.
    """
    pricing = MODEL_PRICING_TABLE.get(model, MODEL_PRICING_TABLE["llama-3.3-70b-versatile"])
    prompt_cost = (prompt_tokens / 1_000_000.0) * pricing["prompt_per_1m"]
    completion_cost = (completion_tokens / 1_000_000.0) * pricing["completion_per_1m"]
    return round(prompt_cost + completion_cost, 7)


class TokenCostTracker:
    """
    Tracks cumulative token usage, costs per model tier, and cost-per-workflow across sessions.
    """

    def __init__(self):
        self.total_prompt_tokens: int = 0
        self.total_completion_tokens: int = 0
        self.total_tokens: int = 0
        self.total_cost_usd: float = 0.0
        self.model_usage: Dict[str, Dict[str, Any]] = {}
        self.workflow_costs: List[Dict[str, Any]] = []

    def record_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        workflow_name: str = "general_chat",
        session_id: Optional[str] = None
    ) -> float:
        """Records token counts and calculates incremental USD cost."""
        total_tok = prompt_tokens + completion_tokens
        cost = calculate_token_cost(model, prompt_tokens, completion_tokens)

        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_tokens += total_tok
        self.total_cost_usd = round(self.total_cost_usd + cost, 7)

        if model not in self.model_usage:
            self.model_usage[model] = {
                "invocations": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cost_usd": 0.0
            }

        self.model_usage[model]["invocations"] += 1
        self.model_usage[model]["prompt_tokens"] += prompt_tokens
        self.model_usage[model]["completion_tokens"] += completion_tokens
        self.model_usage[model]["total_tokens"] += total_tok
        self.model_usage[model]["cost_usd"] = round(self.model_usage[model]["cost_usd"] + cost, 7)

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id or "default",
            "workflow_name": workflow_name,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tok,
            "cost_usd": cost
        }
        self.workflow_costs.append(record)
        if len(self.workflow_costs) > 200:
            self.workflow_costs.pop(0)

        # Bridge to Prometheus Metrics
        try:
            from app.services import observability
            observability.record_llm_usage(
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens
            )
            observability.update_cost_gauge(self.total_cost_usd)
        except Exception as obs_err:
            logger.debug(f"Observability cost update error: {obs_err}")

        return cost

    def get_cost_summary(self) -> Dict[str, Any]:
        """Returns comprehensive aggregated token and financial summary."""
        avg_cost_per_workflow = (
            round(self.total_cost_usd / len(self.workflow_costs), 7)
            if self.workflow_costs else 0.0
        )
        return {
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "total_recorded_workflows": len(self.workflow_costs),
            "avg_cost_per_workflow_usd": avg_cost_per_workflow,
            "model_distribution": self.model_usage,
            "pricing_reference": MODEL_PRICING_TABLE
        }

    def reset(self):
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0
        self.total_cost_usd = 0.0
        self.model_usage.clear()
        self.workflow_costs.clear()


global_cost_tracker = TokenCostTracker()


@contextmanager
def trace_span(name: str, span_type: str = "custom", attributes: Optional[Dict[str, Any]] = None):
    """
    Context manager for measuring execution time, status, and recording sanitized span metrics.
    """
    span = TelemetrySpan(name=name, span_type=span_type, attributes=attributes)
    try:
        yield span
        span.finish(status=span.status)
    except Exception as e:
        span.finish(status="ERROR", extra_attributes={"error_type": type(e).__name__})
        raise
    finally:
        global_telemetry.record_span(span)
        try:
            from app.services import observability
            observability.record_node_execution(
                node_name=span.name,
                status=span.status.lower(),
                latency_seconds=max(0.001, span.duration_ms / 1000.0)
            )
        except Exception:
            pass

