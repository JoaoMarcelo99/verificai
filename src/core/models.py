from typing import List, Optional

from pydantic import BaseModel


class RawPage(BaseModel):
    content: str
    page_number: int
    filename: str


class Chunk(BaseModel):
    id: str
    content: str
    page_numbers: List[int]
    filename: str


class ChatQuery(BaseModel):
    question: str
    threshold: float = 0.4


class SourceResponse(BaseModel):
    file: str
    page: int
    content: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceResponse]
    estimated_cost: Optional[float] = 0.0
