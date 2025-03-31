import logging
from fastapi import HTTPException, Depends, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from app.database import admin_collection
from app.config import config
from datetime import datetime, timedelta
from jose import JWTError, jwt
from pydantic import BaseModel

# OAuth2PasswordBearer instance for admin authentication
oauth2_admin = OAuth2PasswordBearer(tokenUrl="/api/admin/login")

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Utility function to authenticate admin
async def authenticate_admin(username: str, password: str):
    """
    Utility function to authenticate admin based on username and password.

    Args:
        username (str): Admin username.
        password (str): Admin password.

    Returns:
        dict: Admin document from the database.

    Raises:
        HTTPException: If admin credentials are invalid (status_code 401).
    """
    # Query admin collection for given username
    admin = await admin_collection.find_one({"username": username})
    
    # Check if admin exists and password matches
    if not admin or admin['password'] != password:
        logger.error(f"Invalid credentials for user: {username}")
        # Raise HTTPException for unauthorized access
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return admin

# Function to create access token
def create_access_token(data: dict, expires_delta: timedelta = 18000):
    """
    Function to create JWT access token.

    Args:
        data (dict): Data to encode into the token payload.
        expires_delta (timedelta, optional): Expiration time delta for the token. Defaults to 18000 seconds (5 hours).

    Returns:
        str: Encoded JWT token string.
    """
    # Create a copy of data to encode into token payload
    to_encode = data.copy()
    
    # Calculate token expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=300)
    
    # Update payload with expiration time
    to_encode.update({"exp": expire})
    
    # Encode JWT token using configured secret and algorithm
    encoded_jwt = jwt.encode(to_encode, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)
    
    return encoded_jwt

# Pydantic model for token data
class TokenData(BaseModel):
    """
    Pydantic model representing token data.
    """
    username: str

# Function to get current admin based on token
async def get_current_admin(request: Request, token: str = Depends(oauth2_admin)):
    """
    Function to get current admin based on JWT token.

    Args:
        request (Request): FastAPI request object.
        token (str, optional): JWT token obtained from request header or cookie. Defaults to Depends(oauth2_admin).

    Returns:
        TokenData: TokenData instance containing admin username.

    Raises:
        HTTPException: If token is invalid or expired (status_code 401).
    """
    # Try to get token from cookies or header
    token = request.cookies.get('access_token') or token
    logger.debug(f"Received token: {token}")
    
    # Exception to raise for credentials validation failure
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT token payload
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        logger.debug(f"Decoded payload: {payload}")
        
        # Get subject (username) from decoded payload
        username: str = payload.get("sub")
        
        # Raise exception if username is not found in payload
        if username is None:
            raise credentials_exception
        
        # Create TokenData instance with username
        token_data = TokenData(username=username)
    
    except JWTError as e:
        # Log JWT decoding error
        logger.error(f"JWT error: {e}")
        
        # Raise exception for JWT validation failure
        raise credentials_exception
    
    return token_data

