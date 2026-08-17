# src/flashcard_session.py
import heapq
import random
import threading
import time
import uuid
import os
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from utils import load_available_topics
AVAILABLE_TOPICS = load_available_topics()
FLASHCARD_POOL_PATH = "data/state/cards.json"
# Output format for one flashcard
class FlashcardPair(BaseModel):
    question: str = Field(description="The question side of the flashcard")
    answer: str   = Field(description="The answer side of the flashcard")


class FlashcardSession:
    """
    Manages flashcard generation, review queue and simple scheduling.
    Shared WeaknessTracker with quiz mode is used to sample weak topics.

    - question is said and revealed on lcd screen(screen not yet implemented).
    - wait for user to say "reveal"
    - answer said to user and displayed
    - prompt user to evaluate the difficulty, easy, medium or hard
    """

    # Initial intervals (in seconds) for a brand‑new card for active recall
    DEFAULT_INTERVALS = {
        "easy":   86400 * 4,   # 4 days
        "medium": 86400,       # 1 day
        "hard":   3600 * 0.5,    # 30 mins (so it comes back in the same session)
    }

    # Multipliers for reviewed cards
    EASE_MULTIPLIERS = {
        "easy":   2.5, 
        "medium": 1.5,
        "hard":   1.0,         # stays the same (minimum 30 minutes)
    }

    def __init__(self, llm, vectorstore, weakness_tracker, max_pool_size=5):
        self.llm = llm
        self.vectorstore = vectorstore
        self.tracker = weakness_tracker
        self.pool = []                  # heapq of (due_timestamp, card_dict)
        self._lock = threading.Lock()
        #restore from disk if this is not the first session
        self._load_pool()

    # helper for loading cards from disk
    def _load_pool(self):
        # load the pool from a JSON file and rebuild the heap between sessions
        if not os.path.exists(FLASHCARD_POOL_PATH):
            return
        try:
            with open(FLASHCARD_POOL_PATH, "r") as f:
                cards = json.load(f)
            for card in cards:
                if card.get("due") is not None:
                    heapq.heappush(self.pool, (card["due"], card))
        except (json.JSONDecodeError, KeyError, IOError) as e:
            print(f"[Flashcard] Error loading pool: {e}, starting empty.")

    def _save_pool(self):
        #write the current heap to the JSON
        
        #ensure directory exists
        os.makedirs(os.path.dirname(FLASHCARD_POOL_PATH), exist_ok=True)    
        cards = [card for (_, card) in self.pool]
        with open(FLASHCARD_POOL_PATH, "w") as f:
            json.dump(cards, f, indent=2)

    # helper to print retreived document references
    def _print_retrieved_docs(self, docs):
        print("\n[Flashcard] Retrieved documents for this card:")
        for i, doc in enumerate(docs, 1):
            metadata = doc.metadata
            source = metadata.get("source", "unknown")
            page = metadata.get("page", "?")
            document_type = metadata.get("type", "text")
            preview = doc.page_content.strip().replace("\n", " ")[:120]
            print(f"   {i}. {source} | page {page} | type: {document_type}")
            print(f'      "{preview}..."')
        print()

    # Generate a brand‑new flashcard for a given topic
    def generate_flashcard(self, topic: str = None) -> dict:
        """
        Retrieve a chunk for `topic` and produce a {question, answer, topic} dict.
        Falls back to a random chunk if no chunks with that topic exist.
        """

        if not topic:
            # generate random topic from tracker
            topic = self.tracker.sample_topic()
        # Retrieve relevant content
        
        query = f"key concepts about {topic}"
        
        # 2. Retrieve a random chunk with that topic using vectorstore

        CANDIDATE_POOL_SIZE = 20

        docs = self.vectorstore.similarity_search(
            query,
            k=CANDIDATE_POOL_SIZE,                     # get a large set
            filter={"topic": topic}
        )
        

        if not docs:
            docs = self.vectorstore.similarity_search(query, k=CANDIDATE_POOL_SIZE)
            if not docs:
                print("[ERROR] No documents retrieved")
                return {}

        self._print_retrieved_docs(docs)
        chunk_text = random.choice(docs).page_content.strip()

        # Generate Q&A
        parser = JsonOutputParser(pydantic_object=FlashcardPair)
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a biology flashcard creator.
Based on the text below, create ONE clear, concise flashcard.
Output a JSON object with exactly two keys: "question" and "answer".
{format_instructions}"""),
            ("human", "{text}")
        ])
        chain = prompt | self.llm | parser
        result = chain.invoke({
            "text": chunk_text,
            "format_instructions": parser.get_format_instructions()
        })
        return {
            "question": result["question"],
            "answer": result["answer"],
            "topic": topic,
            "interval": None,     # will be set on first rating
            "due": None,
            "id": str(uuid.uuid4())     # simple unique id
        }

    # ------------------------------------------------------------
    # Push a card into the review heap with a new due time
    # ------------------------------------------------------------
    def schedule_card(self, card: dict, rating: str):
        """Calculate next review interval and push to heap."""
        now = time.time()
        if not card["interval"]:   # first review
            interval = self.DEFAULT_INTERVALS.get(rating, self.DEFAULT_INTERVALS["medium"])
        else:
            multiplier = self.EASE_MULTIPLIERS.get(rating, 1.0)
            interval = max(86400, card["interval"] * multiplier)  # min 1 day
        card["interval"] = interval
        card["due"] = now + interval
        with self._lock:
            heapq.heappush(self.pool, (card["due"], card))
            self._save_pool()

    # ------------------------------------------------------------
    # Get all due cards (pops them from heap)
    # ------------------------------------------------------------
    def get_due_cards(self) -> list[dict]:
        """Return list of card dicts whose due time <= now."""
        now = time.time()
        due = []
        with self._lock:
            while self.pool and self.pool[0][0] <= now:
                _, card = heapq.heappop(self.pool)
                due.append(card)
            #update the pool on disk so it does not include removed cards    
            self._save_pool()
        return due

    # ------------------------------------------------------------
    # Pick a topic – either user‑specified or from weaknesses
    # ------------------------------------------------------------
    def pick_topic(self, user_topic: str = None) -> str:
        if not user_topic:
            #assume weakest
            return self.tracker.sample_topic()
        for allowed in AVAILABLE_TOPICS:
            if allowed.lower() == user_topic.lower():
                return allowed
        # fallback to weakest topic
        return self.tracker.sample_topic()
