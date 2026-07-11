# app/models/vehicle.py
# =============================================================================
# AUTO-V API - Vehicle Models (Pydantic Native)
# =============================================================================

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, ValidationInfo

# ──────────────────────────────────────────────────────────────────────────
# FALLBACK VEHICLE CATALOG
# Ensures dropdowns are never empty even with empty database
# ──────────────────────────────────────────────────────────────────────────

FALLBACK_VEHICLE_CATALOG: Dict[str, List[str]] = {
    # ===== CARS =====
    "Toyota": ["Corolla", "Axio", "Camry", "RAV4", "Hilux", "Land Cruiser", "Prado", "Fortuner", "Premio", "Allion", 
               "Vitz", "Passo", "Sienta", "Noah", "Voxy", "Hiace", "Yaris", "Avanza", "Harrier", "Fielder"],
    "Honda": ["Civic", "Accord", "CR-V", "Fit", "City", "HR-V", "Odyssey", "Pilot", "Stepwgn", "Freed", "Vezel"],
    "Nissan": ["X-Trail", "Patrol", "Note", "Qashqai", "Navara", "Murano", "Juke", "Leaf", "Sunny", "Pulsar", "Skyline"],
    "BMW": ["3 Series", "5 Series", "7 Series", "X3", "X5", "X1", "1 Series", "X7", "X6", "4 Series", "2 Series"],
    "Mercedes-Benz": ["C-Class", "E-Class", "S-Class", "GLC", "GLE", "GLA", "A-Class", "B-Class", "GLS", "G-Class", "CLA"],
    "Audi": ["A3", "A4", "A6", "Q3", "Q5", "Q7", "TT", "e-tron", "A5", "A7", "Q2", "Q8"],
    "Volkswagen": ["Golf", "Polo", "Passat", "Tiguan", "Touareg", "Jetta", "Beetle", "T-Roc", "Arteon", "ID.4"],
    "Ford": ["Focus", "Fiesta", "Mustang", "Ranger", "Explorer", "Escape", "Transit", "Everest", "EcoSport", "F-150"],
    "Mazda": ["Mazda3", "Mazda6", "CX-5", "CX-3", "MX-5", "Demio", "CX-30", "CX-9", "BT-50"],
    "Subaru": ["Impreza", "Forester", "Outback", "Legacy", "XV", "WRX", "Ascent", "Crosstrek", "BRZ"],
    "Mitsubishi": ["Outlander", "Pajero", "Lancer", "ASX", "Delica", "Minica", "Triton", "Eclipse Cross", "Mirage"],
    "Hyundai": ["i10", "i20", "i30", "Tucson", "Santa Fe", "Palisade", "Kona", "Elantra", "Sonata", "Creta", "Venue"],
    "Kia": ["Picanto", "Rio", "Cerato", "Sportage", "Sorento", "Stinger", "Telluride", "Soul", "Niro", "Carnival"],
    "Suzuki": ["Swift", "Jimny", "Vitara", "Baleno", "S-Cross", "Ignis", "Alto", "Ciaz", "Ertiga", "XL7"],
    "Isuzu": ["D-Max", "MU-X", "Trooper", "N-Series", "F-Series", "Giga", "Elf"],
    "Land Rover": ["Defender", "Discovery", "Range Rover", "Evoque", "Velar", "Sport", "Freelander", "Series"],
    "Jeep": ["Wrangler", "Cherokee", "Compass", "Grand Cherokee", "Renegade", "Gladiator", "Patriot"],
    "Lexus": ["IS", "ES", "LS", "RX", "NX", "UX", "LX", "GX", "RC", "LC", "RZ"],
    "Volvo": ["S60", "S90", "V60", "XC40", "XC60", "XC90", "C40", "EX30", "EX90"],
    "Peugeot": ["208", "308", "508", "2008", "3008", "5008", "Partner", "Rifter", "Traveller"],
    "Daihatsu": ["Terios", "Xenia", "Sirion", "Boon", "Mira", "Move", "Tanto"],
    "Chevrolet": ["Cruze", "Malibu", "Equinox", "Traverse", "Silverado", "Colorado", "Trailblazer", "Camaro"],
    "Chrysler": ["300", "Voyager", "Grand Voyager", "Pacifica", "Aspen"],
    "Dodge": ["Challenger", "Charger", "Durango", "Ram", "Journey", "Avenger"],
    "Mini": ["Cooper", "Countryman", "Clubman", "Convertible", "Coupe", "Roadster"],
    "Porsche": ["911", "Cayenne", "Macan", "Panamera", "Taycan", "Boxster", "Cayman"],
    "Jaguar": ["XE", "XF", "XJ", "F-Pace", "E-Pace", "I-Pace", "X-Type", "S-Type"],
    "Ferrari": ["F8", "SF90", "Portofino", "Roma", "296", "812", "Purosangue"],
    "Lamborghini": ["Huracan", "Aventador", "Urus", "Revuelto", "Countach"],
    "Maserati": ["Ghibli", "Quattroporte", "Levante", "MC20", "GranTurismo"],
    "Alfa Romeo": ["Giulia", "Stelvio", "Tonale", "Giulietta", "MiTo"],
    "Fiat": ["Punto", "500", "Tipo", "Doblo", "Panda", "Uno"],
    "Renault": ["Clio", "Megane", "Captur", "Kadjar", "Trafic", "Kangoo", "Twingo"],
    "Citroën": ["C3", "C4", "Berlingo", "Jumpy", "DS3", "DS4", "C5"],
    "Skoda": ["Octavia", "Superb", "Kodiaq", "Karoq", "Fabia", "Scala"],
    "Seat": ["Ibiza", "Leon", "Ateca", "Arona", "Tarraco"],
    "MG": ["ZS", "HS", "MG5", "MG6", "Cyberster"],
    "Great Wall": ["H6", "H9", "Steed", "Wingle", "C30"],
    "Proton": ["Saga", "Persona", "X70", "X50", "Iriz"],
    "Perodua": ["Myvi", "Axia", "Bezza", "Alza", "Kancil"],
    "Datsun": ["Go", "Go+", "redi-Go", "mii"],
    
    # ===== BIKES =====
    "Honda": ["CBR 250", "CBR 500", "CBR 650", "CB 150", "CB 500", "Africa Twin", "CRF 250", "CRF 450", 
              "Gold Wing", "Shadow", "Rebel", "NC 750", "X-ADV", "Forza", "PCX", "Super Cub"],
    "Yamaha": ["R1", "R6", "R3", "MT-07", "MT-09", "MT-15", "YZF 450", "Tracer 900", "VMAX", "Bolt", 
               "XSR700", "XSR900", "Ténéré 700", "NMAX", "Aerox", "FZ"],
    "Suzuki": ["GSX-R1000", "GSX-R750", "GSX-8S", "Hayabusa", "V-Strom 650", "V-Strom 1000", "SV650", 
               "GSX-S750", "Burgman", "Address", "Gixxer"],
    "Kawasaki": ["Ninja 250", "Ninja 400", "Ninja 650", "Ninja ZX-6R", "Ninja ZX-10R", "Z900", "Z650", 
                 "Versys 650", "Versys 1000", "KX 450", "Vulcan 900", "KLR 650", "Eliminator"],
    "KTM": ["Duke 200", "Duke 390", "Duke 790", "Duke 890", "RC 390", "890 Adventure", "1290 Super Adventure", 
            "690 Enduro", "450 EXC", "350 EXC", "Freeride"],
    "Ducati": ["Panigale V4", "Panigale 959", "Monster 821", "Monster 1200", "Scrambler", "Multistrada 950", 
               "Multistrada 1260", "Diavel", "XDiavel", "Streetfighter", "Supersport", "DesertX"],
    "Triumph": ["Street Triple", "Tiger 900", "Tiger 1200", "Bonneville", "Speed Twin", "Rocket 3", "Speed Triple",
                "Scrambler", "Thruxton", "Trident", "Trophy"],
    "Harley-Davidson": ["Street 750", "Iron 883", "Forty-Eight", "Softail", "Road King", "Street Glide", 
                        "Road Glide", "Pan America", "LiveWire", "Sportster", "Fat Boy"],
    "Royal Enfield": ["Bullet 350", "Classic 350", "Classic 500", "Himalayan", "Interceptor 650", "GT 650", 
                      "Meteor 350", "Scram 411", "Shotgun 650", "Super Meteor"],
    "Bajaj": ["Pulsar 150", "Pulsar 180", "Pulsar 200", "Pulsar NS 200", "Dominar 400", "Avenger 160", "Avenger 220",
              "Cheetak", "Platina", "Discover"],
    "TVS": ["Apache RTR 160", "Apache RTR 200", "Apache RR 310", "Star City", "Jupiter", "Ntorq", "Radeon", "Sport"],
    "Hero MotoCorp": ["Splendor", "Passion Pro", "Glamour", "Karizma", "XPulse 200", "Maverick", "Destini", "Pleasure"],
    "BMW Motorrad": ["R 1250 GS", "R 1250 RT", "S 1000 RR", "F 900 R", "K 1600 GT", "G 310 R", "G 310 GS", 
                     "R nineT", "C 400 GT", "CE 04"],
    "Aprilia": ["RSV4", "Tuono V4", "RS 660", "Tuono 660", "RS 125", "Tuono 125", "Shiver", "Dorsoduro", "SX 125"],
    "MV Agusta": ["F3 800", "F4 1000", "Brutale 800", "Brutale 1000", "Dragster 800", "Turismo Veloce", "Rush", "Superveloce"],
    "Vespa": ["Primavera", "Sprint", "GTS", "946", "Elettrica", "LX", "LXV"],
    "Lambretta": ["G350", "V125", "X125", "LN125", "G325"],
    "Benelli": ["Leoncino", "TRK 502", "Imperiale", "BN 600", "302R", "502C", "752S"],
    "Husqvarna": ["Vitpilen", "Svartpilen", "TE", "FE", "FC", "FS", "701", "901"],
    "Moto Guzzi": ["V7", "V85", "V100", "California", "Breva", "Nevada", "Griso"],
    "Indian": ["Scout", "Chief", "Challenger", "Roadmaster", "FTR", "Springfield", "Dark Horse"],
    
    # ===== TRICYCLES =====
    "Piaggio": ["Ape City", "Ape Cargo", "Ape Calessino", "Ape 50", "Ape TM", "Porter"],
    "Bajaj": ["RE 4S", "RE Compact", "RE Cargo", "RE CNG", "RE Electric", "RE Maxima"],
    "TVS": ["King", "King DLX", "King Cargo", "King CNG", "King Electric"],
    "Mahindra": ["Alfa", "Alfa Plus", "Alfa DX", "Alfa HD"],
    "Atul Auto": ["Gemini", "Shakti", "GT", "Gemini Cargo"],
    
    "Other": ["Other"]
}

