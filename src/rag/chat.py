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
# CONFIGURATION
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

# Number of documents retrieved from ChromaDB
K = int(
    os.getenv(
        "RAG_K",
        "3",
    )
)

# LLM temperature
TEMP = float(
    os.getenv(
        "RAG_TEMP",
        "0.8",
    )
)


# ============================================================
# BIOLOGY ASSISTANT
# ============================================================

class BioAssistant:

    def __init__(self):

        os.makedirs(
            HISTORY_DIR,
            exist_ok=True,
        )

        self.chain = self.buildChain()

    # ========================================================
    # CHAT HISTORY
    # ========================================================

    def getSessionHistory(
        self,
        session_id: str,
    ) -> BaseChatMessageHistory:

        file_path = os.path.join(
            HISTORY_DIR,
            f"{session_id}.json",
        )

        return FileChatMessageHistory(
            file_path
        )

    # ========================================================
    # FORMAT RETRIEVED DOCUMENTS
    # ========================================================

    def formatDocs(self, docs):

        print()
        print("=" * 60)
        print("RETRIEVED DOCUMENTS")
        print("=" * 60)

        if not docs:
            print("No documents were retrieved.")
            print("=" * 60)
            print()

            return ""

        for i, doc in enumerate(
            docs,
            start=1,
        ):

            metadata = doc.metadata

            source = metadata.get(
                "source",
                "Unknown source",
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

            # Keep the preview short
            if len(preview) > 150:
                preview = preview[:150] + "..."

            print(
                f"\nDocument {i}"
            )

            print(
                f"Source : {source}"
            )

            print(
                f"Page   : {page}"
            )

            print(
                f"Type   : {document_type}"
            )

            print(
                f"Preview: {preview}"
            )

        print()
        print("=" * 60)
        print()

        # Combine retrieved document content
        # and send it to the LLM.
        return "\n\n".join(
            doc.page_content
            for doc in docs
        )

    # ========================================================
    # BUILD RAG CHAIN
    # ========================================================

    def buildChain(self):

        # ----------------------------------------------------
        # 1. LOAD EMBEDDINGS
        # ----------------------------------------------------

        embeddings = OllamaEmbeddings(
            model=EMBEDDING_MODEL,
            base_url=OLLAMA_HOST,
        )

        # ----------------------------------------------------
        # 2. LOAD CHROMA VECTOR DATABASE
        # ----------------------------------------------------

        vectorstore = Chroma(
            persist_directory=CHROMA_PATH,
            embedding_function=embeddings,
        )

        # ----------------------------------------------------
        # 3. CREATE RETRIEVER
        # ----------------------------------------------------

        retriever = vectorstore.as_retriever(
            search_kwargs={
                "k": K
            }
        )

        # ----------------------------------------------------
        # 4. LOAD LLM
        # ----------------------------------------------------

        llm = ChatOllama(
            model=LLM_MODEL,
            temperature=TEMP,
            base_url=OLLAMA_HOST,
        )

        # ----------------------------------------------------
        # 5. CREATE PROMPT
        # ----------------------------------------------------

        final_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
You are Echo, a friendly biology study assistant.

Use ONLY the retrieved biology context to answer
the student's question.

If the answer is not supported by the retrieved
context, say that you don't know rather than
making up information.

Your response will be spoken aloud using
text-to-speech.

Follow these rules:

- Speak naturally and conversationally.
- Keep the explanation clear and easy for a student
  to understand.
- Do not use Markdown.
- Do not use bullet points.
- Do not use numbered lists.
- Do not use symbols or formatting.
- Avoid unnecessary repetition.
- Give a concise answer unless the student asks
  for more detail.
- Use natural sentences that sound good when spoken.
- Do not mention the retrieved documents.
- Do not mention the RAG system.
- Do not mention ChromaDB.
- Do not mention internal system details.

Retrieved biology context:

{context}
""",
                ),

                MessagesPlaceholder(
                    "chat_history"
                ),

                (
                    "human",
                    "{input}",
                ),
            ]
        )

        # ----------------------------------------------------
        # 6. BUILD RAG PIPELINE
        # ----------------------------------------------------

        rag_chain = (
            RunnablePassthrough.assign(
                context=(
                    RunnableLambda(
                        lambda x: x["input"]
                    )
                    | retriever
                    | RunnableLambda(
                        self.formatDocs
                    )
                )
            )
            | final_prompt
            | llm
            | StrOutputParser()
        )

        # ----------------------------------------------------
        # 7. ADD CHAT HISTORY
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
    # ANSWER QUESTION
    # ========================================================

    def answer(
        self,
        question: str,
        session_id: str = "bio_study",
    ) -> str:

        response = self.chain.invoke(
            {
                "input": question
            },
            config={
                "configurable": {
                    "session_id": session_id
                }
            },
        )

        return response