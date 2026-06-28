# app/api/v1/routes/vehicles.py
from fastapi import APIRouter, Depends, HTTPException, status, Request, File, UploadFile
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import json

from app.core.config import settings
from app.core.database import get_db
from app.core.security import JWTBearer
from app.core.logging import get_logger
from app.services.vehicle_service import VehicleService
from app.models.vehicle import VehicleCreate, VehicleUpdate, VehicleResponse

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])
logger = get_logger(__name__)

@router.post("/", response_model=VehicleResponse)
async def create_vehicle(
    vehicle_data: VehicleCreate,
    request: Request,
    token_data: dict = Depends(JWTBearer()),
    db=Depends(get_db)
):
    """Create a new vehicle listing"""
    try:
        user_id = request.state.user_id
        
        # Check if VIN already exists
        existing = db.table('vehicles').select('*').eq('vin', vehicle_data.vin).execute()
        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vehicle with this VIN already exists"
            )
        
        # Auto-fill vehicle details from VIN if enabled
        if settings.FEATURE_VIN_AUTOFILL:
            vehicle_service = VehicleService()
            vin_data = await vehicle_service.decode_vin(vehicle_data.vin)
            if vin_data:
                # Merge auto-filled data
                vehicle_data.model = vehicle_data.model or vin_data.get('model')
                vehicle_data.make = vehicle_data.make or vin_data.get('make')
                vehicle_data.year = vehicle_data.year or vin_data.get('year')
                vehicle_data.engine_type = vehicle_data.engine_type or vin_data.get('engine_type')
        
        # Create vehicle record
        vehicle_id = str(uuid.uuid4())
        vehicle = {
            'id': vehicle_id,
            'user_id': user_id,
            'vin': vehicle_data.vin,
            'make': vehicle_data.make,
            'model': vehicle_data.model,
            'year': vehicle_data.year,
            'color': vehicle_data.color,
            'mileage': vehicle_data.mileage,
            'engine_type': vehicle_data.engine_type,
            'transmission': vehicle_data.transmission,
            'fuel_type': vehicle_data.fuel_type,
            'condition': vehicle_data.condition,
            'description': vehicle_data.description,
            'price': vehicle_data.price,
            'location': vehicle_data.location,
            'status': 'pending',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        # Process images if provided
        if vehicle_data.images:
            vehicle['images'] = vehicle_data.images
        
        result = db.table('vehicles').insert(vehicle).execute()
        
        logger.info(f"Vehicle created: {vehicle_id} by user {user_id}")
        
        return VehicleResponse(**result.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create vehicle error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create vehicle"
        )

@router.get("/{vehicle_id}", response_model=VehicleResponse)
async def get_vehicle(
    vehicle_id: str,
    db=Depends(get_db)
):
    """Get vehicle details by ID"""
    try:
        result = db.table('vehicles').select('*').eq('id', vehicle_id).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehicle not found"
            )
        
        return VehicleResponse(**result.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get vehicle error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get vehicle"
        )

@router.get("/vin/{vin}")
async def get_vehicle_by_vin(
    vin: str,
    db=Depends(get_db)
):
    """Get vehicle by VIN"""
    try:
        result = db.table('vehicles').select('*').eq('vin', vin).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehicle not found"
            )
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get vehicle by VIN error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get vehicle"
        )

@router.put("/{vehicle_id}", response_model=VehicleResponse)
async def update_vehicle(
    vehicle_id: str,
    vehicle_data: VehicleUpdate,
    request: Request,
    token_data: dict = Depends(JWTBearer()),
    db=Depends(get_db)
):
    """Update vehicle details"""
    try:
        user_id = request.state.user_id
        
        # Check vehicle exists and belongs to user
        result = db.table('vehicles').select('*').eq('id', vehicle_id).execute()
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehicle not found"
            )
        
        vehicle = result.data[0]
        
        # Only allow owner or admin to update
        if vehicle['user_id'] != user_id and request.state.user_role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Update vehicle
        update_data = vehicle_data.dict(exclude_unset=True)
        update_data['updated_at'] = datetime.utcnow().isoformat()
        
        result = db.table('vehicles').update(update_data).eq('id', vehicle_id).execute()
        
        logger.info(f"Vehicle updated: {vehicle_id} by user {user_id}")
        
        return VehicleResponse(**result.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update vehicle error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update vehicle"
        )

