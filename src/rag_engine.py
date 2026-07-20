import os
from pathlib import Path
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

from src.config import KNOWLEDGE_BASE_DIR, VECTOR_DB_DIR, EMBEDDING_MODEL_NAME


def build_or_load_vector_db():
    """
    Builds the FAISS vector database from data/knowledge_base files if it doesn't exist,
    otherwise loads the existing database from vector_db/.
    """
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL_NAME)
    faiss_index_path = VECTOR_DB_DIR / "index.faiss"

    # If the vector database already exists, load it from vector_db/
    if faiss_index_path.exists():
        print("Loading existing vector database from vector_db/...")
        vector_db = FAISS.load_local(
            folder_path=str(VECTOR_DB_DIR),
            embeddings=embeddings,
            allow_dangerous_deserialization=True  # Safe for local prototype use
        )
        return vector_db

    # If not built yet, create it from text files in data/knowledge_base/
    print("Building new vector database from data/knowledge_base/...")

    # 1. Load documents from knowledge base directory
    loader = DirectoryLoader(str(KNOWLEDGE_BASE_DIR), glob="*.txt", loader_cls=TextLoader)
    documents = loader.load()

    if not documents:
        raise FileNotFoundError(
            f"No .txt documents found in {KNOWLEDGE_BASE_DIR}. "
            "Please add SOP files before building vector_db."
        )

    # 2. Split documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs = text_splitter.split_documents(documents)

    # 3. Create FAISS index and save it locally in vector_db/
    vector_db = FAISS.from_documents(docs, embeddings)
    vector_db.save_local(folder_path=str(VECTOR_DB_DIR))
    print(f"Vector DB saved successfully to {VECTOR_DB_DIR}!")

    return vector_db


def query_knowledge_base(query_text: str, k: int = 2) -> str:
    """
    Queries the vector database for relevant company procedures to inject into the LLM prompt.
    """
    try:
        vector_db = build_or_load_vector_db()
        results = vector_db.similarity_search(query_text, k=k)

        # Combine retrieved chunks into a single context string
        context = "\n\n".join([doc.page_content for doc in results])
        return context
    except Exception as e:
        print(f"RAG retrieval warning: {e}")
        return ""