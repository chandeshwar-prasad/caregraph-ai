"""
tests/test_model_routing_and_cost.py

Automated tests for Phase 9 Milestone 4:
Cost Tracking, Token Accounting, Model Router Policy, and Comparative Evaluation.
"""

from fastapi.testclient import TestClient
from app.services.telemetry import (
    calculate_token_cost,
    TokenCostTracker,
    global_cost_tracker,
    MODEL_PRICING_TABLE
)
from app.services.llm import (
    ModelRouter,
    evaluate_model_router_performance
)
from app.main import app

client = TestClient(app)


def test_calculate_token_cost_accuracy():
    """Verify exact USD calculation for different model pricing tiers."""
    # llama-3.1-8b-instant: $0.05/1M prompt, $0.08/1M completion
    cost_fast = calculate_token_cost("llama-3.1-8b-instant", prompt_tokens=1_000_000, completion_tokens=1_000_000)
    assert cost_fast == 0.13

    # llama-3.3-70b-versatile: $0.59/1M prompt, $0.79/1M completion
    cost_strong = calculate_token_cost("llama-3.3-70b-versatile", prompt_tokens=1_000_000, completion_tokens=1_000_000)
    assert cost_strong == 1.38

    # Small realistic query: 150 prompt, 50 completion
    cost_small = calculate_token_cost("llama-3.1-8b-instant", prompt_tokens=150, completion_tokens=50)
    assert cost_small > 0.0
    assert cost_small < 0.0001


def test_token_cost_tracker_accumulation():
    """Verify TokenCostTracker tracks totals and model distributions."""
    tracker = TokenCostTracker()
    tracker.reset()

    tracker.record_usage("llama-3.1-8b-instant", prompt_tokens=200, completion_tokens=100, workflow_name="intent_classification")
    tracker.record_usage("llama-3.3-70b-versatile", prompt_tokens=400, completion_tokens=200, workflow_name="triage_reasoning")

    summary = tracker.get_cost_summary()
    assert summary["total_prompt_tokens"] == 600
    assert summary["total_completion_tokens"] == 300
    assert summary["total_tokens"] == 900
    assert summary["total_cost_usd"] > 0.0
    assert summary["total_recorded_workflows"] == 2
    assert "llama-3.1-8b-instant" in summary["model_distribution"]
    assert "llama-3.3-70b-versatile" in summary["model_distribution"]


def test_model_router_policy_and_selection():
    """Verify ModelRouter routes lightweight tasks to Fast Tier and complex tasks to Strong Tier."""
    # Fast tier assignments
    assert ModelRouter.select_model("intent_classification") == ModelRouter.FAST_MODEL
    assert ModelRouter.select_model("scheduling") == ModelRouter.FAST_MODEL
    assert ModelRouter.select_model("reminders") == ModelRouter.FAST_MODEL

    # Strong tier assignments
    assert ModelRouter.select_model("complex_triage") == ModelRouter.STRONG_MODEL
    assert ModelRouter.select_model("clinical_synthesis") == ModelRouter.STRONG_MODEL
    assert ModelRouter.select_model("records_trend_analysis") == ModelRouter.STRONG_MODEL


def test_model_router_no_silent_escalation_rule():
    """Verify that routine tasks do not escalate to strong tier unless complexity exceeds 0.75."""
    # Low complexity general chat -> Fast Model
    assert ModelRouter.select_model("general_chat", complexity_score=0.2) == ModelRouter.FAST_MODEL
    # Explicit high complexity -> Strong Model
    assert ModelRouter.select_model("general_chat", complexity_score=0.9) == ModelRouter.STRONG_MODEL

    policy = ModelRouter.get_routing_policy_summary()
    assert "No silent escalation" in policy["escalation_policy"]
    assert policy["default_fallback_model"] == ModelRouter.FALLBACK_MODEL


def test_comparative_performance_evaluation():
    """Verify comparative analysis computes valid latency, cost, and savings metrics."""
    perf = evaluate_model_router_performance(sample_queries_count=100)
    assert perf["workload_queries"] == 100
    assert "fast_tier" in perf
    assert "strong_tier" in perf
    assert perf["fast_tier"]["cost_per_query_usd"] < perf["strong_tier"]["cost_per_query_usd"]
    assert perf["fast_tier"]["estimated_latency_ms"] < perf["strong_tier"]["estimated_latency_ms"]
    assert perf["cost_savings_percentage"] > 70.0  # Fast tier provides >70% cost reduction


def test_costs_api_endpoint():
    """Verify FastAPI /metrics/costs returns structured financial and routing data."""
    res = client.get("/metrics/costs")
    assert res.status_code == 200
    data = res.json()
    assert "cost_summary" in data
    assert "routing_policy" in data
    assert "comparative_analysis" in data
    assert "fast_tier_model" in data["routing_policy"]
    assert "cost_savings_percentage" in data["comparative_analysis"]
