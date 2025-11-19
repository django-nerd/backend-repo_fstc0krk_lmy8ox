"""
Database Schemas for iBigay

Each Pydantic model represents a MongoDB collection. The collection name is the lowercase of the class name.
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

class User(BaseModel):
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: Optional[str] = Field(None, description="Street address")
    barangay: Optional[str] = Field(None, description="Barangay or neighborhood")
    avatar_url: Optional[str] = Field(None, description="Profile image")
    is_active: bool = Field(True)

class Item(BaseModel):
    user_id: str = Field(..., description="Owner user id")
    title: str = Field(..., description="Short title, e.g., 'Bananas (ripe)'")
    description: Optional[str] = Field(None, description="Description of the item")
    category: Optional[str] = Field(None, description="food | household | other")
    quantity: Optional[float] = Field(None, description="Quantity amount")
    unit: Optional[str] = Field(None, description="pcs | kg | L | pack ...")
    photo_url: Optional[str] = Field(None)
    expiry_date: Optional[datetime] = Field(None)
    location_lat: float = Field(..., description="Latitude")
    location_lng: float = Field(..., description="Longitude")
    barangay: Optional[str] = Field(None)
    available: bool = Field(True)

class Chat(BaseModel):
    item_id: str = Field(...)
    giver_id: str = Field(...)
    receiver_id: str = Field(...)
    last_message: Optional[str] = None

class Message(BaseModel):
    chat_id: str = Field(...)
    sender_id: str = Field(...)
    text: str = Field(...)

# Add additional schemas here if needed
