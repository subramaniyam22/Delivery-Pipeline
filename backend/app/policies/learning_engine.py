"""
Policy learning engine: suggest assignment/quality threshold deltas from delivery outcomes + sentiment (Prompt 9).
Shadow mode: suggestions stored in learning_proposals_json (AdminConfig); never auto-applied.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.models import DeliveryOutcome, ClientSentiment

logger = logging.getLogger(__name__)

LEARNING_PROPOSALS_KEY = "learning_proposals_json"


def compute_learning_proposals(db: Session) -> List[Dict[str, Any]]:
    """
    Compute suggested policy deltas from outcomes + sentiment.
    Returns list of proposals: { policy_key, current_value, suggested_value, rationale }.
    Caller persists to AdminConfig[LEARNING_PROPOSALS_KEY].
    """
    proposals: List[Dict[str, Any]] = []
    outcomes = db.query(DeliveryOutcome).all()
    if not outcomes:
        return proposals
    avg_defects = sum(o.defect_count for o in outcomes) / len(outcomes)
    sentiments = db.query(ClientSentiment).all()
    avg_sentiment = None
    if sentiments:
        vals = []
        for s in sentiments:
            if getattr(s, "overall_score", None) is not None:
                vals.append(float(s.overall_score))
            elif s.rating is not None:
                vals.append(float(s.rating) if s.rating <= 5 else s.rating / 20.0)
        if vals:
            avg_sentiment = sum(vals) / len(vals)
    # If high defect rate -> suggest increasing assignment weight for performance/skill
    if avg_defects and avg_defects > 2.0:
        proposals.append({
            "policy_key": "assignment_engine.WEIGHT_PERFORMANCE",
            "current_value": 0.15,
            "suggested_value": 0.22,
            "rationale": f"Avg defects ({avg_defects:.1f}) is high; increase weight for builder performance/skill in assignment.",
        })
    # If low sentiment -> suggest raising a11y threshold
    if avg_sentiment is not None and avg_sentiment < 3.8:
        proposals.append({
            "policy_key": "global_thresholds_json.lighthouse_min.accessibility",
            "current_value": 0.9,
            "suggested_value": 0.95,
            "rationale": f"Avg sentiment ({avg_sentiment:.2f}) suggests raising accessibility bar for blueprint critic.",
        })
    # Repeated a11y feedback in tags
    a11y_count = 0
    for s in sentiments:
        tags = getattr(s, "tags_json", None) or []
        if isinstance(tags, list) and "accessibility" in tags:
            a11y_count += 1
    if a11y_count >= 3:
        proposals.append({
            "policy_key": "blueprint_critic.a11y_threshold",
            "current_value": 0.9,
            "suggested_value": 0.95,
            "rationale": f"Repeated accessibility feedback ({a11y_count} sentiments); suggest higher a11y threshold.",
        })
    return proposals


def get_learning_proposals(db: Session) -> List[Dict[str, Any]]:
    """Load learning proposals from AdminConfig."""
    from app.models import AdminConfig
    row = db.query(AdminConfig).filter(AdminConfig.key == LEARNING_PROPOSALS_KEY).first()
    if not row or not isinstance(row.value_json, list):
        return []
    return list(row.value_json)


def save_learning_proposals(db: Session, proposals: List[Dict[str, Any]]) -> None:
    """Persist learning proposals to AdminConfig (shadow mode)."""
    from app.models import AdminConfig
    row = db.query(AdminConfig).filter(AdminConfig.key == LEARNING_PROPOSALS_KEY).first()
    if not row:
        row = AdminConfig(key=LEARNING_PROPOSALS_KEY, value_json=proposals)
        db.add(row)
    else:
        row.value_json = proposals
    db.commit()


def run_learning_and_save(db: Session) -> List[Dict[str, Any]]:
    """Compute proposals and save to config; return proposals."""
    proposals = compute_learning_proposals(db)
    save_learning_proposals(db, proposals)
    return proposals
