from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.authentication import router as authentication_router
from backend.movies import router as movies_router
from backend.reviews import router as reviews_router
from backend.reports import router as reports_router
from backend.penalties import router as penalties_router


app = FastAPI()

# Include routers
app.include_router(authentication_router.router)
app.include_router(movies_router.router)
app.include_router(reviews_router.router)
app.include_router(reports_router.router)
app.include_router(penalties_router.router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get('/')
async def read_root():
    return {"message": "Backend is up"}