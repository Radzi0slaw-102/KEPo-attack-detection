import asyncio

from lightrag import LightRAG, QueryParam
from lightrag.llm.ollama import ollama_model_complete, ollama_embed
from lightrag.utils import EmbeddingFunc

WORKING_DIR = "./storage"
BOOK_PATH = "book.txt"
LLM_MODEL = "qwen3.5:4b"


async def init_rag() -> LightRAG:
    rag = LightRAG() # TODO - write object paramiters

    return rag


async def main() -> None:
    rag = await init_rag()
    # TODO - initialize storage

    with open("book.txt", "r", encoding="utf-8") as f:
        print()
        # TODO - read book.txt and insert its content to rag
    print("-- Finished building storages --")
    
    question = "Who and when build the Great Wall of China?"
    answer = None # TODO - query rag with question
    print(question)
    print(answer)
    
    # TODO - finalize storage
    


if __name__ == "__main__":
    asyncio.run(main())