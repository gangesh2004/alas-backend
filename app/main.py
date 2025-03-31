from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importing route modules from different submodules
from .auth.routes import router as auth_router
# from .profile.routes import router as profile_router
# from .patient.routes import router as patient_router
# from .report.routes import router as report_router
from .admin.routes import router as admin_router

# Create an instance of the FastAPI class
app = FastAPI()

# List of allowed origins for CORS
origins = [
    "http://localhost:5173",
    "http://localhost:8000",
    "http://localhost"
]

# Adding CORS middleware to the FastAPI app
# This middleware allows requests from specified origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,             # List of allowed origins
    allow_credentials=True,            # Allow cookies and authentication
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Allowed HTTP methods
    allow_headers=["*"],               # Allow all headers
)

# Including routers from different submodules with specified prefixes and tags
app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
# app.include_router(profile_router, prefix="/api/profile", tags=["Profile"])
# app.include_router(patient_router, prefix="/api/patient", tags=["Patient"])
# app.include_router(report_router, prefix="/api/report", tags=["Report"])

# Define a root endpoint
@app.get("/")
def read_root():
    """
    Root endpoint that returns a welcome message.
    """
    return {"message": "Welcome to Jivandeep Label-Ai App"}
