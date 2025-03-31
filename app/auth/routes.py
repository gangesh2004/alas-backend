from fastapi import APIRouter, HTTPException, Depends, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from app.database import users_collection
from app.auth.schemas import DoctorCreate, Token, UserInDB
from app.auth.utils import get_password_hash, verify_password, create_access_token, authenticate_user, generate_verification_code, send_verification_code, ForgotPasswordRequest, VerifyCodeRequest, ResetPasswordRequest
from datetime import timedelta, datetime


router = APIRouter()

@router.post("/register", response_model=dict)
async def register(doctor: DoctorCreate):
    existing_user = await users_collection.find_one({"email": doctor.email})
    if existing_user:
        if not existing_user.get("is_active", True):
            raise HTTPException(status_code=400, detail="Your account has been deactivated. Please contact support at gangeshsonu2004@gmail.com.")
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(doctor.password)
    doctor_dict = doctor.dict()
    doctor_dict["password"] = hashed_password
    doctor_dict["is_active"] = True  # Ensure new users are active by default
    
    await users_collection.insert_one(doctor_dict)
    return {"message": "User created successfully"}

# Login endpoint
@router.post("/login")
async def login_for_access_token(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Your account has been deactivated. Please contact support at gangeshsonu2004@gmail.com.")
    
    access_token_expires = timedelta(minutes=1440)
    access_token = create_access_token(data={"sub": user["email"]}, expires_delta=access_token_expires)
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True, samesite="None")
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    user = await users_collection.find_one({"email": request.email})
    if not user:
        raise HTTPException(status_code=400, detail="Email not registered")

    verification_code = generate_verification_code()
    await users_collection.update_one(
        {"email": request.email},
        {"$set": {"verification_code": verification_code, "code_expiry": datetime.utcnow() + timedelta(minutes=10)}}
    )

    await send_verification_code(request.email, verification_code)
    return {"message": "Verification code sent to email"}

@router.post("/verify-code")
async def verify_code(request: VerifyCodeRequest):
    user = await users_collection.find_one({"email": request.email})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or code")
    
    if user.get("verification_code") != request.code or datetime.utcnow() > user.get("code_expiry"):
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    
    return {"message": "Code verified successfully"}

@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    user = await users_collection.find_one({"email": request.email})
    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or code")

    if user.get("verification_code") != request.code or datetime.utcnow() > user.get("code_expiry"):
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    hashed_password = get_password_hash(request.new_password)
    await users_collection.update_one(
        {"email": request.email},
        {"$set": {"password": hashed_password}, "$unset": {"verification_code": "", "code_expiry": ""}}
    )

    return {"message": "Password reset successfully"}