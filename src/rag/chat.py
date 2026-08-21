import os

from dotenv import load_dotenv

from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_chroma import Chroma

from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
)

from langchain_core.output_parsers import StrOutputParser

from langchain_core.runnables import (
    RunnablePassthrough,
    RunnableLambda,
)

from langchain_core.runnables.history import (
    RunnableWithMessageHistory,
)

from langchain_core.chat_history import (
    BaseChatMessageHistory,
)

from langchain_community.chat_message_histories import (
    FileChatMessageHistory,
)


load_dotenv()


# ============================================================
# Configuration
# ============================================================

CHROMA_PATH = "data/chromadb"

LLM_MODEL = os.getenv(
    "LLM_MODEL",
    "llama3.2:3b",
)

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "nomic-embed-text",
)

OLLAMA_HOST = os.getenv(
    "OLLAMA_HOST",
    "http://localhost:11434",
)

HISTORY_DIR = "data/chat_histories"

K = int(
    os.getenv(
        "RAG_K",
        "3",
    )
)

TEMP = float(
    os.getenv(
        "RAG_TEMP",
        "0.6",
    )
)

MAX_MESSAGES = int(
    os.getenv(
        "RAG_MAX_HISTORY_MESSAGES",
        "10",
    )
)

NUM_PREDICT = int(
    os.getenv(
        "RAG_NUM_PREDICT",
        "256",
    )
)

NUM_CONTEXT = int(
    os.getenv(
        "RAG_NUM_CONTEXT",
        "2048",
    )
)


# ============================================================
# Limited chat history
# ============================================================

class LimitedFileChatMessageHistory(FileChatMessageHistory):
    """
    File-based chat history with a maximum number of messages.

    This prevents the conversation history from becoming too
    large and slowing down the LLM.
    """

    def __init__(
        self,
        file_path: str,
        max_messages: int = MAX_MESSAGES,
    ):
        super().__init__(file_path)
        self.max_messages = max_messages

    @property
    def messages(self):
        messages = super().messages

        if len(messages) > self.max_messages:
            return messages[-self.max_messages:]

        return messages


# ============================================================
# Biology Assistant
# ============================================================

class BioAssistant:

    def __init__(self):

        os.makedirs(
            HISTORY_DIR,
            exist_ok=True,
        )

        self.vectorstore = None

        self.retriever = None

        self.llm = None

        self.chain = self.buildChain()

    # ========================================================
    # Chat history
    # ========================================================

    def getSessionHistory(
        self,
        session_id: str,
    ) -> BaseChatMessageHistory:

        file_path = os.path.join(
            HISTORY_DIR,
            f"{session_id}.json",
        )

        return LimitedFileChatMessageHistory(
            file_path,
            max_messages=MAX_MESSAGES,
        )

    # ========================================================
    # Format retrieved documents
    # ========================================================

    def formatDocs(self, docs):
        """
        Format retrieved documents and display their sources.
        """

        print("\n[RAG] Retrieved documents:")

        if not docs:

            print(
                "[RAG] No documents were retrieved."
            )

            return ""

        for i, doc in enumerate(docs, 1):

            metadata = doc.metadata

            source = metadata.get(
                "source",
                "unknown",
            )

            page = metadata.get(
                "page",
                "?",
            )

            document_type = metadata.get(
                "type",
                "text",
            )

            preview = (
                doc.page_content
                .strip()
                .replace("\n", " ")
            )

            preview = preview[:120]

            print(
                f"   {i}. {source} "
                f"| page {page} "
                f"| type: {document_type}"
            )

            print(
                f'      "{preview}..."'
            )

        print()

        return "\n\n".join(
            doc.page_content
            for doc in docs
        )

    # ========================================================
    # Build RAG chain
    # ========================================================

    def buildChain(self):

        # ----------------------------------------------------
        # 1. Load embeddings
        # ----------------------------------------------------

        embeddings = OllamaEmbeddings(
            model=EMBEDDING_MODEL,
            base_url=OLLAMA_HOST,
        )

        # ----------------------------------------------------
        # 2. Load ChromaDB
        # ----------------------------------------------------

        vectorstore = Chroma(
            persist_directory=CHROMA_PATH,
            embedding_function=embeddings,
        )

        self.vectorstore = vectorstore

        print(
            f"Vectorstore type: {type(vectorstore)}"
        )

        # ----------------------------------------------------
        # 3. Create retriever
        # ----------------------------------------------------

        self.retriever = vectorstore.as_retriever(
            search_kwargs={
                "k": K,
            }
        )

        # ----------------------------------------------------
        # 4. Create Ollama LLM
        # ----------------------------------------------------

        self.llm = ChatOllama(
            model=LLM_MODEL,
            temperature=TEMP,
            base_url=OLLAMA_HOST,
            num_predict=NUM_PREDICT,
            num_ctx=NUM_CONTEXT,
        )

        # ----------------------------------------------------
        # 5. Teacher-style prompt
        # ----------------------------------------------------

        final_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
You are Echo, a professional male biology teacher. Use only the provided context to answer. If the answer isn't there, say so—do not invent facts.

Speak calmly, clearly, and confidently. Avoid casual, playful, or overly enthusiastic language (e.g., "Awesome!"). Explain the why behind concepts, not just the what. Use correct scientific terms, explained naturally. For comparisons or processes, give logical, clear explanations. Keep answers as short as needed, but expand if the student asks for more detail.

For TTS: write in plain spoken sentences—no markdown, bullets, lists, tables, symbols, or formatting. Do not refer to "the context" or "the documents." Sound natural and conversational.

Retrieved biology context:

{context}
""",
                ),

                MessagesPlaceholder(
                    variable_name="chat_history"
                ),

                (
                    "human",
                    "{input}",
                ),
            ]
        )

        # ----------------------------------------------------
        # 6. RAG pipeline
        # ----------------------------------------------------

        rag_chain = (
            RunnablePassthrough.assign(
                context=(
                    RunnableLambda(
                        lambda x: x["input"]
                    )
                    | self.retriever
                    | RunnableLambda(
                        self.formatDocs
                    )
                )
            )
            | final_prompt
            | self.llm
            | StrOutputParser()
        )

        # ----------------------------------------------------
        # 7. Add conversation history
        # ----------------------------------------------------

        conversation_chain = (
            RunnableWithMessageHistory(
                rag_chain,
                self.getSessionHistory,
                input_messages_key="input",
                history_messages_key="chat_history",
            )
        )

        return conversation_chain

    # ========================================================
    # Ask the assistant
    # ========================================================

    def answer(
        self,
        question: str,
        session_id: str = "bio_study",
    ) -> str:

        if not question:

            return (
                "I did not hear your question."
            )

        response = self.chain.invoke(
            {
                "input": question,
            },
            config={
                "configurable": {
                    "session_id": session_id,
                }
            },
        )

        return response