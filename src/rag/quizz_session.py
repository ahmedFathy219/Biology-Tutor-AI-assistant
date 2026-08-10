# src/quiz_session.py
import threading
import random
import queue
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from pydantic import BaseModel, Field
from .weakness_tracker import WeaknessTracker

# LLM output format for evaluation
class EvaluationResult(BaseModel):
    correct: bool = Field(description="True if the student's answer is essentially correct.")
    feedback: str = Field(description="Friendly, spoken feedback, max 2 sentences.")
    confidence: float = Field(description="Confidence score from 0.0 to 1.0 that the answer is correct", ge=0.0, le=1.0)


class QuizSession:
    def __init__(self, llm, vectorstore, weakness_tracker=None, max_pool_size=5, focus_topic=None):
        self.llm = llm
        self.vectorstore = vectorstore          
        self.pool = queue.Queue(maxsize=max_pool_size)
        self.tracker = weakness_tracker if weakness_tracker else WeaknessTracker()
        self.focus_topic = focus_topic
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._gen_thread = None

        # Pre‑fill the pool synchronously
        for _ in range(max_pool_size):
            self._generate_one()

        # start background refill thread
        self._fill_pool()
    # ------------------------------------------------------------
    # Background question generator
    # ------------------------------------------------------------
    def _fill_pool(self, initial=False):
        self._gen_thread = threading.Thread(target=self._fill_loop, daemon=True)
        self._gen_thread.start()

    def _fill_loop(self):
        while not self._stop_event.is_set():
            if self.pool.qsize() < self.pool.maxsize:
                self._generate_one()
            else:
                # Sleep a little to avoid busy‑waiting
                self._stop_event.wait(0.2)

    def _generate_loop(self):
        while not self._stop_event.is_set():
            if self.pool.qsize() < self.pool.maxsize:
                self._generate_one()
            else:
                threading.Event().wait(0.2)

    def _generate_one(self):
        try:
            # 1. Choose a topic
            if self.focus_topic:
                topic = self.focus_topic
            else: #get random topic  
                topic = self.tracker.sample_topic()
            query = f"{topic} biology" if topic else "biology"
            # 2. Retrieve a random chunk with that topic using vectorstore
            docs = self.vectorstore.similarity_search(
                query,               # dummy query
                k=3,                     # get a few and pick randomly
                filter={"topic": topic}
            )
            if not docs:
                docs = self.vectorstore.similarity_search("biology", k=3)
                if not docs:
                    return
                chunk = random.choice(docs)
                topic = chunk.metadata.get("topic", "General Biology")
                chunk = chunk.page_content.strip()
                
            else:
                chunk = random.choice(docs).page_content.strip()

            # 3. Generate question (fast LLM call)
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a biology quiz generator. Given the text, create ONE clear, spoken‑style quiz question. Output ONLY the question."),
                ("human", "{text}")
            ])
            chain = prompt | self.llm | StrOutputParser()
            question = chain.invoke({"text": chunk}).strip()

            # 4. Store in pool
            self.pool.put((question, topic, chunk), block=False)
        except queue.Full:
            pass
        except Exception as e:
            print(f"[QuizGen] error: {e}")

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------
    def get_next_question(self) -> tuple[str, str, str]:
        """Return (question, topic, context_chunk)."""
        return self.pool.get()

    def evaluate(self, question: str, user_answer: str) -> dict:
        # Retrieve 2 relevant chunks (no filter needed)
        docs = self.vectorstore.similarity_search(question, k=2)
        context = "\n".join(doc.page_content.strip() for doc in docs)

        parser = JsonOutputParser(pydantic_object=EvaluationResult)    
            
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a biology tutor. Evaluate the student's spoken answer.
Question: {question}
Relevant biology content: {context}
Student's answer: {user_answer}

{format_instructions}"""),
            ("human", "Evaluation:")
        ])
        # Use the same LLM with low temperature for evaluation
        from langchain_ollama import ChatOllama
        eval_llm = ChatOllama(
            model=self.llm.model,
            temperature=0.0,
            base_url=self.llm.base_url,
            num_predict=150,
            num_ctx=2048,
            format="json"
        )
        chain = prompt | eval_llm | parser
        feedback = chain.invoke({
            "question": question,
            "context": context,
            "user_answer": user_answer,
            "format_instructions": parser.get_format_instructions()
        })
        return feedback

    def record_result(self, topic: str, correct: bool):
        self.tracker.update(topic, correct)

    def stop(self):
        self._stop_event.set()
        if self._gen_thread:
            self._gen_thread.join(timeout=2)