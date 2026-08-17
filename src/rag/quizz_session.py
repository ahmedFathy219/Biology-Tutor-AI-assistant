# src/quiz_session.py
import threading
import random
import queue
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from pydantic import BaseModel, Field
from collections import deque
from .weakness_tracker import WeaknessTracker
from utils import load_available_topics

ALLOWED_TOPICS = load_available_topics()

# LLM output format for evaluation
class EvaluationResult(BaseModel):
    correct: bool = Field(description="True if the student's answer is essentially correct.")
    feedback: str = Field(description="Friendly, spoken feedback, max 2 sentences.")
    confidence: float = Field(description="Confidence score from 0.0 to 1.0 that the answer is correct", ge=0.0, le=1.0)


class QuizSession:
    def __init__(self, llm, vectorstore, weakness_tracker=None, max_pool_size=2, focus_topic=None):
        self.llm = llm
        self.vectorstore = vectorstore          
        self.pool = queue.Queue(maxsize=max_pool_size)
        self.tracker = weakness_tracker if weakness_tracker else WeaknessTracker()
        self.focus_topic = focus_topic
        self.recent_chunks = deque(maxlen=20)

        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._gen_thread = None

        # Pre‑fill the pool synchronously
        

        # start background refill thread
        self._fill_pool()
    # ------------------------------------------------------------
    # Background question generator
    # ------------------------------------------------------------
    def _fill_pool(self):
        self._gen_thread = threading.Thread(target=self._fill_loop, daemon=True)
        self._gen_thread.start()

    def _fill_loop(self):
        while not self._stop_event.is_set():
            if self.pool.qsize() < self.pool.maxsize:
                self._generate_one()
            else:
                # Sleep a little to avoid busy‑waiting
                self._stop_event.wait(0.2)
            self._stop_event.wait(0.1)

    def _generate_one(self):
        try:
            # 1. Choose a topic
            if self.focus_topic:
                topic = self.focus_topic
            else: #get random topic  
                topic = self.tracker.sample_topic()

            query = f"key concepts about {topic}"

            # 2. Retrieve a random chunk with that topic using vectorstore

            CANDIDATE_POOL_SIZE = 20

            docs = self.vectorstore.similarity_search(
                query,
                k=CANDIDATE_POOL_SIZE,                     # get a large set
                filter={"topic": topic}
            )

            # if no documents retrieved, fallback to a search using the same querry but no filter
            if not docs:
                docs = self.vectorstore.similarity_search(query, k=CANDIDATE_POOL_SIZE)

                if not docs:
                    print("[ERROR] No documents retrieved")
                    self._stop_event.set() # stop the loop
                    return
            
            fresh_docs = [d for d in docs if d.metadata.get("id") not in self.recent_chunks]

            #choose randomly from fresh docs
            if fresh_docs:
                chunk = random.choice(fresh_docs)
            else: #fallback to all docs
                chunk = random.choice(docs)

            chunk_text = chunk.page_content.strip()
            chunk_id = chunk.metadata.get("id")    
            self.recent_chunks.append(chunk.metadata.get("id"))
            # 3. Generate question (fast LLM call)
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a biology quiz generator. Given the context, create ONE clear, spoken‑style quiz question. Output ONLY the question."),
                ("human", "{context}")
            ])
            chain = prompt | self.llm | StrOutputParser()
            question = chain.invoke({"context": chunk_text}).strip()

            # 4. Store in pool
            self.pool.put((question, topic, chunk_text), block=False)
        except queue.Full:
            pass
        except Exception as e:
            print(f"[QuizGen] error: {e}")
            self._stop_event.set()  #stop the loop

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    def set_topic(self, new_topic: str = None):
        # stop background generation
        self.stop()

        # empty previous question pool
        while not self.pool.empty():
            try:
                self.pool.get_nowait()
            except queue.Empty:
                break

        if new_topic:
            # Validate against allowed topics
            for allowed in ALLOWED_TOPICS:
                if allowed.lower() == new_topic.lower():
                    new_topic = allowed
                    break
            else:
                # executes if we dont break 
                new_topic = self.tracker.sample_topic()
        else:
            new_topic = self.tracker.sample_topic()

        self.focus_topic = new_topic

        #reset stop even for new thread
        self._stop_event = threading.Event()    

        self._generate_one()

        #start background thread
        self._fill_pool()

    def get_next_question(self) -> tuple[str, str, str]:
        """Return (question, topic, context_chunk)."""
        return self.pool.get()

    def evaluate(self, question: str, chunk: str, user_answer: str) -> dict:
        # Retrieve 2 relevant chunks (no filter needed)
        
        # use the same chunk that was used in question generation
        context = chunk

        parser = JsonOutputParser(pydantic_object=EvaluationResult)    
            
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a biology tutor. Evaluate the student's spoken answer. if the student answers partailly or uses keywords that are in the answer, assume correct and explain the missing part in the feedback in a friendly way.
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