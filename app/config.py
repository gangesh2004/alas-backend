import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

class Config:
    # MongoDB configuration
    MONGO_URI = os.getenv("MONGO_URI")                      # MongoDB URI
    MONGO_DB = os.getenv("MONGO_DB")                        # MongoDB database name

    # JWT configuration
    JWT_SECRET = os.getenv("JWT_SECRET")                    # JWT secret key
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")              # JWT algorithm

    # Email configuration
    EMAIL_SENDER = os.getenv("EMAIL_SENDER")                # Sender email address
    SMTP_SERVER = os.getenv("SMTP_SERVER")                  # SMTP server address
    SMTP_PORT = os.getenv("SMTP_PORT")                      # SMTP server port
    SMTP_USERNAME = os.getenv("SMTP_USERNAME")              # SMTP username
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")              # SMTP password

    # Google service account configuration
    # GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")  # Path to the Google service account file
    # GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")            # Google Drive folder ID

# Create an instance of the Config class
config = Config()
