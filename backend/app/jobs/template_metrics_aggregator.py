"""
Aggregate template performance from sentiments + delivery_outcomes.
Updates TemplateRegistry.performance_metrics_json; ranks templates by weighted score.
Run daily or on-demand. Emits no pipeline event (project-agnostic); updates last_template_metrics_updated_at in config.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import (
    ClientSentiment,
    DeliveryOutcome,
    TemplateRegistry,
    AdminConfig,
)

logger = logging.getLogger(__name__)

# Weighted score: sentiment (0-5 scale) + low defects + fast cycle
WEIGHT_SENTIMENT = 0.4
WEIGHT_DEFECTS = 0.35  # lower is better, invert
WEIGHT_CYCLE = 0.25  # lower is better, invert
MAX_CYCLE_DAYS = 30
MAX_DEFECTS = 20


def _sentiment_value(s: ClientSentiment) -> float:
    """Normalize to 0-5 scale: overall_score if set, else rating, else 3."""
    if getattr(s, "overall_score", None) is not None:
        return float(s.overall_score)
    if s.rating is not None:
        return float(s.rating) if s.rating <= 5 else (s.rating / 20.0)  # 0-100 -> 0-5
    return 3.0


def aggregate_template_performance(db: Session | None = None) -> Dict[str, Any]:
    """
    For each template: aggregate sentiments + delivery_outcomes into performance_metrics_json.
    Rank by weighted score. Persist and return summary.
    """
    session = db or SessionLocal()
    close = db is None
    try:
        templates = session.query(TemplateRegistry).filter(TemplateRegistry.is_active == True).all()
        now_iso = datetime.utcnow().isoformat() + "Z"
        updated_count = 0
        for template in templates:
            tid = template.id
            # Sentiments linked to this template (template_registry_id or legacy template_id string)
            sentiments = (
                session.query(ClientSentiment)
                .filter(
                    (ClientSentiment.template_registry_id == tid)
                    | (ClientSentiment.template_id == str(tid))
                )
                .all()
            )
            outcomes = (
                session.query(DeliveryOutcome)
                .filter(DeliveryOutcome.template_registry_id == tid)
                .all()
            )
            # Also outcomes by project that used this template (from contract/onboarding) - we don't have template on outcome from project directly; we have template_registry_id on outcome. So we're good.
            usage_count = len(set(s.project_id for s in sentiments)) + len(set(o.project_id for o in outcomes))
            if usage_count == 0:
                usage_count = len(sentiments) + len(outcomes) or 0
            avg_sentiment = None
            if sentiments:
                vals = [_sentiment_value(s) for s in sentiments]
                avg_sentiment = round(sum(vals) / len(vals), 2)
            avg_cycle_time_days = None
            if outcomes:
                cycles = [o.cycle_time_days for o in outcomes if o.cycle_time_days is not None]
                if cycles:
                    avg_cycle_time_days = round(sum(cycles) / len(cycles), 1)
            avg_defects = None
            if outcomes:
                defects = [o.defect_count for o in outcomes]
                avg_defects = round(sum(defects) / len(defects), 1)
            on_time_count = sum(1 for o in outcomes if o.on_time_delivery is True)
            conversion_proxy = round(on_time_count / len(outcomes), 2) if outcomes else None
            metrics = {
                "usage_count": usage_count,
                "avg_sentiment": avg_sentiment,
                "avg_cycle_time_days": avg_cycle_time_days,
                "avg_defects": avg_defects,
                "conversion_proxy": conversion_proxy,
                "last_updated_at": now_iso,
            }
            # Weighted score for ranking (higher is better)
            score = 0.0
            if avg_sentiment is not None:
                score += WEIGHT_SENTIMENT * (avg_sentiment / 5.0)
            if avg_defects is not None:
                score += WEIGHT_DEFECTS * (1.0 - min(1.0, avg_defects / MAX_DEFECTS))
            if avg_cycle_time_days is not None:
                score += WEIGHT_CYCLE * (1.0 - min(1.0, avg_cycle_time_days / MAX_CYCLE_DAYS))
            if avg_sentiment is None and avg_defects is None and avg_cycle_time_days is None:
                score = 0.5
            metrics["weighted_score"] = round(score, 3)
            template.performance_metrics_json = metrics
            updated_count += 1
        session.commit()
        # Store last run time (no pipeline event - project_id required)
        try:
            row = session.query(AdminConfig).filter(AdminConfig.key == "last_template_metrics_updated_at").first()
            if not row:
                row = AdminConfig(key="last_template_metrics_updated_at", value_json={"updated_at": now_iso})
                session.add(row)
            else:
                row.value_json = {"updated_at": now_iso} if isinstance(row.value_json, dict) else {"updated_at": now_iso}
            session.commit()
        except Exception as e:
            logger.warning("Could not save last_template_metrics_updated_at: %s", e)
            session.rollback()
        return {"status": "ok", "templates_updated": updated_count}
    except Exception as e:
        logger.exception("aggregate_template_performance failed: %s", e)
        if session:
            session.rollback()
        return {"status": "error", "error": str(e)}
    finally:
        if close and session:
            session.close()
