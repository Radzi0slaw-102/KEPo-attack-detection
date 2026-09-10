import asyncio
import os
from dotenv import load_dotenv

from lightrag import LightRAG
from lightrag.llm.ollama import ollama_model_complete, ollama_embed
from lightrag.utils import EmbeddingFunc
from lightrag.kg.shared_storage import initialize_pipeline_status

load_dotenv()

WORKING_DIR = os.environ.get("LIGHTRAG_WORKING_DIR", "./storage")
BOOK_PATH = os.environ.get("LIGHTRAG_BOOK_PATH", "book.txt")
LLM_MODEL = os.environ.get("KEPO_GENERATOR_MODEL", "qwen2.5:1.5b")

_raw_ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_HOST = _raw_ollama_host if "://" in _raw_ollama_host else f"http://{_raw_ollama_host}"
OLLAMA_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "1800"))
LLM_NUM_PREDICT = int(os.environ.get("LLM_NUM_PREDICT", "4096"))


async def build_rag() -> LightRAG:
    os.makedirs(WORKING_DIR, exist_ok=True)

    rag = LightRAG(
        working_dir=WORKING_DIR,
        llm_model_func=ollama_model_complete,
        llm_model_name=LLM_MODEL,
        llm_model_kwargs={
            "host": OLLAMA_HOST,
            "timeout": OLLAMA_TIMEOUT,
            "options": {"num_ctx": 8192, "num_predict": LLM_NUM_PREDICT},
        },
        embedding_func=EmbeddingFunc(
            embedding_dim=1024,
            max_token_size=8192,
            func=lambda texts: ollama_embed(
                texts,
		embed_model="bge-m3",
		host=OLLAMA_HOST,
		timeout=OLLAMA_TIMEOUT
            ),
        ),
        enable_llm_cache=False,
    )

    await rag.initialize_storages()
    await initialize_pipeline_status()
    return rag


async def main() -> None:
    rag = await build_rag()

    with open(BOOK_PATH, "r", encoding="utf-8") as f:
        await rag.ainsert(f.read())

    await rag.finalize_storages()

    print("-- Finished building storages --")


if __name__ == "__main__":
    asyncio.run(main())
