import uuid
from pydantic import BaseModel


class RAGQueryRequest(BaseModel):
    query: str


class RAGSourceItem(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    content: str


class RAGQueryResponse(BaseModel):
    query: str
    answer: str
    sources: list[RAGSourceItem]