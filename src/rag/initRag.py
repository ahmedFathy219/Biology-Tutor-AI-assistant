import os
from dotenv import load_dotenv
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))
load_dotenv()

import fitz
import pytesseract
import shutil
import platform
from PIL import Image
import io
from collections import Counter
import json
from tqdm import tqdm
from uuid import uuid4
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_ollama import ChatOllama
from langchain_chroma import Chroma

from utils import load_config
# --- Configuration ---
DATA_PATH = "data/bio_materials"
CHROMA_PATH = "data/chromadb"
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL","nomic-embed-text")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE","1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP","200"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE","200"))          # embed 200 chunks at a time
TOPIC_LLM_MODEL = "llama3.2:3b" #small model to detect chunk topic from allowed topic list
TOPIC_BATCH_SIZE = 25 #number of chunks to call LLM on in the same prompt for topic detection
ALLOWED_TOPICS = load_config()["ALLOWED_TOPICS"]

AVAILABLE_TOPICS_PATH = Path(__file__).parent.parent / "utils" / "available_topics.json"
AVAILABLE_TOPICS_PATH = str(AVAILABLE_TOPICS_PATH)

MIN_CHUNKS_PER_TOPIC = int(os.getenv("MIN_CHUNKS_PER_TOPIC", "5"))

if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# On Linux (Pi) Tesseract is in PATH – no need to set it.

#ensure chromadb is empty
shutil.rmtree(CHROMA_PATH)
os.makedirs(CHROMA_PATH, exist_ok=True)

def ocr_image(image_bytes: bytes) -> str:
    image = Image.open(io.BytesIO(image_bytes))
    text = pytesseract.image_to_string(image)
    return text.strip()

def embed_topics(embeddings, allowed_topics):
    # precompute embeddings for each topic description
    topic_descriptions = [f"This text is about {topic}" for topic in allowed_topics]
    topic_embeddings = embeddings.embed_documents(topic_descriptions)
    return topic_embeddings, allowed_topics

def classify_chunk(chunk_text, chunk_embedding, topic_embeddings, topic_list, threshold=0.5):
    # Assign topic based on embedding similarity
    sims = cosine_similarity([chunk_embedding], topic_embeddings)[0]
    best_idx = np.argmax(sims)
    if sims[best_idx] >= threshold:
        return topic_list[best_idx]
    else:
        return "General Biology"

def process_pdfs():
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""]
    )

    # Collect all chunks with metadata
    all_texts = []
    all_metadatas = []

    for filename in os.listdir(DATA_PATH):
        if not filename.lower().endswith(".pdf"):
            continue
        filepath = os.path.join(DATA_PATH, filename)
        print(f"Reading {filename}...")
        doc = fitz.open(filepath)

        for page_num in tqdm(range(1, doc.page_count + 1), desc=f"  Pages {filename}", leave=False):
            page = doc[page_num - 1]
            # --- Page text ---
            page_text = page.get_text()
            if page_text.strip():
                chunks = text_splitter.split_text(page_text)
                for chunk in chunks:
                    all_texts.append(chunk)
                    all_metadatas.append({
                        "source": filename,
                        "page": page_num,
                        "type": "text"
                    })

            # --- OCR from images ---
            # image_list = page.get_images(full=True)
            # for img_idx, img_info in enumerate(image_list):
            #     xref = img_info[0]
            #     base_image
            #     image_bytes

            #     try:
            #         base_image = doc.extract_image(xref)
            #         image_bytes = base_image["image"]
            #     except Exception as e:
            #         print(f"  Image extraction fail {filename} p{page_num} img{img_idx}: {e}")
            #         continue
            #     try:
            #         ocr_text = ocr_image(image_bytes)
            #     except Exception as e:
            #         print(f"  OCR fail {filename} p{page_num} img{img_idx}: {e}")
            #         continue
            #     if ocr_text:
            #         all_texts.append(ocr_text)
            #         all_metadatas.append({
            #             "source": filename,
            #             "page": page_num,
            #             "image": img_idx+1,
            #             "type": "ocr"
            #         })

    print(f"Total chunks to embed: {len(all_texts)}")

    
    # --- Create vector store in batches ---
    embeddings = OllamaEmbeddings(
        model=EMBEDDING_MODEL,
        base_url=OLLAMA_HOST
    )

    # embed topics
    topic_embeddings, topic_list = embed_topics(embeddings, ALLOWED_TOPICS)

    vector_store = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=embeddings
    )   

    topics = []

    for i in tqdm(range(0, len(all_texts), BATCH_SIZE), desc="Classifying and Embedding batches"):
        batch_texts = all_texts[i:i+BATCH_SIZE]
        batch_metadatas = all_metadatas[i:i+BATCH_SIZE]

        # embed this batch
        batch_embeddings = embeddings.embed_documents(batch_texts)

        # classify each chunk in the batch
        batch_topics = []
        for chunk_text, chunk_emb in zip(batch_texts, batch_embeddings):
            topic = classify_chunk(chunk_text, chunk_emb, topic_embeddings, topic_list, threshold=0.4)
            batch_topics.append(topic)

        topics.extend(batch_topics)

        # add topic to metadata for each chunk
        for meta, topic in zip(batch_metadatas, batch_topics):
            meta["topic"] = topic

        # Generate unique IDs for each chunk and add to metadata
        ids = [str(uuid4()) for _ in batch_texts]
        for meta, id_ in zip(batch_metadatas, ids):
            meta["id"] = id_

        # add computed embeddings to vector store   

        collection = vector_store._collection

        collection.add(
            documents=batch_texts,
            embeddings=batch_embeddings,
            metadatas=batch_metadatas,
            ids=ids
        )

# --- Count topic occurences ---
    topic_counter = Counter(topics)
    print("\nTopic distribution:")
    for t, cnt in sorted(topic_counter.items(), key=lambda x: -x[1]):
        print(f"   {t}: {cnt} chunks")

    # --- Filter topics by minimum chunk count ---

    available_topics = [t for t in ALLOWED_TOPICS if topic_counter.get(t, 0) >= MIN_CHUNKS_PER_TOPIC]

    if "General Biology" not in available_topics and topic_counter.get("General Biology", 0) > 0:
        available_topics.append("General Biology")

    print(f"\nAvailable topics (count tagged >= {MIN_CHUNKS_PER_TOPIC} chunks): {available_topics}")

    # --- Save Available topics to a json file to be used by other components ---
    
    os.makedirs(os.path.dirname(AVAILABLE_TOPICS_PATH), exist_ok=True)
    with open(AVAILABLE_TOPICS_PATH, "w") as f:
        json.dump(available_topics, f, indent=2)

    print(f"Saved available topics to {AVAILABLE_TOPICS_PATH}")

    print(f"Vector store saved to {CHROMA_PATH} with {len(all_texts)} chunks.")


if __name__ == "__main__":
    process_pdfs()