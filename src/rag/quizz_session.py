# src/quiz_session.py
import threading
import random
import queue
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from .weakness_tracker import WeaknessTracker

class QuizSession:
    def __init__(self, llm, vectorstore, max_pool_size=5):
        self.llm = llm
        self.vectorstore = vectorstore          
        self.pool = queue.Queue(maxsize=max_pool_size)
        self.tracker = WeaknessTracker()
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._gen_thread = None
        self._fill_pool(initial=True)

    # ------------------------------------------------------------
    # Background question generator
    # ------------------------------------------------------------
    def _fill_pool(self, initial=False):
        if initial:
            for _ in range(self.pool.maxsize):
                self._generate_one()
        else:
            if self._gen_thread and self._gen_thread.is_alive():
                return
            self._stop_event.clear()
            self._gen_thread = threading.Thread(target=self._generate_loop, daemon=True)
            self._gen_thread.start()

    def _generate_loop(self):
        while not self._stop_event.is_set():
            if self.pool.qsize() < self.pool.maxsize:
                self._generate_one()
            else:
                threading.Event().wait(0.2)

    def _generate_one(self):
        try:
            # 1. Choose a topic based on weaknesses
            topic = self.tracker.sample_topic()

            # 2. Retrieve a random chunk with that topic using vectorstore
            docs = self.vectorstore.similarity_search(
                "biology",               # dummy query
                k=3,                     # get a few and pick randomly
                filter={"topic": topic}
            )
            if not docs:
                return
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
        self._fill_pool()
        question, topic, context = self.pool.get()
        return question, topic, context

    def evaluate(self, question: str, user_answer: str) -> str:
        # Retrieve 2 relevant chunks (no filter needed)
        docs = self.vectorstore.similarity_search(question, k=2)
        context = "\n".join(doc.page_content.strip() for doc in docs)

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a biology tutor. Evaluate the student's spoken answer.
Question: {question}
Relevant biology content: {context}
Student's answer: {user_answer}

Give friendly, spoken feedback. If correct, say so and add a brief compliment.
If incorrect or incomplete, give the correct information helpfully.
DO NOT use markdown or lists. Keep it concise."""),
            ("human", "Feedback:")
        ])
        # Use the same LLM with low temperature for evaluation
        from langchain_ollama import ChatOllama
        eval_llm = ChatOllama(
            model=self.llm.model,
            temperature=0.1,
            base_url=self.llm.base_url,
            num_predict=128,
            num_ctx=2048,
        )
        chain = prompt | eval_llm | StrOutputParser()
        feedback = chain.invoke({
            "question": question,
            "context": context,
            "user_answer": user_answer,
        })
        return feedback.strip()

    def record_result(self, topic: str, correct: bool):
        self.tracker.update(topic, correct)

    def stop(self):
        self._stop_event.set()
        if self._gen_thread:
            self._gen_thread.join(timeout=2)