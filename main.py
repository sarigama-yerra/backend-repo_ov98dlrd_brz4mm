import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Database helpers (MongoDB)
from database import db, create_document, get_documents

app = FastAPI(title="Medi Mitra API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Models for request validation
# -----------------------------
class MealItem(BaseModel):
    foodItemId: Optional[str] = None
    name: str
    quantity: float = 1
    calories: Optional[float] = None

class MealLogIn(BaseModel):
    userId: Optional[str] = None
    date: str
    items: List[MealItem]
    notes: Optional[str] = None

class ActivityItem(BaseModel):
    name: str
    durationMin: float
    caloriesBurned: Optional[float] = None

class ActivityLogIn(BaseModel):
    userId: Optional[str] = None
    date: str
    activities: List[ActivityItem]
    notes: Optional[str] = None

class SymptomCheckIn(BaseModel):
    text: str
    userId: Optional[str] = None

class LabOrderItem(BaseModel):
    labTestId: Optional[str] = None
    name: str
    price: float

class LabOrderIn(BaseModel):
    userId: Optional[str] = None
    items: List[LabOrderItem]
    preferredDate: Optional[str] = None
    address: Optional[str] = None

class AppointmentIn(BaseModel):
    userId: Optional[str] = None
    doctorId: str
    date: str
    time: str
    reason: Optional[str] = None

# -----------------------------
# Health
# -----------------------------
@app.get("/api/health")
def health():
    return {"ok": True}

# -----------------------------
# Lifestyle: foods, meals, activities
# -----------------------------
# Simple catalog of foods (seed-like). In a full app, these would be in DB.
FOODS = [
    {"id": "f1", "name": "Boiled Egg", "calories": 78, "macros": {"protein": 6, "carbs": 0.6, "fat": 5}, "servingSize": "1 egg"},
    {"id": "f2", "name": "Grilled Chicken Breast (100g)", "calories": 165, "macros": {"protein": 31, "carbs": 0, "fat": 3.6}, "servingSize": "100 g"},
    {"id": "f3", "name": "Brown Rice (1 cup)", "calories": 216, "macros": {"protein": 5, "carbs": 45, "fat": 1.8}, "servingSize": "1 cup cooked"},
    {"id": "f4", "name": "Greek Yogurt (170g)", "calories": 100, "macros": {"protein": 17, "carbs": 6, "fat": 0}, "servingSize": "170 g"},
    {"id": "f5", "name": "Banana (medium)", "calories": 105, "macros": {"protein": 1.3, "carbs": 27, "fat": 0.3}, "servingSize": "1 medium"},
]

@app.get("/api/lifestyle/foods")
def list_foods(search: str = "", page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=50)):
    data = [f for f in FOODS if search.lower() in f["name"].lower()]
    total = len(data)
    start = (page - 1) * page_size
    end = start + page_size
    return {"items": data[start:end], "page": page, "pageSize": page_size, "total": total}

@app.post("/api/lifestyle/meals")
def add_meal_log(payload: MealLogIn):
    total_cal = 0.0
    items = []
    for it in payload.items:
        cals = it.calories if it.calories is not None else 0
        total_cal += cals * (it.quantity or 1)
        items.append({"foodItemId": it.foodItemId, "name": it.name, "quantity": it.quantity, "calories": cals})
    doc = {
        "userId": payload.userId,
        "date": payload.date,
        "items": items,
        "totalCalories": round(total_cal, 2),
        "notes": payload.notes,
    }
    inserted_id = create_document("meallog", doc)
    return {"id": inserted_id, **doc}

@app.get("/api/lifestyle/meals")
def get_meal_logs(userId: Optional[str] = None, date: Optional[str] = None):
    filt = {}
    if userId:
        filt["userId"] = userId
    if date:
        filt["date"] = date
    docs = get_documents("meallog", filt)
    # Convert ObjectId to string where present
    for d in docs:
        if "_id" in d:
            d["id"] = str(d.pop("_id"))
    return {"items": docs}

@app.post("/api/lifestyle/activities")
def add_activity_log(payload: ActivityLogIn):
    total_burn = 0.0
    activities = []
    for a in payload.activities:
        burn = a.caloriesBurned if a.caloriesBurned is not None else (a.durationMin * 5)  # naive estimate
        total_burn += burn
        activities.append({"name": a.name, "durationMin": a.durationMin, "caloriesBurned": burn})
    doc = {
        "userId": payload.userId,
        "date": payload.date,
        "activities": activities,
        "totalBurned": round(total_burn, 2),
        "notes": payload.notes,
    }
    inserted_id = create_document("activitylog", doc)
    return {"id": inserted_id, **doc}

