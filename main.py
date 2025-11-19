import os
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from bson import ObjectId

from database import db, create_document, get_documents

app = FastAPI(title="iBigay API", description="Hyperlocal, zero-waste giving platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------ Utilities ------------------

def serialize_id(value):
    if isinstance(value, ObjectId):
        return str(value)
    return value


def serialize_doc(doc: Dict[str, Any]):
    if not doc:
        return doc
    out = {}
    for k, v in doc.items():
        if k == "_id":
            out["id"] = serialize_id(v)
        elif isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


# ------------------ Models ------------------

class RegisterUserRequest(BaseModel):
    name: str
    email: str
    address: Optional[str] = None
    barangay: Optional[str] = None
    avatar_url: Optional[str] = None


class CreateItemRequest(BaseModel):
    user_id: str
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    photo_url: Optional[str] = None
    expiry_date: Optional[datetime] = None
    location_lat: float
    location_lng: float
    barangay: Optional[str] = None


class ItemsQuery(BaseModel):
    lat: float
    lng: float
    radius_km: float = Field(2.0, description="Search radius in km")


class TipidRequest(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None


class CreateChatRequest(BaseModel):
    item_id: str
    giver_id: str
    receiver_id: str


class SendMessageRequest(BaseModel):
    sender_id: str
    text: str


# ------------------ Root & Health ------------------

@app.get("/")
def read_root():
    return {"message": "iBigay API is running"}


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
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"

    return response


# ------------------ Auth (Simple) ------------------

@app.post("/api/auth/register")
def register_user(req: RegisterUserRequest):
    data = req.model_dump()
    # naive uniqueness check on email
    existing = db["user"].find_one({"email": req.email}) if db else None
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = create_document("user", data)
    return {"id": user_id, **data}


# ------------------ Items ------------------

@app.post("/api/items")
def create_item(req: CreateItemRequest):
    data = req.model_dump()
    item_id = create_document("item", data)
    return {"id": item_id, **data}


def _haversine_km(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, sqrt, atan2
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c


@app.get("/api/items")
def list_items(lat: float, lng: float, radius_km: float = 2.0):
    docs = get_documents("item")
    enriched: List[Dict[str, Any]] = []
    for d in docs:
        d_ser = serialize_doc(d)
        try:
            dist = _haversine_km(lat, lng, float(d_ser.get("location_lat")), float(d_ser.get("location_lng")))
        except Exception:
            dist = 9999
        d_ser["distance_km"] = round(dist, 2)
        if dist <= radius_km and d_ser.get("available", True):
            enriched.append(d_ser)
    # sort by proximity
    enriched.sort(key=lambda x: x.get("distance_km", 9999))
    return enriched


# ------------------ AI: Cen-'tipid' ------------------

def _generate_tipid_suggestions(title: str, description: Optional[str], category: Optional[str]):
    text = f"{title} {description or ''}".lower()
    tips = []
    recipes = []

    def add_tip(t):
        if t not in tips:
            tips.append(t)

    def add_recipe(r):
        if r not in recipes:
            recipes.append(r)

    if "banana" in text:
        add_tip("Freeze overripe bananas for smoothies or baking.")
        add_recipe("Banana Bread na Pang-tipid")
        add_recipe("Smoothie: saging + gatas + yelo")
        add_recipe("Maruya / Banana Fritters")
    if "bread" in text or "tinapay" in text:
        add_tip("Gawing breadcrumbs o croutons ang matigas na tinapay.")
        add_recipe("French Toast / Toasted Bread with itlog")
        add_recipe("Bread Pudding sa Kaldero")
    if "rice" in text or "kanin" in text:
        add_tip("Gawing sinangag ang natirang kanin—perfect for breakfast!")
        add_recipe("Sinangag with Garlic at gulay")
        add_recipe("Arroz Caldo kung sabaw ang hanap")
    if "vegetable" in text or "gulay" in text or "lettuce" in text or "carrot" in text:
        add_tip("Gamitin sa stir-fry o soup ang nalalantang gulay.")
        add_recipe("Gulay Stir-fry na may toyo at bawang")
        add_recipe("Pickled Gulay para tumagal")
    if category == "household":
        add_tip("Repurpose jars/containers for storage.")
        add_tip("Donate locally para hindi mapunta sa landfill.")
    if not tips and not recipes:
        add_tip("Check your fridge first—baka pwedeng i-recipe na! 😄")
        add_recipe("Fried Rice ng Bahay")

    message = {
        "mascot": {
            "name": "Cen-'tipid'",
            "tagline": "Pag 'di na kailangan, wag itapon—I-Bigay o I-kusina!",
        },
        "tips": tips,
        "recipes": recipes
    }
    return message


@app.post("/api/ai/tipid")
def tipid_ai(req: TipidRequest):
    return _generate_tipid_suggestions(req.title, req.description, req.category)


# ------------------ Chat ------------------

@app.post("/api/chats")
def create_chat(req: CreateChatRequest):
    data = req.model_dump()
    chat_id = create_document("chat", {**data, "created_at": datetime.now(timezone.utc)})
    return {"id": chat_id, **data}


@app.get("/api/chats/{chat_id}/messages")
def get_messages(chat_id: str):
    docs = get_documents("message", {"chat_id": chat_id})
    return [serialize_doc(d) for d in docs]


@app.post("/api/chats/{chat_id}/messages")
def send_message(chat_id: str, req: SendMessageRequest):
    data = req.model_dump()
    msg_id = create_document("message", {**data, "chat_id": chat_id})
    return {"id": msg_id, **data, "chat_id": chat_id}


# ------------------ Activity ------------------

@app.get("/api/users/{user_id}/stats")
def user_stats(user_id: str):
    items = get_documents("item", {"user_id": user_id})
    total_items = len(items)
    people_helped = 0
    kg_diverted = 0.0
    for it in items:
        qty = it.get("quantity") or 0
        unit = (it.get("unit") or "").lower()
        if unit in ["kg", "kilo", "kilogram", "kilograms"]:
            kg_diverted += float(qty)
        elif unit in ["g", "gram", "grams"]:
            kg_diverted += float(qty) / 1000.0
        elif unit in ["lb", "lbs", "pound", "pounds"]:
            kg_diverted += float(qty) * 0.453592
        else:
            # heuristic: 0.2kg per piece/pack
            kg_diverted += float(qty) * 0.2
        if it.get("available", True) is False:
            people_helped += 1
    return {
        "items_shared": total_items,
        "people_helped": people_helped,
        "kilograms_diverted": round(kg_diverted, 2)
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
