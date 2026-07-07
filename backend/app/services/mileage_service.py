# app/services/mileage_service.py
# =============================================================================
# AUTO-V API - Mileage Service
# =============================================================================

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.services.supabase_service import SupabaseService
from app.schemas.mileage import (
    VehicleCategoryCreate,
    VehicleVariantCreate,
    RouteCreate,
    MileageClaimCreate,
)

logger = logging.getLogger(__name__)


class MileageService(SupabaseService):
    """Mileage service for vehicle categories, variants, and claims."""
    
    def __init__(self):
        super().__init__()
    
    # ─── Categories ──────────────────────────────────────────────────
    
    def get_categories(self, active_only: bool = True) -> List[Dict]:
        """Get all vehicle categories."""
        try:
            filters = {"is_active": True} if active_only else {}
            return self.select("vehicle_categories", "*", filters)
        except Exception as e:
            logger.error(f"Error fetching categories: {e}")
            raise
    
    def create_category(self, data: VehicleCategoryCreate) -> Dict:
        """Create a new vehicle category."""
        try:
            category_dict = data.dict()
            category_dict["created_at"] = datetime.utcnow().isoformat()
            return self.insert("vehicle_categories", category_dict)
        except Exception as e:
            logger.error(f"Error creating category: {e}")
            raise
    
    # ─── Variants ────────────────────────────────────────────────────
    
    def get_variants(self, category_id: Optional[str] = None) -> List[Dict]:
        """Get vehicle variants."""
        try:
            filters = {}
            if category_id:
                filters["category_id"] = category_id
            return self.select("vehicle_variants", "*", filters)
        except Exception as e:
            logger.error(f"Error fetching variants: {e}")
            raise
    
    def create_variant(self, data: VehicleVariantCreate) -> Dict:
        """Create a new vehicle variant."""
        try:
            variant_dict = data.dict()
            variant_dict["created_at"] = datetime.utcnow().isoformat()
            return self.insert("vehicle_variants", variant_dict)
        except Exception as e:
            logger.error(f"Error creating variant: {e}")
            raise
    
    # ─── Routes ──────────────────────────────────────────────────────
    
    def get_routes(self, active_only: bool = True) -> List[Dict]:
        """Get all routes."""
        try:
            filters = {"is_active": True} if active_only else {}
            return self.select("routes", "*", filters)
        except Exception as e:
            logger.error(f"Error fetching routes: {e}")
            raise
    
    def create_route(self, data: RouteCreate) -> Dict:
        """Create a new route."""
        try:
            route_dict = data.dict()
            route_dict["created_at"] = datetime.utcnow().isoformat()
            return self.insert("routes", route_dict)
        except Exception as e:
            logger.error(f"Error creating route: {e}")
            raise
    
    # ─── Mileage Claims ─────────────────────────────────────────────
    
    def get_claims(self, user_id: Optional[str] = None) -> List[Dict]:
        """Get mileage claims."""
        try:
            filters = {}
            if user_id:
                filters["user_id"] = user_id
            return self.select("mileage_claims", "*", filters)
        except Exception as e:
            logger.error(f"Error fetching claims: {e}")
            raise
    
    def create_claim(self, data: MileageClaimCreate) -> Dict:
        """Create a new mileage claim."""
        try:
            claim_dict = data.dict()
            claim_dict["created_at"] = datetime.utcnow().isoformat()
            claim_dict["status"] = "pending"
            return self.insert("mileage_claims", claim_dict)
        except Exception as e:
            logger.error(f"Error creating claim: {e}")
            raise
    
    def approve_claim(self, claim_id: str, approver_id: str) -> Dict:
        """Approve a mileage claim."""
        try:
            return self.update(
                "mileage_claims",
                {
                    "status": "approved",
                    "approved_by": approver_id,
                    "approved_at": datetime.utcnow().isoformat()
                },
                {"id": claim_id}
            )
        except Exception as e:
            logger.error(f"Error approving claim: {e}")
            raise


__all__ = ["MileageService"]
