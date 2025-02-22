from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from app.core.config import settings
from app.controllers.router import router
from app.core.database import engine, Base
from app.core.logging_config import setup_logging

# Setup logging at application startup
setup_logging()

# Create database tables asynchronously
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Create startup event handler
async def startup_event():
    await init_db()

app = FastAPI(
    title=settings.PROJECT_NAME
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register startup event
app.add_event_handler("startup", startup_event)

app.include_router(router, prefix=settings.API_V1_STR) 