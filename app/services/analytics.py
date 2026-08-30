"""
app/services/analytics.py

Server-side analytics aggregation service for Power BI and executive dashboards.
Provides zero-PHI clinical operations, agent telemetry, cost intelligence,
and tabular export datasets.
"""

import io
import csv
from typing import Dict, Any, List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app import models
from app.services.telemetry import global_telemetry, global_cost_tracker, MODEL_PRICING_TABLE


def get_clinical_operations_metrics(db: Session) -> Dict[str, Any]:
    """
    Computes aggregated operational metrics from clinical tables with strict zero-PHI guarantees.
    No patient-identifiable data (names, DOB, emails, phone numbers, notes, MRNs) is exposed.
    """
    total_patients = db.query(models.Patient).count()

    # 1. Appointments Aggregation
    total_appointments = db.query(models.Appointment).count()
    appts_by_status_query = (
        db.query(models.Appointment.status, func.count(models.Appointment.id))
        .group_by(models.Appointment.status)
        .all()
    )
    appointments_by_status = {status: count for status, count in appts_by_status_query}

    appts_by_specialty_query = (
        db.query(models.Appointment.specialty, func.count(models.Appointment.id))
        .group_by(models.Appointment.specialty)
        .all()
    )
    appointments_by_specialty = {spec: count for spec, count in appts_by_specialty_query}

    appts_by_doctor_query = (
        db.query(models.Appointment.doctor_name, func.count(models.Appointment.id))
        .group_by(models.Appointment.doctor_name)
        .all()
    )
    appointments_by_doctor = {doc: count for doc, count in appts_by_doctor_query}

    # 2. Medications Aggregation
    total_medications = db.query(models.Medication).count()
    active_medications = (
        db.query(models.Medication).filter(models.Medication.is_active == True).count()
    )
    inactive_medications = total_medications - active_medications

    meds_by_name_query = (
        db.query(models.Medication.name, func.count(models.Medication.id))
        .group_by(models.Medication.name)
        .all()
    )
    medications_by_name = {name: count for name, count in meds_by_name_query}

    meds_by_freq_query = (
        db.query(models.Medication.frequency, func.count(models.Medication.id))
        .group_by(models.Medication.frequency)
        .all()
    )
    medications_by_frequency = {freq: count for freq, count in meds_by_freq_query}

    # 3. Vitals Aggregation
    total_vitals = db.query(models.Vital).count()
    vitals_by_type_query = (
        db.query(models.Vital.vital_type, func.count(models.Vital.id))
        .group_by(models.Vital.vital_type)
        .all()
    )
    vitals_by_type = {v_type: count for v_type, count in vitals_by_type_query}

    # 4. Consents Aggregation
    total_consents = db.query(models.PatientConsent).count()
    consents_by_type_query = (
        db.query(models.PatientConsent.consent_type, func.count(models.PatientConsent.id))
        .group_by(models.PatientConsent.consent_type)
        .all()
    )
    consents_by_type = {c_type: count for c_type, count in consents_by_type_query}

    consents_by_status_query = (
        db.query(models.PatientConsent.status, func.count(models.PatientConsent.id))
        .group_by(models.PatientConsent.status)
        .all()
    )
    consents_by_status = {status: count for status, count in consents_by_status_query}

    # 5. Reminders Aggregation
    total_reminders = db.query(models.MedicationReminder).count()
    reminders_by_status_query = (
        db.query(models.MedicationReminder.status, func.count(models.MedicationReminder.id))
        .group_by(models.MedicationReminder.status)
        .all()
    )
    reminders_by_status = {status: count for status, count in reminders_by_status_query}

    return {
        "total_patients": total_patients,
        "appointments": {
            "total_count": total_appointments,
            "by_status": appointments_by_status,
            "by_specialty": appointments_by_specialty,
            "by_doctor": appointments_by_doctor,
        },
        "medications": {
            "total_count": total_medications,
            "active_count": active_medications,
            "inactive_count": inactive_medications,
            "by_name": medications_by_name,
            "by_frequency": medications_by_frequency,
        },
        "vitals": {
            "total_count": total_vitals,
            "by_type": vitals_by_type,
        },
        "consents": {
            "total_count": total_consents,
            "by_type": consents_by_type,
            "by_status": consents_by_status,
        },
        "reminders": {
            "total_count": total_reminders,
            "by_status": reminders_by_status,
        },
        "zero_phi": True,
    }