@router.delete("/{vehicle_id}")
async def delete_vehicle(
    vehicle_id: str,
    request: Request,
    token_data: dict = Depends(JWTBearer()),
    db=Depends(get_db)
):
    """Delete a vehicle"""
    try:
        user_id = request.state.user_id
        
        # Check vehicle exists and belongs to user
        result = db.table('vehicles').select('*').eq('id', vehicle_id).execute()
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehicle not found"
            )
        
        vehicle = result.data[0]
        
        # Only allow owner or admin to delete
        if vehicle['user_id'] != user_id and request.state.user_role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Delete vehicle
        db.table('vehicles').delete().eq('id', vehicle_id).execute()
        
        logger.info(f"Vehicle deleted: {vehicle_id} by user {user_id}")
        
        return {"message": "Vehicle deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete vehicle error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete vehicle"
        )

@router.get("/search")
async def search_vehicles(
    request: Request,
    db=Depends(get_db),
    make: Optional[str] = None,
    model: Optional[str] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    condition: Optional[str] = None,
    location: Optional[str] = None,
    status: Optional[str] = "active",
    limit: int = 20,
    offset: int = 0
):
    """Search for vehicles with filters"""
    try:
        query = db.table('vehicles').select('*')
        
        # Apply filters
        if status:
            query = query.eq('status', status)
        if make:
            query = query.ilike('make', f'%{make}%')
        if model:
            query = query.ilike('model', f'%{model}%')
        if year_min:
            query = query.gte('year', year_min)
        if year_max:
            query = query.lte('year', year_max)
        if price_min:
            query = query.gte('price', price_min)
        if price_max:
            query = query.lte('price', price_max)
        if condition:
            query = query.eq('condition', condition)
        if location:
            query = query.ilike('location', f'%{location}%')
        
        # Get total count
        count_query = db.table('vehicles').select('count', count='exact')
        if status:
            count_query = count_query.eq('status', status)
        total_count = count_query.execute().count
        
        # Get paginated results
        result = query.range(offset, offset + limit).execute()
        
        return {
            'vehicles': result.data,
            'total': total_count,
            'limit': limit,
            'offset': offset
        }
        
    except Exception as e:
        logger.error(f"Search vehicles error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search vehicles"
        )

@router.post("/{vehicle_id}/upload-images")
async def upload_vehicle_images(
    vehicle_id: str,
    request: Request,
    token_data: dict = Depends(JWTBearer()),
    db=Depends(get_db),
    files: List[UploadFile] = File(...)
):
    """Upload images for a vehicle"""
    try:
        user_id = request.state.user_id
        
        # Check vehicle exists and belongs to user
        result = db.table('vehicles').select('*').eq('id', vehicle_id).execute()
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehicle not found"
            )
        
        vehicle = result.data[0]
        
        if vehicle['user_id'] != user_id and request.state.user_role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Validate file sizes
        for file in files:
            if file.size > settings.MAX_IMAGE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Image {file.filename} exceeds maximum size"
                )
        
        # Upload images to storage
        # TODO: Implement image upload to Supabase storage
        image_urls = []
        
        for file in files:
            # Process and upload image
            image_url = f"https://auto-v.meipressgroup.com/images/vehicles/{vehicle_id}/{file.filename}"
            image_urls.append(image_url)
        
        # Update vehicle with image URLs
        update_data = {
            'images': vehicle.get('images', []) + image_urls,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        db.table('vehicles').update(update_data).eq('id', vehicle_id).execute()
        
        return {
            'message': 'Images uploaded successfully',
            'images': image_urls
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload images error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload images"
        )
