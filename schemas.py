"""
Database Schemas for Medi Mitra

Each Pydantic model here represents a MongoDB collection.
Collection name = lowercase of class name (e.g., User -> "user").
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class User(BaseModel):
    name: str
    email: str
    age: Optional[int] = Field(default=None, ge=0, le=120)
    gender: Optional[str] = None
    heightCm: Optional[float] = None
    weightKg: Optional[float] = None
    goals: List[Literal["build_muscle", "fat_loss", "maintenance", "yoga_focus"]] = []

class Fooditem(BaseModel):
    name: str
    calories: float
    macros: dict = Field(default_factory=lambda: {"protein": 0, "carbs": 0, "fat": 0})
    servingSize: str
    tags: List[str] = []

class Meallog(BaseModel):
    userId: str
    date: str  # YYYY-MM-DD
    items: List[dict] = []  # {foodItemId, name, quantity}
    totalCalories: float = 0
    notes: Optional[str] = None

class Activitylog(BaseModel):
    userId: str
    date: str
    activities: List[dict] = []  # {name, durationMin, caloriesBurned}
    notes: Optional[str] = None

class Symptomcheck(BaseModel):
    userId: Optional[str] = None
    inputText: str
    aiFindings: dict
    suggestedLabs: List[str] = []  # lab test ids
    suggestedSpecialties: List[str] = []

class Labtest(BaseModel):
    name: str
    code: str
    category: Optional[str] = None
    description: Optional[str] = None
    sampleType: Optional[str] = None
    price: float = 0
    preparation: Optional[str] = None
    typicalUseCases: List[str] = []
    tags: List[str] = []

class Laborder(BaseModel):
    userId: str
    items: List[dict]  # {labTestId, name, price}
    total: float
    status: Literal["pending", "scheduled", "completed", "cancelled"] = "pending"
    preferredDate: Optional[str] = None
    address: Optional[str] = None

class Doctor(BaseModel):
    name: str
    specialty: str
    yearsExperience: int
    rating: float
    location: str
    availability: List[dict] = []  # {date, times: []}
    bio: Optional[str] = None

class Appointment(BaseModel):
    userId: str
    doctorId: str
    date: str
    time: str
    reason: Optional[str] = None
    status: Literal["scheduled", "completed", "cancelled"] = "scheduled"
    notes: Optional[str] = None
