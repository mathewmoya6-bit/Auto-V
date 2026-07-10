# app/services/vehicle_assessment_service.py
"""
Business logic for Vehicle Assessments.

TODO(integration): this service is written to *call into* your existing
modules rather than duplicate their logic:
  - app.services.valuation_service   (or wherever get_vehicle_valuation lives)
  - app.services.inspection_service  (get_vehicle_inspections)
  - app.services.mileage_service     (get_vehicle_mileage)
Replace the `_fetch_*` stubs below with real calls to those services/repos.
"""
from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import Optional

from app.schemas.vehicle_assessment import (
    AssessmentCreate,
    VehicleAssessmentResponse,
    ComponentScore,
    ValuationSnapshot,
    InspectionSnapshot,
    MileageTrendSnapshot,
    ConditionGrade,
)


# --- Data-gathering stubs ---------------------------------------------------

async def _fetch_latest_valuation(db, vehicle_id: UUID) -> Optional[ValuationSnapshot]:
    # TODO(integration): call your Valuation module, e.g.
    # valuation = await valuation_service.get_latest(db, vehicle_id)
    # return ValuationSnapshot(valuation_id=valuation.id, estimated_value=valuation.value, valuation_date=valuation.created_at)
    return None


async def _fetch_latest_inspection(db, vehicle_id: UUID) -> Optional[InspectionSnapshot]:
    # TODO(integration): call your Inspections module, e.g.
    # inspection = await inspection_service.get_latest(db, vehicle_id)
    # return InspectionSnapshot(inspection_id=inspection.id, inspection_date=inspection.created_at, summary=inspection.summary)
    return None


async def _fetch_mileage_trend(db, vehicle_id: UUID) -> Optional[MileageTrendSnapshot]:
    # TODO(integration): call your Mileage module, e.g.
    # entries = await mileage_service.get_vehicle_mileage(db, vehicle_id)
    # compute average_monthly_km / trend classification from entries
    return None


# --- Scoring -----------------------------------------------------------------

def _score_from_inspection(inspection: Optional[InspectionSnapshot]) -> ComponentScore:
    # TODO(integration): derive a real score from inspection findings/checklist
    score = 75.0 if inspection else 60.0
    return ComponentScore(
        category="Inspection Condition",
        score=score,
        weight=0.4,
        notes="Based on latest inspection report." if inspection else "No inspection on file.",
    )


def _score_from_mileage(mileage: Optional[MileageTrendSnapshot]) -> ComponentScore:
    score = 80.0
    notes = "Mileage pattern looks consistent."
    if mileage and mileage.trend == "high_usage":
        score, notes = 55.0, "Higher than average usage detected."
    elif mileage and mileage.trend == "inconsistent":
        score, notes = 40.0, "Mileage records show inconsistencies — verify odometer history."
    return ComponentScore(category="Mileage Consistency", score=score, weight=0.3, notes=notes)


def _score_from_valuation(valuation: Optional[ValuationSnapshot]) -> ComponentScore:
    score = 70.0 if valuation else 50.0
    return ComponentScore(
        category="Market Value",
        score=score,
        weight=0.3,
        notes="Reflects most recent valuation." if valuation else "No valuation on file.",
    )


def _grade_from_score(score: float) -> ConditionGrade:
    if score >= 90:
        return ConditionGrade.excellent
    if score >= 75:
        return ConditionGrade.good
    if score >= 60:
        return ConditionGrade.fair
    if score >= 40:
        return ConditionGrade.poor
    return ConditionGrade.critical


def _recommendations_for(components: list[ComponentScore]) -> list[str]:
    recs = []
    for c in components:
        if c.score < 60:
            recs.append(f"Review {c.category.lower()}: {c.notes}")
    if not recs:
        recs.append("No urgent action items — vehicle is in line with expectations.")
    return recs


# --- Public API ---------------------------------------------------------------

async def create_assessment(
    db, vehicle_id: UUID, payload: AssessmentCreate
) -> VehicleAssessmentResponse:
    valuation = await _fetch_latest_valuation(db, vehicle_id) if payload.include_valuation else None
    inspection = await _fetch_latest_inspection(db, vehicle_id) if payload.include_inspection else None
    mileage = await _fetch_mileage_trend(db, vehicle_id) if payload.include_mileage_trend else None

    components = [
        _score_from_inspection(inspection),
        _score_from_mileage(mileage),
        _score_from_valuation(valuation),
    ]
    overall = sum(c.score * c.weight for c in components) / sum(c.weight for c in components)

    result = VehicleAssessmentResponse(
        id=uuid4(),
        vehicle_id=vehicle_id,
        overall_score=round(overall, 1),
        condition_grade=_grade_from_score(overall),
        component_scores=components,
        valuation_snapshot=valuation,
        inspection_snapshot=inspection,
        mileage_trend_snapshot=mileage,
        recommendations=_recommendations_for(components),
        notes=payload.notes,
        created_at=datetime.now(timezone.utc),
    )

    # TODO(integration): persist `result` to a VehicleAssessment table
    # db.add(VehicleAssessment(**result.model_dump())); await db.commit()

    return result


async def list_assessments(db, vehicle_id: UUID) -> list:
    # TODO(integration): real query, ordered by created_at desc
    return []


async def get_assessment(db, assessment_id: UUID) -> Optional[VehicleAssessmentResponse]:
    # TODO(integration): real lookup
    return None
