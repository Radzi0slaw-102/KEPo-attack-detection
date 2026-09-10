import asyncio

from lightrag import LightRAG, QueryParam
from lightrag.llm.ollama import ollama_model_complete, ollama_embed
from lightrag.utils import EmbeddingFunc

WORKING_DIR = "./storage"
BOOK_PATH = "book.txt"
LLM_MODEL = "qwen3.5:4b"


async def init_rag() -> LightRAG:
    rag = LightRAG(
        working_dir=WORKING_DIR,
        llm_model_func=ollama_model_complete,
        llm_model_name=LLM_MODEL,
        llm_model_kwargs={
            "think": False,
            "options": {"num_ctx": 8192, "num_predict": 4096}
        },
        embedding_func=EmbeddingFunc(
            embedding_dim=1024,
            max_token_size=8192,
            func=lambda texts: ollama_embed(
                texts,
                embed_model="bge-m3"
            ),
        ),
        enable_llm_cache=False
    )

    return rag


async def main() -> None:
    rag = await init_rag()
    await rag.initialize_storages()

    with open("book.txt", "r", encoding="utf-8") as f:
        await rag.ainsert(f.read())
    print("-- Finished building storages --")
    
    question = "Who and when build the Great Wall of China?"
    answer = await rag.aquery(
        question,
        param=QueryParam(mode="hybrid"),
    )
    print(question)
    print(answer)
    
    await rag.finalize_storages()
    


if __name__ == "__main__":
    asyncio.run(main())