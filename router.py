# app/api/v1/endpoints/instant_value.py
"""
Instant Value routes.

Public-friendly: estimation works with no auth (lead-gen use case). If a
valid token IS supplied, the estimate is saved to that user's history.

TODO(integration): adjust imports below to match your real project layout:
  - app.api.deps.get_db            -> your DB session dependency
  - app.api.deps.get_current_user_optional -> should return None instead of
    raising 401 when no/invalid token is supplied (add if you don't have one)
  - app.api.deps.get_current_user  -> your existing required-auth dependency
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.instant_value import (
    InstantValueRequest,
    InstantValueResponse,
    InstantValueHistoryItem,
)
from app.services import instant_value_service as service

# from app.api.deps import get_db, get_current_user, get_current_user_optional

router = APIRouter()


@router.post("/estimate", response_model=InstantValueResponse, tags=["Instant Value"])
async def calculate_instant_value(
    payload: InstantValueRequest,
    # db=Depends(get_db),
    # current_user=Depends(get_current_user_optional),
):
    """Calculate an instant value estimate. No auth required.

    If called with a valid bearer token, the estimate is saved to the
    caller's history and `saved=True` is returned.
    """
    result = service.calculate_instant_value(payload)

    # TODO(integration): uncomment once get_current_user_optional exists
    # if current_user:
    #     result = await service.save_estimate(db, current_user.id, payload, result)

    return result


@router.get(
    "/estimate/{estimate_id}",
    response_model=InstantValueResponse,
    tags=["Instant Value"],
)
async def get_instant_value_estimate(
    estimate_id: UUID,
    # db=Depends(get_db),
    # current_user=Depends(get_current_user),
):
    """Retrieve a previously saved instant value estimate (owner only)."""
    # estimate = await service.get_estimate_by_id(db, current_user.id, estimate_id)
    estimate = None
    if estimate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Estimate not found")
    return estimate


@router.get(
    "/history",
    response_model=list[InstantValueHistoryItem],
    tags=["Instant Value"],
)
async def get_instant_value_history(
    # db=Depends(get_db),
    # current_user=Depends(get_current_user),
):
    """List the current user's past instant value estimates."""
    # return await service.list_user_estimates(db, current_user.id)
    return []
