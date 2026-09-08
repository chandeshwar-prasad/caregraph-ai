"""
app/services/observability.py

Enterprise Prometheus Metrics Collection and Zero-PHI Telemetry Bridge for CareGraph AI.
Provides:
1. Standard Prometheus Counter, Histogram, and Gauge collectors.
2. Direct hooks bridging internal sanitized telemetry into Prometheus metrics.
3. Observability tracking for graph execution latency, intent accuracy, safety escalations,
   token consumption/financial cost, and HL7 FHIR API transactions.
4. Export handler for Prometheus scraping (/metrics endpoint).
"""

import logging
from typing import Optional, Dict, Any, Tuple
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
    REGISTRY
)

logger = logging.getLogger("caregraph.observability")

# --- Prometheus Metrics Definitions ---

# 1. Graph Node & Workflow Execution Counters
graph_node_executions_total = Counter(
    "caregraph_graph_node_executions_total",
    "Total executions of graph nodes categorized by status",
    ["node_name", "status"]
)

intent_classifications_total = Counter(
    "caregraph_intent_classifications_total",
    "Intent classification results and accuracy tracking",
    ["detected_intent", "match"]
)

safety_escalations_total = Counter(
    "caregraph_safety_escalations_total",
    "Deterministic and triage safety escalations triggered",
    ["escalation_type", "risk_level"]
)

tool_executions_total = Counter(
    "caregraph_tool_executions_total",
    "Tool execution attempts by tool name and authorization outcome",
    ["tool_name", "status"]
)

fhir_api_calls_total = Counter(
    "caregraph_fhir_api_calls_total",
    "HL7 FHIR R4 server API calls by method, resource, and status",
    ["method", "resource_type", "status"]
)

# 2. Latency & Token Histograms
graph_node_latency_seconds = Histogram(
    "caregraph_graph_node_latency_seconds",
    "Latency of graph node executions in seconds",
    ["node_name"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)

llm_token_usage_total = Histogram(
    "caregraph_llm_token_usage_total",
    "LLM token consumption distribution per model call",
    ["model", "token_type"],
    buckets=(50, 100, 250, 500, 1000, 2500, 5000, 10000)
)

llm_request_latency_seconds = Histogram(
    "caregraph_llm_request_latency_seconds",
    "LLM inference API request latency in seconds",
    ["model"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0)
)

fhir_api_latency_seconds = Histogram(
    "caregraph_fhir_api_latency_seconds",
    "FHIR R4 API request latency in seconds",
    ["resource_type"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)

# 3. State Gauges
active_sessions_gauge = Gauge(
    "caregraph_active_sessions_current",
    "Current number of active agent conversation sessions"
)

estimated_total_cost_usd = Gauge(
    "caregraph_estimated_total_cost_usd",
    "Cumulative estimated LLM inference costs in USD"
)


# --- Instrumentation Recording Functions ---

def record_node_execution(node_name: str, status: str = "success", latency_seconds: float = 0.01):
    """Records a single graph node execution event."""
    try:
        graph_node_executions_total.labels(node_name=node_name, status=status).inc()
        if latency_seconds > 0:
            graph_node_latency_seconds.labels(node_name=node_name).observe(latency_seconds)
    except Exception as e:
        logger.debug(f"Failed to record node execution metric: {e}")


def record_intent_classification(detected_intent: str, match: bool = True):
    """Records intent routing decision."""
    try:
        intent_classifications_total.labels(
            detected_intent=str(detected_intent),
            match="true" if match else "false"
        ).inc()
    except Exception as e:
        logger.debug(f"Failed to record intent metric: {e}")


def record_safety_escalation(escalation_type: str = "red_flag", risk_level: str = "emergency"):
    """Records emergency or red-flag safety escalation."""
    try:
        safety_escalations_total.labels(
            escalation_type=str(escalation_type),
            risk_level=str(risk_level)
        ).inc()
    except Exception as e:
        logger.debug(f"Failed to record safety escalation metric: {e}")


def record_tool_execution(tool_name: str, status: str = "success"):
    """Records server-side tool execution / authorization outcome."""
    try:
        tool_executions_total.labels(
            tool_name=str(tool_name),
            status=str(status)
        ).inc()
    except Exception as e:
        logger.debug(f"Failed to record tool execution metric: {e}")


def record_fhir_call(method: str, resource_type: str, status: str = "success", latency_seconds: float = 0.05):
    """Records HL7 FHIR API call and response latency."""
    try:
        fhir_api_calls_total.labels(
            method=str(method).upper(),
            resource_type=str(resource_type),
            status=str(status)
        ).inc()
        if latency_seconds > 0:
            fhir_api_latency_seconds.labels(resource_type=str(resource_type)).observe(latency_seconds)
    except Exception as e:
        logger.debug(f"Failed to record FHIR metric: {e}")


def record_llm_usage(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    latency_seconds: Optional[float] = None
):
    """Records LLM token consumption and request latency."""
    try:
        if prompt_tokens > 0:
            llm_token_usage_total.labels(model=model, token_type="input").observe(prompt_tokens)
        if completion_tokens > 0:
            llm_token_usage_total.labels(model=model, token_type="output").observe(completion_tokens)
        if latency_seconds is not None and latency_seconds > 0:
            llm_request_latency_seconds.labels(model=model).observe(latency_seconds)
    except Exception as e:
        logger.debug(f"Failed to record LLM metrics: {e}")


def update_cost_gauge(total_cost: float):
    """Updates the Prometheus gauge for total financial cost in USD."""
    try:
        estimated_total_cost_usd.set(total_cost)
    except Exception as e:
        logger.debug(f"Failed to set cost gauge: {e}")


def generate_prometheus_metrics() -> Tuple[bytes, str]:
    """
    Renders all registered Prometheus metrics in the official text format.
    Guarantees Zero PHI (only metrics, counters, and buckets emitted).
    """
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
