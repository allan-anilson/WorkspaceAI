from pathlib import Path
from docx import Document as DocxDocument
from google import genai
from google.genai import types
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from typing import BinaryIO
import io

from app.core.config import settings

# Initialize Gemini Client
client = genai.Client(api_key=settings.GEMINI_API_KEY)


def extract_text_from_file(file_source: str | Path | BinaryIO, file_ext: str | None = None) -> str:
    """
    Extracts text from a file path, BytesIO stream, or raw binary buffer.
    Supports .txt, .md, .pdf, and .docx formats.
    """
    # 1. Determine extension if not explicitly supplied
    if file_ext is None:
        if isinstance(file_source, (str, Path)):
            file_ext = Path(file_source).suffix.lower()
        else:
            file_ext = ".txt"
    else:
        file_ext = file_ext.lower()
        if not file_ext.startswith("."):
            file_ext = f".{file_ext}"

    # 2. Extract based on format
    try:
        if file_ext in (".txt", ".md"):
            if isinstance(file_source, (str, Path)):
                with open(file_source, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            elif isinstance(file_source, (io.BytesIO, io.BufferedReader)):
                return file_source.read().decode("utf-8", errors="ignore")
            elif isinstance(file_source, bytes):
                return file_source.decode("utf-8", errors="ignore")

        elif file_ext == ".pdf":
            # PdfReader accepts both a file path string or an in-memory BytesIO stream
            reader = PdfReader(file_source)
            text_parts = [page.extract_text() or "" for page in reader.pages]
            return "\n\n".join(text_parts)

        elif file_ext == ".docx":
            # docx.Document accepts either a file path or a BytesIO stream
            doc = DocxDocument(file_source)
            return "\n\n".join([p.text for p in doc.paragraphs if p.text.strip()])

        else:
            # Fallback for plain text or unsupported formats
            if isinstance(file_source, (io.BytesIO, io.BufferedReader)):
                return file_source.read().decode("utf-8", errors="ignore")
            elif isinstance(file_source, bytes):
                return file_source.decode("utf-8", errors="ignore")
            return ""

    except Exception as e:
        raise RuntimeError(f"Failed to parse text from {file_ext} file: {e}")


def split_text_into_chunks(
    text: str, chunk_size: int = 1000, chunk_overlap: int = 150
) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )
    return splitter.split_text(text)


async def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Generates vector embeddings via Gemini embedding model."""
    if not texts:
        return []

    response = await client.aio.models.embed_content(
        model=settings.EMBEDDING_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(
            output_dimensionality=768,
        ),
    )
    return [item.values for item in response.embeddings]


async def generate_rag_answer(query: str, context_chunks: list[str]) -> str:
    """Synthesizes an answer using the retrieved context via Gemini."""
    context_str = "\n\n---\n\n".join(context_chunks)
    system_instruction = (
        "You are an AI assistant for a collaborative workspace. Answer the user's question "
        "truthfully and concisely based ONLY on the provided context. If the context does not contain "
        "the answer, state that the documents do not provide this information."
    )
    user_prompt = f"Context:\n{context_str}\n\nQuestion: {query}"

    response = await client.aio.models.generate_content(
        model=settings.LLM_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.2,
        ),
    )
    return response.text or ""  