from pydantic import BaseModel, EmailStr, Field
from typing import Optional

# Pydantic model for creating a doctor (with Field annotations)
class DoctorCreate(BaseModel):
    name: str = Field  # Field annotation for doctor's name
    email: EmailStr = Field  # Field annotation for doctor's email (must be an EmailStr)
    phone: str = Field  # Field annotation for doctor's phone number
    password: str = Field  # Field annotation for doctor's password

# Pydantic model representing a user in the database, inherits from DoctorCreate
class UserInDB(DoctorCreate):
    hashed_password: str  # Additional field for storing hashed password in the database

# Pydantic model for a token response
class Token(BaseModel):
    access_token: str  # JWT access token
    token_type: str  # Type of token (e.g., bearer)

# Pydantic model for token data
class TokenData(BaseModel):
    email: Optional[str] = None  # Optional email field in token data

# Comments added to explain the purpose of each class and field:
# - DoctorCreate: Defines schema for creating a doctor with specified fields (name, email, phone, password).
# - UserInDB: Extends DoctorCreate to include hashed_password, representing a doctor's record in the database.
# - Token: Represents the structure of a JWT token response containing an access_token and token_type.
# - TokenData: Represents the structure of decoded JWT token data, specifically with an optional email field.

