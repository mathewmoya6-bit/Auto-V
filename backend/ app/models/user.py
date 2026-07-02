# app/models/user.py
from pydantic import BaseModel, EmailStr, Field, validator, root_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import re

# ─── Base Models ──────────────────────────────────────────────────

class UserBase(BaseModel):
    """Base user model with common fields"""
    email: EmailStr
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    phone_number: Optional[str] = Field(None, min_length=10, max_length=15)
    
    @validator('phone_number', always=True)
    def validate_phone(cls, v):
        if v is None or v == '':
            return v
        # Remove any spaces and special characters
        v = re.sub(r'[\s\-\(\)\+]', '', v)
        
        # Check if phone number is valid Kenyan format
        if not v.startswith('254') and not v.startswith('0'):
            # If it starts with 7 or 1, prepend 0
            if v.startswith('7') or v.startswith('1'):
                v = '0' + v
            else:
                raise ValueError('Phone number must start with 254 or 0')
        
        # Ensure minimum length after cleaning
        if len(v) < 10:
            raise ValueError('Phone number must be at least 10 digits')
        
        return v
    
    @root_validator(pre=True)
    def set_full_name(cls, values):
        """Set full_name from first_name and last_name if not provided"""
        if 'full_name' not in values or not values['full_name']:
            first = values.get('first_name', '')
            last = values.get('last_name', '')
            if first or last:
                values['full_name'] = f"{first} {last}".strip()
        return values

# ─── User Creation ──────────────────────────────────────────────────

class UserCreate(UserBase):
    """Model for user registration"""
    password: str = Field(..., min_length=8, max_length=72)
    role: Optional[str] = Field('user', regex='^(user|admin|inspector|super_admin)$')
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        # Check for at least one number and one uppercase letter
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        return v

# ─── User Login ──────────────────────────────────────────────────

class UserLogin(BaseModel):
    """Model for user login"""
    email: EmailStr
    password: str
    
    @validator('email')
    def normalize_email(cls, v):
        return v.lower().strip()

# ─── User Response ──────────────────────────────────────────────────

class UserResponse(BaseModel):
    """Response model for user data"""
    id: str
    email: EmailStr
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str = "user"
    email_verified: bool = False
    phone_number: Optional[str] = None
    is_active: bool = True
    is_first_login: bool = False
    has_vehicle: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

# ─── Token Models ──────────────────────────────────────────────────

class TokenResponse(BaseModel):
    """Response model for authentication tokens"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int = 3600  # 1 hour default
    refresh_expires_in: Optional[int] = 2592000  # 30 days
    
class TokenRefresh(BaseModel):
    """Model for refreshing tokens"""
    refresh_token: str

class TokenData(BaseModel):
    """Internal token data model"""
    user_id: str
    email: str
    role: str
    exp: Optional[int] = None

# ─── User Profile ──────────────────────────────────────────────────

class UserProfile(BaseModel):
    """User profile model with extended information"""
    user_id: str
    profile_picture: Optional[str] = None
    company: Optional[str] = Field(None, max_length=100)
    company_name: Optional[str] = None  # Alias for company
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = 'Kenya'
    postal_code: Optional[str] = None
    preferences: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
    
    @validator('company_name', pre=True, always=True)
    def set_company_name(cls, v, values):
        """Alias for company field"""
        if not v and 'company' in values:
            return values['company']
        return v

class UserProfileUpdate(BaseModel):
    """Model for updating user profile"""
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    phone_number: Optional[str] = None
    company: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    profile_picture: Optional[str] = None

# ─── User Settings ──────────────────────────────────────────────────

class UserSettings(BaseModel):
    """User preferences and settings"""
    email_notifications: bool = True
    sms_notifications: bool = True
    push_notifications: bool = False
    two_factor_auth: bool = False
    language: str = "en"
    currency: str = "KES"
    date_format: str = "DD/MM/YYYY"
    timezone: str = "Africa/Nairobi"
    session_timeout: int = 60  # minutes
    
    # Notification preferences
    email_valuation: bool = True
    email_inspection: bool = True
    email_certificate: bool = True
    email_reminder: bool = True
    
    # Valuation preferences
    default_valuation_type: str = "Market Value"
    depreciation_rate: float = 8.0
    high_mileage_threshold: int = 150000
    
    # Inspection preferences
    default_inspection_type: str = "Pre-Purchase"
    min_tread_depth: float = 1.6
    passing_score: int = 70
    
    # Certificate preferences
    certificate_validity: int = 1  # years
    certificate_prefix: str = "AUTOV"
    include_watermark: bool = False
    
    class Config:
        from_attributes = True
    
    @validator('currency')
    def validate_currency(cls, v):
        valid_currencies = ['KES', 'USD', 'EUR', 'GBP']
        if v not in valid_currencies:
            raise ValueError(f'Currency must be one of: {", ".join(valid_currencies)}')
        return v
    
    @validator('language')
    def validate_language(cls, v):
        valid_languages = ['en', 'sw', 'fr']
        if v not in valid_languages:
            raise ValueError(f'Language must be one of: {", ".join(valid_languages)}')
        return v

class UserSettingsUpdate(BaseModel):
    """Model for updating user settings"""
    email_notifications: Optional[bool] = None
    sms_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    two_factor_auth: Optional[bool] = None
    language: Optional[str] = None
    currency: Optional[str] = None
    date_format: Optional[str] = None
    timezone: Optional[str] = None
    session_timeout: Optional[int] = None
    email_valuation: Optional[bool] = None
    email_inspection: Optional[bool] = None
    email_certificate: Optional[bool] = None
    email_reminder: Optional[bool] = None
    default_valuation_type: Optional[str] = None
    depreciation_rate: Optional[float] = None
    high_mileage_threshold: Optional[int] = None
    default_inspection_type: Optional[str] = None
    min_tread_depth: Optional[float] = None
    passing_score: Optional[int] = None
    certificate_validity: Optional[int] = None
    certificate_prefix: Optional[str] = None
    include_watermark: Optional[bool] = None

# ─── Password Change ──────────────────────────────────────────────────

class PasswordChange(BaseModel):
    """Model for changing password"""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=72)
    confirm_password: str
    
    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        return v
    
    @root_validator
    def check_passwords_match(cls, values):
        if values.get('new_password') != values.get('confirm_password'):
            raise ValueError('New passwords do not match')
        return values

class PasswordResetRequest(BaseModel):
    """Model for requesting password reset"""
    email: EmailStr
    
    @validator('email')
    def normalize_email(cls, v):
        return v.lower().strip()

class PasswordResetConfirm(BaseModel):
    """Model for confirming password reset"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=72)
    confirm_password: str
    
    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        return v
    
    @root_validator
    def check_passwords_match(cls, values):
        if values.get('new_password') != values.get('confirm_password'):
            raise ValueError('New passwords do not match')
        return values

