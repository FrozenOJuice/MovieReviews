from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


class Usefulness(BaseModel):
    helpful: int = 0
    total_votes: int = 0


class Review(BaseModel):
    review_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    movie_id: str
    user_id: str
    title: str
    rating: int
    date: str = Field(default_factory=lambda: datetime.utcnow().date().isoformat())
    text: str
    usefulness: Usefulness = Field(default_factory=Usefulness)


class ReviewCreate(BaseModel):
    title: str
    rating: int
    text: str


class ReviewUpdate(BaseModel):
    title: Optional[str] = None
    rating: Optional[int] = None
    text: Optional[str] = None


class Vote(BaseModel):
    vote: bool  # True = helpful, False = not helpful
