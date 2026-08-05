import os
from dotenv import load_dotenv
# os.environ["OLLAMA_HOST"] = "http://localhost:11434"
# os.environ["OLLAMA_NUM_PARALLEL"] = "0"   # disable local tokenizer

load_dotenv()

import fitz
import pytesseract
import shutil
import platform
from PIL import Image
import io
from tqdm import tqdm
from uuid import uuid4
import re

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_ollama import ChatOllama
from langchain_chroma import Chroma

# --- Configuration ---
DATA_PATH = "data/bio_materials"
CHROMA_PATH = "data/chromadb"
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL","nomic-embed-text")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE","1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP","200"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE","200"))          # embed 200 chunks at a time
TOPIC_LLM_MODEL = "tinyllama:latest" #small model to detect chunk topic from allowed topic list
TOPIC_BATCH_SIZE = 25 #number of chunks to call LLM on in the same prompt for topic detection
ALLOWED_TOPICS = ["Cell Structure", "Genetics", "Ecology", "Psychology", "DNA", "Enzymes", "Human Anatomy", "Genetics", "General Biology", "MicroOrganisms", "Experiments"]

if platform.system() == "Windows":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
# On Linux (Pi) Tesseract is in PATH – no need to set it.

#ensure chromadb is empty
shutil.rmtree(CHROMA_PATH)
os.makedirs(CHROMA_PATH, exist_ok=True)

def classify_chunks_batch(chunks: list[str], model_name: str = TOPIC_LLM_MODEL) -> list[str]:
    #Send a batch of chunks to the LLM to get a list of corresponding topics

    llm = ChatOllama(
        model=model_name,
        temperature=0.0, #no random output
        base_url=OLLAMA_HOST,
        num_predict=5,
        num_ctx=2048
    )

    # Build prompt
    numbered = "\n".join([f"{i+1}. {chunk[:300]}" for i, chunk in enumerate(chunks)])

    prompt = f"""You are a biology topic classifier. Below are {len(chunks)} Biology text snippets. For each snippet, output EXACTLY ONE topic from this list: {', '.join(ALLOWED_TOPICS)}. If none fit, output "General Biology". Return ONLY the topics, one per line, in the same order as the snippets.
    
    Snippets:{numbered}

    topics:"""

    response = llm.invoke(prompt).content.strip()
    topics = [line.strip() for line in response.split("\n") if line.strip()]
    while len(topics) < len(chunks):
        #if output less than expected, pad missing with "General Biology"
        topics.append("General Biology")
    return topics[:len(chunks)]


def ocr_image(image_bytes: bytes) -> str:
    image = Image.open(io.BytesIO(image_bytes))
    text = pytesseract.image_to_string(image)
    return text.strip()

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
            image_list = page.get_images(full=True)
            for img_idx, img_info in enumerate(image_list):
                xref = img_info[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                try:
                    ocr_text = ocr_image(image_bytes)
                except Exception as e:
                    print(f"  OCR fail {filename} p{page_num} img{img_idx}: {e}")
                    continue
                if ocr_text:
                    all_texts.append(ocr_text)
                    all_metadatas.append({
                        "source": filename,
                        "page": page_num,
                        "image": img_idx+1,
                        "type": "ocr"
                    })

    print(f"Total chunks to embed: {len(all_texts)}")

    # --- Classify topics in batches ---
    print("Classifying topics with tiny LLM...")
    topics = []  # will hold topic for each chunk
    for i in tqdm(range(0, len(all_texts), TOPIC_BATCH_SIZE), desc="Topic batches"):
        batch = all_texts[i:i+TOPIC_BATCH_SIZE]
        batch_topics = classify_chunks_batch(batch)
        topics.extend(batch_topics)

    # --- Attach topic to each metadata ---
    for meta, topic in zip(all_metadatas, topics):
        meta["topic"] = topic

    # --- Create vector store in batches ---
    embeddings = OllamaEmbeddings(
        model=EMBEDDING_MODEL,
        base_url=OLLAMA_HOST
    )

    vector_store = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=embeddings
    )

    for i in tqdm(range(0, len(all_texts), BATCH_SIZE), desc="Embedding batches"):
        batch_texts = all_texts[i:i+BATCH_SIZE]
        batch_metadatas = all_metadatas[i:i+BATCH_SIZE]
        # Generate unique IDs for each chunk
        ids = [str(uuid4()) for _ in batch_texts]
        vector_store.add_texts(
            texts=batch_texts,
            metadatas=batch_metadatas,
            ids=ids
        )

    print(f"Vector store saved to {CHROMA_PATH} with {len(all_texts)} chunks.")

if __name__ == "__main__":
    process_pdfs()