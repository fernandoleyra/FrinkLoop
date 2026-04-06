"""
API project — starter scaffold (FastAPI).
Agents will implement routes and services based on the BRIEF.
"""

from fastapi import FastAPI
from api.routes import router
from api.config import Settings

settings = Settings()
app = FastAPI(title=settings.app_name)
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