# ──────────────────────────────────────────────────────────────────────────
# BIKE MAKE NAME MAPPING
# ──────────────────────────────────────────────────────────────────────────

BIKE_MAKE_MAP: Dict[str, str] = {
    "Honda": "Honda",
    "Yamaha": "Yamaha",
    "Suzuki": "Suzuki",
    "Kawasaki": "Kawasaki",
    "KTM": "KTM",
    "Ducati": "Ducati",
    "Triumph": "Triumph",
    "Royal Enfield": "Royal Enfield",
    "Bajaj": "Bajaj",
    "TVS": "TVS",
    "Hero": "Hero MotoCorp",
    "Harley Davidson": "Harley-Davidson",
    "BMW Motorrad": "BMW Motorrad",
    "Aprilia": "Aprilia",
    "MV Agusta": "MV Agusta",
    "Vespa": "Vespa",
    "Lambretta": "Lambretta",
    "Benelli": "Benelli",
    "Husqvarna": "Husqvarna",
    "Moto Guzzi": "Moto Guzzi",
    "Indian": "Indian",
}

# ──────────────────────────────────────────────────────────────────────────
# VEHICLE IMAGE MODEL
# ──────────────────────────────────────────────────────────────────────────

class VehicleImage(BaseModel):
    """Model for vehicle images"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    vehicle_id: uuid.UUID
    image_url: str
    is_primary: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────────────────────────────
# VIN SCAN MODEL
# ──────────────────────────────────────────────────────────────────────────

class VINScan(BaseModel):
    """Model for VIN scan records"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    vin: str = Field(..., min_length=17, max_length=17, description="17-character VIN")
    raw_response: Optional[Dict[str, Any]] = None
    status: str = "pending"  # pending, success, failed
    
    @field_validator('vin')
    @classmethod
    def validate_vin(cls, v: str) -> str:
        """Validate VIN format"""
        v = v.upper().strip()
        if len(v) != 17:
            raise ValueError("VIN must be exactly 17 characters")
        # Check for invalid characters (I, O, Q are not allowed in VIN)
        invalid_chars = ['I', 'O', 'Q']
        for char in invalid_chars:
            if char in v:
                raise ValueError(f"VIN contains invalid character: {char}")
        return v
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status value"""
        allowed = ['pending', 'success', 'failed', 'processing']
        if v not in allowed:
            raise ValueError(f"Status must be one of: {', '.join(allowed)}")
        return v
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────────────────────────────
# VEHICLE MODEL
# ──────────────────────────────────────────────────────────────────────────

class Vehicle(BaseModel):
    """Main vehicle model for registered vehicles"""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    user_id: uuid.UUID
    make: str = Field(..., min_length=1, max_length=100)
    model: str = Field(..., min_length=1, max_length=100)
    year: int = Field(..., ge=1900, le=2025)
    license_plate: str = Field(..., min_length=3, max_length=20)
    vin: Optional[str] = Field(None, min_length=17, max_length=17)
    color: Optional[str] = Field(None, max_length=50)
    current_odometer: float = Field(0.0, ge=0)
    status: str = "active"
    vehicle_type: Optional[str] = Field(None, description="Car, Bike, or Tricycle")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # ─── Validators ──────────────────────────────────────────────────────

    @field_validator('make')
    @classmethod
    def validate_make(cls, v: str) -> str:
        """Validate and normalize make name"""
        v = v.strip()
        if not v:
            raise ValueError("Make cannot be empty")
        return v

    @field_validator('model')
    @classmethod
    def validate_model(cls, v: str) -> str:
        """Validate and normalize model name"""
        v = v.strip()
        if not v:
            raise ValueError("Model cannot be empty")
        return v

    @field_validator('year')
    @classmethod
    def validate_year(cls, v: int, info: ValidationInfo) -> int:
        """Validate year is reasonable"""
        if v < 1900:
            raise ValueError("Year must be 1900 or later")
        if v > 2025:
            raise ValueError("Year cannot be in the future (max 2025)")
        return v

    @field_validator('license_plate')
    @classmethod
    def validate_license_plate(cls, v: str) -> str:
        """Validate and normalize license plate"""
        v = v.upper().strip()
        if len(v) < 3:
            raise ValueError("License plate is too short")
        return v

    @field_validator('vin')
    @classmethod
    def validate_vin_optional(cls, v: Optional[str]) -> Optional[str]:
        """Validate VIN if provided"""
        if v is None:
            return None
        v = v.upper().strip()
        if len(v) != 17:
            raise ValueError("VIN must be exactly 17 characters")
        invalid_chars = ['I', 'O', 'Q']
        for char in invalid_chars:
            if char in v:
                raise ValueError(f"VIN contains invalid character: {char}")
        return v

    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status value"""
        allowed = ['active', 'inactive', 'sold', 'scrapped', 'pending']
        if v not in allowed:
            raise ValueError(f"Status must be one of: {', '.join(allowed)}")
        return v

    @field_validator('vehicle_type')
    @classmethod
    def validate_vehicle_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate vehicle type"""
        if v is None:
            return None
        allowed = ['Car', 'Bike', 'Tricycle']
        if v not in allowed:
            raise ValueError(f"Vehicle type must be one of: {', '.join(allowed)}")
        return v

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────────────────────────────
# VEHICLE CREATE / UPDATE SCHEMAS
# ──────────────────────────────────────────────────────────────────────────

class VehicleCreate(BaseModel):
    """Schema for creating a new vehicle"""
    make: str = Field(..., min_length=1, max_length=100)
    model: str = Field(..., min_length=1, max_length=100)
    year: int = Field(..., ge=1900, le=2025)
    license_plate: str = Field(..., min_length=3, max_length=20)
    vin: Optional[str] = Field(None, min_length=17, max_length=17)
    color: Optional[str] = Field(None, max_length=50)
    current_odometer: float = Field(0.0, ge=0)
    vehicle_type: Optional[str] = Field(None, description="Car, Bike, or Tricycle")

    @field_validator('make')
    @classmethod
    def validate_make(cls, v: str) -> str:
        return v.strip()

    @field_validator('model')
    @classmethod
    def validate_model(cls, v: str) -> str:
        return v.strip()

    @field_validator('license_plate')
    @classmethod
    def validate_license_plate(cls, v: str) -> str:
        return v.upper().strip()


class VehicleUpdate(BaseModel):
    """Schema for updating an existing vehicle"""
    make: Optional[str] = Field(None, min_length=1, max_length=100)
    model: Optional[str] = Field(None, min_length=1, max_length=100)
    year: Optional[int] = Field(None, ge=1900, le=2025)
    license_plate: Optional[str] = Field(None, min_length=3, max_length=20)
    vin: Optional[str] = Field(None, min_length=17, max_length=17)
    color: Optional[str] = Field(None, max_length=50)
    current_odometer: Optional[float] = Field(None, ge=0)
    status: Optional[str] = None
    vehicle_type: Optional[str] = Field(None, description="Car, Bike, or Tricycle")

    @field_validator('status')
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        allowed = ['active', 'inactive', 'sold', 'scrapped', 'pending']
        if v not in allowed:
            raise ValueError(f"Status must be one of: {', '.join(allowed)}")
        return v


# ──────────────────────────────────────────────────────────────────────────
# RESPONSE MODELS
# ──────────────────────────────────────────────────────────────────────────

class VehicleResponse(BaseModel):
    """Response schema for vehicle data"""
    id: uuid.UUID
    user_id: uuid.UUID
    make: str
    model: str
    year: int
    license_plate: str
    vin: Optional[str]
    color: Optional[str]
    current_odometer: float
    status: str
    vehicle_type: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VehicleDetailResponse(VehicleResponse):
    """Detailed vehicle response with additional info"""
    images: List[VehicleImage] = Field(default_factory=list)
    category: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────
# VEHICLE CATALOG FUNCTIONS
# ──────────────────────────────────────────────────────────────────────────

def get_vehicle_catalog() -> Dict[str, List[str]]:
    """Get the complete vehicle catalog (fallback + any dynamic updates)"""
    return FALLBACK_VEHICLE_CATALOG


def get_makes_by_type(vehicle_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get all makes, optionally filtered by vehicle type.
    Returns list of {make: str, models: List[str], model_count: int}
    """
    catalog = get_vehicle_catalog()
    
    # If no type filter, return all makes
    if not vehicle_type:
        return [
            {"make": make, "models": models, "model_count": len(models)}
            for make, models in sorted(catalog.items())
        ]
    
    # Filter by vehicle type (simplified - assumes make names indicate type)
    # In production, you'd have a proper mapping table
    type_keywords = {
        "Car": ["Toyota", "Honda", "Nissan", "BMW", "Mercedes", "Audi", "Volkswagen", "Ford", 
                "Mazda", "Subaru", "Mitsubishi", "Hyundai", "Kia", "Suzuki", "Isuzu", "Land Rover", 
                "Jeep", "Lexus", "Volvo", "Peugeot", "Daihatsu", "Chevrolet", "Chrysler", "Dodge", 
                "Mini", "Porsche", "Jaguar", "Ferrari", "Lamborghini", "Maserati", "Alfa Romeo", 
                "Fiat", "Renault", "Citroën", "Skoda", "Seat", "MG", "Great Wall", "Proton", "Perodua", "Datsun"],
        "Bike": ["Honda", "Yamaha", "Suzuki", "Kawasaki", "KTM", "Ducati", "Triumph", "Harley-Davidson", 
                 "Royal Enfield", "Bajaj", "TVS", "Hero MotoCorp", "BMW Motorrad", "Aprilia", "MV Agusta", 
                 "Vespa", "Lambretta", "Benelli", "Husqvarna", "Moto Guzzi", "Indian"],
        "Tricycle": ["Piaggio", "Bajaj", "TVS", "Mahindra", "Atul Auto"]
    }
    
    # Get makes for the specified type
    valid_makes = type_keywords.get(vehicle_type, [])
    
    result = []
    for make, models in sorted(catalog.items()):
        # Check if make belongs to this type (or is "Other")
        if make in valid_makes or make == "Other":
            result.append({"make": make, "models": models, "model_count": len(models)})
    
    return result


def get_models_by_make(make: str) -> List[str]:
    """Get all models for a specific make"""
    catalog = get_vehicle_catalog()
    return catalog.get(make, [])


def search_vehicles(query: str, limit: int = 20) -> List[Dict[str, str]]:
    """Search for makes and models matching the query"""
    query_lower = query.lower()
    results = []
    seen = set()
    
    for make, models in get_vehicle_catalog().items():
        # Check if make matches
        if query_lower in make.lower():
            for model in models:
                key = f"{make}|{model}"
                if key not in seen and len(results) < limit:
                    seen.add(key)
                    results.append({"make": make, "model": model})
        
        # Check if any model matches
        if len(results) < limit:
            for model in models:
                if query_lower in model.lower():
                    key = f"{make}|{model}"
                    if key not in seen:
                        seen.add(key)
                        results.append({"make": make, "model": model})
                        if len(results) >= limit:
                            break
    
    return results
