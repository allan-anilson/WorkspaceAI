from pathlib import Path
from docx import Document as DocxDocument
from google import genai
from google.genai import types
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from app.core.config import settings

# Initialize Gemini Client
client = genai.Client(api_key=settings.GEMINI_API_KEY)


def extract_text_from_file(file_path: str) -> str:
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in (".txt", ".md"):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    elif suffix == ".pdf":
        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)

    elif suffix == ".docx":
        doc = DocxDocument(str(path))
        return "\n".join([p.text for p in doc.paragraphs])

    return ""


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
    """Generates vector embeddings via Gemini text-embedding-004."""
    if not texts:
        return []

    # Gemini async batch embeddings
    response = await client.aio.models.embed_content(
        model=settings.EMBEDDING_MODEL,
        contents=texts,
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