# -----------------------------
# Symptom checker (rule-based mock resembling AI)
# -----------------------------
@app.post("/api/symptom/check")
def symptom_check(payload: SymptomCheckIn):
    text = payload.text.lower()
    severity = "low"
    probable = []
    advice = []
    suggested_labs = []
    suggested_specialties = []

    if any(k in text for k in ["chest pain", "severe", "faint", "blood in stool", "unconscious"]):
        severity = "high"
    elif any(k in text for k in ["fever", "persistent", "worsening", "shortness of breath"]):
        severity = "moderate"
    elif any(k in text for k in ["cold", "cough", "sore throat", "headache", "fatigue"]):
        severity = "low"
    else:
        severity = "unclear"

    if "fever" in text:
        probable.append({"name": "Viral fever", "confidence": 0.6})
        advice.extend(["Hydrate well", "Paracetamol if needed", "Rest"]) 
    if "cough" in text:
        probable.append({"name": "Upper respiratory infection", "confidence": 0.55})
        advice.extend(["Warm fluids", "Steam inhalation"]) 
    if "chest" in text:
        probable.append({"name": "Cardiac or musculoskeletal cause", "confidence": 0.4})
        suggested_specialties.append("Cardiology")
        suggested_labs.extend(["ECG", "Troponin T/I"])

    if severity in ["high", "unclear"]:
        suggested_labs = list(set(suggested_labs + ["CBC", "CRP"]))
        if not suggested_specialties:
            suggested_specialties.append("General Medicine")

    record = {
        "userId": payload.userId,
        "inputText": payload.text,
        "aiFindings": {"severity": severity, "probableConditions": probable, "advice": advice},
        "suggestedLabs": suggested_labs,
        "suggestedSpecialties": suggested_specialties,
    }
    try:
        _id = create_document("symptomcheck", record)
        record["id"] = _id
    except Exception:
        # database may be unavailable; still return response
        pass

    # Map suggested labs to known tests list (below)
    mapped = []
    for name in suggested_labs:
        m = next((t for t in LAB_TESTS if t["name"].lower() == name.lower() or t.get("code", "").lower() == name.lower()), None)
        if m:
            mapped.append(m)
    return {"result": record, "mappedLabs": mapped}

# -----------------------------
# Labs
# -----------------------------
LAB_TESTS = [
    {"id": "lt1", "code": "CBC", "name": "Complete Blood Count", "category": "Hematology", "price": 300, "description": "Measures blood components.", "sampleType": "Blood"},
    {"id": "lt2", "code": "LIPID", "name": "Lipid Profile", "category": "Biochemistry", "price": 700, "description": "Cholesterol panel.", "sampleType": "Blood"},
    {"id": "lt3", "code": "HBA1C", "name": "HbA1c", "category": "Diabetes", "price": 500, "description": "Avg blood glucose (3 months).", "sampleType": "Blood"},
    {"id": "lt4", "code": "TSH", "name": "Thyroid TSH", "category": "Hormone", "price": 450, "description": "Thyroid stimulating hormone.", "sampleType": "Blood"},
]

@app.get("/api/labs/tests")
def list_lab_tests(search: str = "", category: str = "", page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=50)):
    data = [t for t in LAB_TESTS if search.lower() in t["name"].lower() and (category.lower() in t["category"].lower() if category else True)]
    total = len(data)
    start = (page - 1) * page_size
    end = start + page_size
    return {"items": data[start:end], "page": page, "pageSize": page_size, "total": total}

@app.post("/api/labs/orders")
def create_lab_order(payload: LabOrderIn):
    total = sum(i.price for i in payload.items)
    order = {
        "userId": payload.userId,
        "items": [i.model_dump() for i in payload.items],
        "total": total,
        "status": "pending",
        "preferredDate": payload.preferredDate,
        "address": payload.address,
    }
    inserted_id = create_document("laborder", order)
    return {"id": inserted_id, **order}

@app.get("/api/labs/orders")
def list_lab_orders(userId: Optional[str] = None):
    filt = {"userId": userId} if userId else {}
    docs = get_documents("laborder", filt)
    for d in docs:
        if "_id" in d:
            d["id"] = str(d.pop("_id"))
    return {"items": docs}

# -----------------------------
# Doctors & Appointments
# -----------------------------
DOCTORS = [
    {"id": "d1", "name": "Dr. Ananya Gupta", "specialty": "General Medicine", "yearsExperience": 10, "rating": 4.7, "location": "Mumbai", "availability": [{"date": "2025-11-20", "times": ["10:00", "11:00", "15:00"]}], "bio": "MBBS, MD - General Physician"},
    {"id": "d2", "name": "Dr. Rahul Mehta", "specialty": "Cardiology", "yearsExperience": 12, "rating": 4.8, "location": "Delhi", "availability": [{"date": "2025-11-21", "times": ["09:30", "14:00"]}], "bio": "MD, DM - Cardiology"},
    {"id": "d3", "name": "Dr. Priya Nair", "specialty": "Dermatology", "yearsExperience": 8, "rating": 4.6, "location": "Bengaluru", "availability": [{"date": "2025-11-19", "times": ["12:00", "16:00"]}], "bio": "MD - Dermatology"},
]

@app.get("/api/doctors")
def list_doctors(specialty: str = "", search: str = "", page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=50)):
    data = [d for d in DOCTORS if (specialty.lower() in d["specialty"].lower() if specialty else True) and (search.lower() in (d["name"].lower() + d["specialty"].lower()))]
    total = len(data)
    start = (page - 1) * page_size
    end = start + page_size
    return {"items": data[start:end], "page": page, "pageSize": page_size, "total": total}

@app.post("/api/doctors/appointments")
def create_appointment(payload: AppointmentIn):
    doc = payload.model_dump()
    doc["status"] = "scheduled"
    inserted_id = create_document("appointment", doc)
    return {"id": inserted_id, **doc}

@app.get("/api/doctors/appointments")
def list_appointments(userId: Optional[str] = None):
    filt = {"userId": userId} if userId else {}
    docs = get_documents("appointment", filt)
    for d in docs:
        if "_id" in d:
            d["id"] = str(d.pop("_id"))
    return {"items": docs}

# -----------------------------
# Root and test
# -----------------------------
@app.get("/")
def read_root():
    return {"message": "Medi Mitra API running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
                response["connection_status"] = "Connected"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
