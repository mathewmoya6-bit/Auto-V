# app/services/vehicle_service.py
# =============================================================================
# AUTO-V API - Vehicle Service
# =============================================================================

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.services.supabase_service import SupabaseService
from app.schemas.vehicle import VehicleCreate, VehicleUpdate

logger = logging.getLogger(__name__)


class VehicleService(SupabaseService):
    """Vehicle service for CRUD operations."""
    
    def __init__(self):
        super().__init__()
    
    def get_vehicles(self, user_id: Optional[str] = None) -> List[Dict]:
        """Get all vehicles."""
        try:
            filters = {}
            if user_id:
                filters["user_id"] = user_id
            return self.select("vehicles", "*", filters)
        except Exception as e:
            logger.error(f"Error fetching vehicles: {e}")
            raise
    
    def get_vehicle(self, vehicle_id: str) -> Optional[Dict]:
        """Get a single vehicle by ID."""
        try:
            return self.select_one("vehicles", {"id": vehicle_id})
        except Exception as e:
            logger.error(f"Error fetching vehicle {vehicle_id}: {e}")
            raise
    
    def create_vehicle(self, data: VehicleCreate) -> Dict:
        """Create a new vehicle."""
        try:
            vehicle_dict = data.dict()
            vehicle_dict["created_at"] = datetime.utcnow().isoformat()
            vehicle_dict["updated_at"] = datetime.utcnow().isoformat()
            return self.insert("vehicles", vehicle_dict)
        except Exception as e:
            logger.error(f"Error creating vehicle: {e}")
            raise
    
    def update_vehicle(self, vehicle_id: str, data: VehicleUpdate) -> Dict:
        """Update a vehicle."""
        try:
            update_dict = data.dict(exclude_unset=True)
            update_dict["updated_at"] = datetime.utcnow().isoformat()
            return self.update("vehicles", update_dict, {"id": vehicle_id})
        except Exception as e:
            logger.error(f"Error updating vehicle {vehicle_id}: {e}")
            raise
    
    def delete_vehicle(self, vehicle_id: str) -> bool:
        """Delete a vehicle."""
        try:
            return self.delete("vehicles", {"id": vehicle_id})
        except Exception as e:
            logger.error(f"Error deleting vehicle {vehicle_id}: {e}")
            raise


__all__ = ["VehicleService"]
