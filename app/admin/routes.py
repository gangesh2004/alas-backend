from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from app.database import admin_collection, users_collection
from app.admin.utils import authenticate_admin, create_access_token, get_current_admin, TokenData
from pydantic import BaseModel, Field
from datetime import timedelta
import logging
from typing import List
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import config

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()

# Login route for admin
@router.post("/login")
async def login_admin(form_data: OAuth2PasswordRequestForm = Depends()):
    logger.debug(f"Received login request: username={form_data.username}")
    try:
        # Authenticate admin using form data (username and password)
        admin = await authenticate_admin(form_data.username, form_data.password)
        
        # Set token expiration time
        access_token_expires = timedelta(minutes=30)
        
        # Create access token for the admin
        access_token = create_access_token(data={"sub": admin["username"]}, expires_delta=access_token_expires)
        
        logger.debug(f"Generated access token for admin: {admin['username']}")
        
        # Return access token with token type
        return {"access_token": access_token, "token_type": "bearer"}
    
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(status_code=400, detail="Login failed")

# Response model for statistics
class StatisticsResponse(BaseModel):
    total_users: int
    total_uploaded_reports: int

# Secure route to fetch statistics

# Response model for user information
class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    is_active: bool = Field(default=True)  # Default value for existing users

# Response model for uploaded reports

# Endpoint to fetch list of users
@router.get("/users", response_model=List[UserResponse])
async def list_users(admin: TokenData = Depends(get_current_admin)):
    # Retrieve all users from the database
    users = await users_collection.find().to_list(length=None)
    
    # Map database results to UserResponse model
    return [UserResponse(
        id=str(user["_id"]),
        name=user["name"],
        email=user["email"],
        phone=user["phone"],
        is_active=user.get("is_active", True)  # Default to True if not specified
    ) for user in users]


# Request model for user status update (activation/deactivation)
class UpdateUserStatusRequest(BaseModel):
    reason: str = None  # Optional reason for deactivation

# Function to send notification email
def send_email(user_email: str, subject: str, html_content: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.EMAIL_SENDER
    msg["To"] = user_email
    
    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.starttls()  # Secure the connection
            server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
            server.sendmail(config.EMAIL_SENDER, [user_email], msg.as_string())
        logger.info(f"Email sent successfully to {user_email}")
    
    except Exception as e:
        logger.error(f"Failed to send email: {e}")

# Endpoint to update user status (activate/deactivate)
@router.post("/users/{user_email}/status")
async def update_user_status(user_email: str, request: UpdateUserStatusRequest, activate: bool = True, admin: TokenData = Depends(get_current_admin)):
    # Check if user exists
    user = await users_collection.find_one({"email": user_email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prepare data to update in the database
    update_data = {"is_active": activate}
    
    # If deactivating and reason provided, include reason in update_data
    if not activate and request.reason:
        update_data["deactivation_reason"] = request.reason
    
    # Update user status in the database
    await users_collection.update_one({"email": user_email}, {"$set": update_data})

    # Prepare and send email notification based on activation status
    if activate:
        subject = "Account Activated - Label-Ai-App"
        html_content = f"""
        <html>
        <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                <h2 style="text-align: center; color: #4CAF50;">Account Activated</h2>
                <p>Dear {user['name']},</p>
                <p>Your account has been <strong>activated</strong>. You can now log in and continue using the services.</p>
                <p>Thank you,<br>The Admin Team,<br>Jivandeep Healthcare</p>
            </div>
        </body>
        </html>
        """
    else:
        subject = "Account Deactivated - Label-Ai-App"
        html_content = f"""
        <html>
        <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                <h2 style="text-align: center; color: #f44336;">Account Deactivated</h2>
                <p>Dear {user['name']},</p>
                <p>Your account has been <strong>deactivated</strong> for the following reason:</p>
                <p style="color: #f44336;"><strong>{request.reason}</strong></p>
                <p>If you believe this is a mistake, please contact support.</p>
                <p>Thank you,<br>The Admin Team,<br>Jivandeep Healthcare</p>
            </div>
        </body>
        </html>
        """

    # Send notification email to the user
    send_email(user_email, subject, html_content)
    
    # Return success message
    return {"message": f"User {'activated' if activate else 'deactivated'} successfully"}
