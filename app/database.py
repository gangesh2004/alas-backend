from motor.motor_asyncio import AsyncIOMotorClient
from .config import config

# Initialize the AsyncIOMotorClient with the MongoDB URI from the config
client = AsyncIOMotorClient(config.MONGO_URI)

# Access the specified database from the client
database = client[config.MONGO_DB]

# Collections in the MongoDB database

# Admin Collection: Stores admin-related data
admin_collection = database.get_collection("admin")

# Users Collection: Stores information about doctors and other users
users_collection = database.get_collection("users")

# Patients Collection: Stores patient-related data
teachers_collection = database.get_collection("teachers")


