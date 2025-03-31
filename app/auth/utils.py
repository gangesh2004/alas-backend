from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from app.config import config  # Assuming this imports your project's configuration
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.database import users_collection  # Assuming you have a users_collection for users

# OAuth2PasswordBearer instance for token management
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# Pydantic model for token data
class TokenData(BaseModel):
    username: str 

# CryptContext for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Function to verify a plain password against a hashed password
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# Function to hash a password
def get_password_hash(password):
    return pwd_context.hash(password)

# Function to create an access token with optional expiration time
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=1440)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)
    return encoded_jwt

# Function to retrieve a user from the database by email
def get_user(username: str):
    user = users_collection.find_one({"email": username})
    if user:
        return user
    return None

# Asynchronous function to authenticate a user based on username and password
async def authenticate_user(username: str, password: str):
    user = await users_collection.find_one({"email": username})
    if not user:
        return False
    if not verify_password(password, user["password"]):
        return False
    return user

# Asynchronous function to get the current user from a request and validate the JWT token
async def get_current_user(request: Request, token: str = Depends(oauth2_scheme)):
    token = request.cookies.get('access_token') or token
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    return token_data

# Pydantic models for password reset request and verification code request
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class VerifyCodeRequest(BaseModel):
    email: EmailStr
    code: str

# Pydantic model for reset password request
class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str 
    
# Function to generate a random 6-digit verification code
def generate_verification_code():
    return str(random.randint(100000, 999999))

# Asynchronous function to send a verification code via email
async def send_verification_code(email: str, code: str):
    # HTML email content with the verification code
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            .email-container {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                padding: 20px;
                max-width: 600px;
                margin: 0 auto;
                border: 1px solid #ddd;
                border-radius: 10px;
            }}
            .email-header {{
                background-color: #f4f4f4;
                padding: 20px;
                text-align: center;
                border-bottom: 1px solid #ddd;
            }}
            .email-body {{
                padding: 20px;
            }}
            .email-footer {{
                background-color: #f4f4f4;
                padding: 10px;
                text-align: center;
                font-size: 12px;
                color: #777;
                border-top: 1px solid #ddd;
            }}
            .verification-code {{
                font-size: 24px;
                font-weight: bold;
                text-align: center;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="email-header">
                <h1>Password Reset Verification Code</h1>
            </div>
            <div class="email-body">
                <p>Dear User,</p>
                <p>You have requested to reset your password. Please use the following verification code to proceed:</p>
                <div class="verification-code">{code}</div>
                <p>This code is valid for 10 minutes. If you did not request a password reset, please ignore this email.</p>
            </div>
            <div class="email-footer">
                <p>Thank You,<br>Jivandeep Healthcare</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Create the email message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Label Ai App Password Reset Verification Code"
    msg["From"] = config.EMAIL_SENDER
    msg["To"] = email
    
    # Attach the HTML content
    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.starttls()  # Secure the connection
            server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
            server.sendmail(config.EMAIL_SENDER, [email], msg.as_string())
        print("Email sent successfully")
    except Exception as e:
        print(f"Failed to send email: {e}")
