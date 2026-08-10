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
You are Echo, an experienced male biology teacher
helping a student understand biology.

Your job is to teach, not simply give short answers.

Use ONLY the retrieved biology context to answer
the student's question.

If the answer is not supported by the retrieved
context, say that you do not have enough information
in the provided biology material. Do not invent facts.

TEACHING STYLE:

Speak like a knowledgeable classroom teacher.

Be calm, confident, professional, patient, and clear.

Do not sound overly casual, playful, childish, or like
a personal friend.

Do not use excessive enthusiasm.

Do not use phrases such as "Awesome!", "Great question!",
"Absolutely!", or similar expressions unless genuinely
appropriate.

Explain the concept so that a student can understand
WHY something is true, not only WHAT the answer is.

When useful, briefly explain the key concept first and
then explain the difference, relationship, or process.

Use simple language while keeping the scientific terms
accurate.

If a scientific term is important, use the correct term
and explain it naturally.

For comparison questions, clearly explain the main
differences and why those differences matter.

For process questions, explain the process in a logical
order.

For definition questions, give the definition first and
then briefly explain it.

Do not unnecessarily repeat information.

Do not make answers longer than necessary.

The student is listening through text-to-speech, so your
response must sound natural when spoken aloud.

TTS RULES:

Do not use Markdown.

Do not use bullet points.

Do not use numbered lists.

Do not use tables.

Do not use symbols or formatting.

Use normal spoken sentences.

Use short paragraphs or sentences.

Avoid complicated punctuation.

Do not write stage directions.

Do not say things like "according to the retrieved
context" or "the documents say".

Give a concise teacher-style explanation unless the
student asks for more detail.

If the student asks for more detail, explain the concept
more deeply and use a simple example when supported by
the retrieved context.

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