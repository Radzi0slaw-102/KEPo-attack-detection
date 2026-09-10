import os

from lightrag import LightRAG
from lightrag.llm.ollama import ollama_model_complete, ollama_embed
from lightrag.utils import EmbeddingFunc
from lightrag.kg.shared_storage import initialize_pipeline_status

_raw_ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_HOST = _raw_ollama_host if "://" in _raw_ollama_host else f"http://{_raw_ollama_host}"
OLLAMA_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "1800"))

GENERATOR_MODEL = os.environ.get("FOOTBALL_GENERATOR_MODEL", "qwen2.5:32b")
JUDGE_MODEL = os.environ.get("FOOTBALL_JUDGE_MODEL", "qwen2.5:32b")
LLM_NUM_PREDICT = int(os.environ.get("LLM_NUM_PREDICT", "2048"))


async def build_rag(working_dir: str) -> LightRAG:
    os.makedirs(working_dir, exist_ok=True)

    rag = LightRAG(
        working_dir=working_dir,
        llm_model_func=ollama_model_complete,
        llm_model_name=GENERATOR_MODEL,
        llm_model_kwargs={
            "host": OLLAMA_HOST,
            "timeout": OLLAMA_TIMEOUT,
            "options": {"num_ctx": 8192, "num_predict": LLM_NUM_PREDICT},
        },
        embedding_func=EmbeddingFunc(
            embedding_dim=1024,
            max_token_size=8192,
            func=lambda texts: ollama_embed(
                texts, embed_model="bge-m3", host=OLLAMA_HOST, timeout=OLLAMA_TIMEOUT
            ),
        ),
        enable_llm_cache=False,
    )

    await rag.initialize_storages()
    await initialize_pipeline_status()
    return rag