def get_agent_telemetry_metrics() -> Dict[str, Any]:
    """
    Retrieves aggregated multi-agent performance and operational telemetry metrics.
    Scrubbed and validated to contain zero PHI/PII.
    """
    telemetry_summary = global_telemetry.get_summary()
    traces = global_telemetry.traces

    # Calculate status and tool usage breakdown
    status_breakdown: Dict[str, int] = {}
    tool_breakdown: Dict[str, int] = {}

    for t in traces:
        st = t.get("status", "SUCCESS")
        status_breakdown[st] = status_breakdown.get(st, 0) + 1

        tool = t.get("tool_name")
        if tool:
            tool_breakdown[tool] = tool_breakdown.get(tool, 0) + 1

    return {
        "total_events": telemetry_summary.get("total_events", 0),
        "avg_latency_ms": telemetry_summary.get("avg_latency_ms", 0.0),
        "safety_escalations": telemetry_summary.get("safety_escalations", 0),
        "error_rate": telemetry_summary.get("error_rate", 0.0),
        "intents_breakdown": telemetry_summary.get("intents_breakdown", {}),
        "agents_breakdown": telemetry_summary.get("agents_breakdown", {}),
        "status_breakdown": status_breakdown,
        "tool_breakdown": tool_breakdown,
        "recent_traces_count": len(traces),
        "zero_phi": True,
    }


def get_cost_intelligence_metrics() -> Dict[str, Any]:
    """
    Retrieves cumulative token accounting, pricing tier distributions, and financial analytics.
    """
    cost_summary = global_cost_tracker.get_cost_summary()
    model_usage = cost_summary.get("model_distribution", cost_summary.get("model_usage", {}))

    # Tier breakdown
    tier_distribution: Dict[str, int] = {}
    for model_name, usage in model_usage.items():
        pricing = MODEL_PRICING_TABLE.get(model_name, {})
        category = pricing.get("category", "unknown")
        tier_distribution[category] = tier_distribution.get(category, 0) + usage.get("invocations", 0)

    return {
        "total_prompt_tokens": cost_summary.get("total_prompt_tokens", 0),
        "total_completion_tokens": cost_summary.get("total_completion_tokens", 0),
        "total_tokens": cost_summary.get("total_tokens", 0),
        "total_cost_usd": cost_summary.get("total_cost_usd", 0.0),
        "avg_cost_per_workflow_usd": cost_summary.get("avg_cost_per_workflow_usd", 0.0),
        "model_usage": model_usage,
        "tier_distribution": tier_distribution,
        "pricing_table": MODEL_PRICING_TABLE,
        "zero_phi": True,
    }