# ─── Email Change ──────────────────────────────────────────────────

class EmailChange(BaseModel):
    """Model for changing email"""
    new_email: EmailStr
    password: str  # Require password confirmation
    
    @validator('new_email')
    def normalize_email(cls, v):
        return v.lower().strip()

class EmailChangeConfirm(BaseModel):
    """Model for confirming email change"""
    token: str

# ─── User Stats ──────────────────────────────────────────────────

class UserStats(BaseModel):
    """User statistics model"""
    total_vehicles: int = 0
    total_valuations: int = 0
    total_inspections: int = 0
    total_certificates: int = 0
    total_payments: int = 0
    total_spent: float = 0.0
    member_since: Optional[datetime] = None
    last_activity: Optional[datetime] = None

# ─── User Activity ──────────────────────────────────────────────────

class UserActivity(BaseModel):
    """User activity log model"""
    id: Optional[str] = None
    user_id: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Dict[str, Any] = {}
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime

# ─── User Export ──────────────────────────────────────────────────

class UserExportData(BaseModel):
    """Model for user data export"""
    user: UserResponse
    profile: Optional[UserProfile] = None
    settings: Optional[UserSettings] = None
    vehicles: List[Dict[str, Any]] = []
    valuations: List[Dict[str, Any]] = []
    inspections: List[Dict[str, Any]] = []
    certificates: List[Dict[str, Any]] = []
    payments: List[Dict[str, Any]] = []
    export_date: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

# ─── Validation Helpers ──────────────────────────────────────────────────

def validate_kenyan_phone(phone: str) -> bool:
    """
    Validate Kenyan phone number format.
    Accepts formats: 0712345678, 254712345678, +254712345678
    """
    if not phone:
        return False
    # Remove spaces and special characters
    cleaned = re.sub(r'[\s\-\(\)\+]', '', phone)
    # Check pattern
    pattern = r'^(?:0|254)?[17]\d{8}$'
    return bool(re.match(pattern, cleaned))

def normalize_kenyan_phone(phone: str) -> str:
    """Normalize Kenyan phone number to 254XXXXXXXXX format"""
    if not phone:
        return phone
    cleaned = re.sub(r'[\s\-\(\)\+]', '', phone)
    if cleaned.startswith('0'):
        cleaned = '254' + cleaned[1:]
    elif not cleaned.startswith('254'):
        cleaned = '254' + cleaned
    return cleaned
