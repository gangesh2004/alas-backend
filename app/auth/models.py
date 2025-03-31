from pydantic import BaseModel, EmailStr
from bson import ObjectId

# Pydantic model representing a User
class User(BaseModel):
    id: ObjectId  # ObjectId field for MongoDB document ID
    name: str  # String field for user's name
    email: EmailStr  # EmailStr field for user's email (validated as email format)
    phone: str  # String field for user's phone number
    password: str  # String field for user's password
    username: EmailStr  # EmailStr field for user's username (validated as email format)