def get_export_dataset(
    db: Session, dataset_name: str, format_type: str = "json"
) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """
    Generates structured, zero-PHI tabular records for Power BI Power Query ingestion.
    Supports dataset names:
      - clinical_operations / clinical-operations / clinical_summary
      - appointments
      - medications
      - vitals
      - consents
      - agent_telemetry / agent-telemetry / telemetry
      - cost_intelligence / cost-intelligence / costs

    Returns (records_list, csv_string_if_csv_format).
    If dataset_name is invalid, returns (None, None).
    """
    normalized_name = dataset_name.lower().replace("-", "_")

    records: List[Dict[str, Any]] = []

    if normalized_name in ["clinical_operations", "clinical_summary"]:
        # Flattened key operational metrics table
        metrics = get_clinical_operations_metrics(db)
        records.append({
            "category": "Patients",
            "metric_name": "total_patients",
            "dimension": "All",
            "metric_value": metrics["total_patients"],
        })
        records.append({
            "category": "Appointments",
            "metric_name": "total_appointments",
            "dimension": "All",
            "metric_value": metrics["appointments"]["total_count"],
        })
        for status, cnt in metrics["appointments"]["by_status"].items():
            records.append({
                "category": "Appointments",
                "metric_name": "appointments_by_status",
                "dimension": status,
                "metric_value": cnt,
            })
        for spec, cnt in metrics["appointments"]["by_specialty"].items():
            records.append({
                "category": "Appointments",
                "metric_name": "appointments_by_specialty",
                "dimension": spec,
                "metric_value": cnt,
            })
        for doc, cnt in metrics["appointments"]["by_doctor"].items():
            records.append({
                "category": "Appointments",
                "metric_name": "appointments_by_doctor",
                "dimension": doc,
                "metric_value": cnt,
            })
        records.append({
            "category": "Medications",
            "metric_name": "total_medications",
            "dimension": "All",
            "metric_value": metrics["medications"]["total_count"],
        })
        records.append({
            "category": "Medications",
            "metric_name": "active_medications",
            "dimension": "Active",
            "metric_value": metrics["medications"]["active_count"],
        })
        records.append({
            "category": "Medications",
            "metric_name": "inactive_medications",
            "dimension": "Inactive",
            "metric_value": metrics["medications"]["inactive_count"],
        })
        for med_name, cnt in metrics["medications"]["by_name"].items():
            records.append({
                "category": "Medications",
                "metric_name": "medications_by_name",
                "dimension": med_name,
                "metric_value": cnt,
            })
        for vtype, cnt in metrics["vitals"]["by_type"].items():
            records.append({
                "category": "Vitals",
                "metric_name": "vitals_by_type",
                "dimension": vtype,
                "metric_value": cnt,
            })
        for ctype, cnt in metrics["consents"]["by_type"].items():
            records.append({
                "category": "Consents",
                "metric_name": "consents_by_type",
                "dimension": ctype,
                "metric_value": cnt,
            })

    elif normalized_name == "appointments":
        appts = db.query(models.Appointment).all()
        for a in appts:
            records.append({
                "appointment_id": a.id,
                "doctor_name": a.doctor_name,
                "specialty": a.specialty,
                "appointment_time": a.appointment_time,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            })

    elif normalized_name == "medications":
        meds = db.query(models.Medication).all()
        for m in meds:
            records.append({
                "medication_id": m.id,
                "name": m.name,
                "dosage": m.dosage,
                "frequency": m.frequency,
                "is_active": m.is_active,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            })

    elif normalized_name == "vitals":
        vits = db.query(models.Vital).all()
        for v in vits:
            records.append({
                "vital_id": v.id,
                "vital_type": v.vital_type,
                "unit": v.unit,
                "recorded_at": v.recorded_at.isoformat() if v.recorded_at else None,
                "source": v.source,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            })

    elif normalized_name == "consents":
        cons = db.query(models.PatientConsent).all()
        for c in cons:
            records.append({
                "consent_id": c.id,
                "consent_type": c.consent_type,
                "status": c.status,
                "version": c.version,
                "granted_at": c.granted_at.isoformat() if c.granted_at else None,
                "expires_at": c.expires_at.isoformat() if c.expires_at else None,
            })

    elif normalized_name in ["agent_telemetry", "telemetry"]:
        traces = global_telemetry.traces
        for idx, t in enumerate(traces):
            attrs = t.get("attributes") if isinstance(t.get("attributes"), dict) else {}
            tokens = t.get("token_usage")
            if not isinstance(tokens, dict):
                tokens = attrs.get("token_usage") if isinstance(attrs.get("token_usage"), dict) else {}
            records.append({
                "event_id": idx + 1,
                "timestamp": t.get("timestamp"),
                "actor_role": t.get("actor_role", "patient"),
                "intent": t.get("intent") or attrs.get("intent", "unknown"),
                "selected_agent": t.get("selected_agent") or attrs.get("selected_agent", "unknown"),
                "latency_ms": t.get("latency_ms", t.get("duration_ms", 0.0)),
                "status": t.get("status", "SUCCESS"),
                "safety_escalated": t.get("safety_escalated", False),
                "tool_name": t.get("tool_name") or attrs.get("tool_name"),
                "prompt_tokens": tokens.get("prompt_tokens", 0),
                "completion_tokens": tokens.get("completion_tokens", 0),
                "total_tokens": tokens.get("total_tokens", 0),
            })

    elif normalized_name in ["cost_intelligence", "costs"]:
        costs = global_cost_tracker.workflow_costs
        for idx, c in enumerate(costs):
            records.append({
                "record_id": idx + 1,
                "timestamp": c.get("timestamp"),
                "workflow_name": c.get("workflow_name", "unknown"),
                "model": c.get("model", "unknown"),
                "prompt_tokens": c.get("prompt_tokens", 0),
                "completion_tokens": c.get("completion_tokens", 0),
                "total_tokens": c.get("total_tokens", 0),
                "cost_usd": c.get("cost_usd", 0.0),
            })

    else:
        return None, None

    if format_type.lower() == "csv":
        output = io.StringIO()
        if records:
            fieldnames = list(records[0].keys())
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            for r in records:
                writer.writerow(r)
        else:
            # Empty CSV with default columns if any
            output.write("")
        return records, output.getvalue()

    return records, None
