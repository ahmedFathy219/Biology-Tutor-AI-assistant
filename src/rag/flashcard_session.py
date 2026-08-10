# src/flashcard_session.py
import heapq
import random
import threading
import time
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

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
        "hard":   3600 * 2,    # 2 hours (so it comes back in the same session)
    }

    # Multipliers for reviewed cards
    EASE_MULTIPLIERS = {
        "easy":   2.5, 
        "medium": 1.5,
        "hard":   1.0,         # stays the same (minimum 1 day)
    }

    def __init__(self, llm, vectorstore, weakness_tracker, max_pool_size=5):
        self.llm = llm
        self.vectorstore = vectorstore
        self.tracker = weakness_tracker
        self.pool = []                  # heapq of (due_timestamp, card_dict)
        self._lock = threading.Lock()

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
    def generate_flashcard(self, topic: str) -> dict:
        """
        Retrieve a chunk for `topic` and produce a {question, answer, topic} dict.
        Falls back to a random chunk if no chunks with that topic exist.
        """

        if not topic:
            # generate random topic from tracker
            topic = self.tracker.sample_topic()
        # Retrieve relevant content
        query = f"{topic} biology"
        docs = self.vectorstore.similarity_search(
            query, k=3, filter={"topic": topic}
        )
        if not docs:
            docs = self.vectorstore.similarity_search(query, k=3)

        self._print_retrieved_docs(docs)
        chunk = random.choice(docs).page_content.strip()

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
            "text": chunk,
            "format_instructions": parser.get_format_instructions()
        })
        return {
            "question": result["question"],
            "answer": result["answer"],
            "topic": topic,
            "interval": None,     # will be set on first rating
            "due": None,
            "id": time.time()     # simple unique id
        }

    # ------------------------------------------------------------
    # Push a card into the review heap with a new due time
    # ------------------------------------------------------------
    def schedule_card(self, card: dict, rating: str):
        """Calculate next review interval and push to heap."""
        now = time.time()
        if card["interval"] is None:   # first review
            interval = self.DEFAULT_INTERVALS.get(rating, self.DEFAULT_INTERVALS["medium"])
        else:
            multiplier = self.EASE_MULTIPLIERS.get(rating, 1.0)
            interval = max(86400, card["interval"] * multiplier)  # min 1 day
        card["interval"] = interval
        card["due"] = now + interval
        with self._lock:
            heapq.heappush(self.pool, (card["due"], card))

    # ------------------------------------------------------------
    # Get all due cards (pops them from heap)
    # ------------------------------------------------------------
    def get_due_cards(self) -> list[dict]:
        """Return list of card dicts whose due time ≤ now."""
        now = time.time()
        due = []
        with self._lock:
            while self.pool and self.pool[0][0] <= now:
                _, card = heapq.heappop(self.pool)
                due.append(card)
        return due

    # ------------------------------------------------------------
    # Pick a topic – either user‑specified or from weaknesses
    # ------------------------------------------------------------
    def pick_topic(self, user_topic: str = None) -> str:
        if user_topic and user_topic.lower() != "weakest":
            return user_topic
        # fallback to weakest topic
        return self.tracker.sample_topic()
