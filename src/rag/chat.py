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


# Limit the amount of previous conversation
# sent to the LLM
MAX_MESSAGES = int(
    os.getenv(
        "RAG_MAX_HISTORY_MESSAGES",
        "10",
    )
)


# Ollama generation settings
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
# Limited Chat History
# ============================================================

class LimitedFileChatMessageHistory(
    FileChatMessageHistory
):
    """
    File-based chat history with a maximum number
    of stored messages.

    This prevents the conversation history from
    becoming too large and slowing down the LLM.
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
    # Chat History
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
    # Format Retrieved Documents
    # ========================================================

    def formatDocs(self, docs):
        """
        Format retrieved documents and display
        their sources.
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

        # Combine retrieved chunks into context.
        return "\n\n".join(
            doc.page_content
            for doc in docs
        )

    # ========================================================
    # Build RAG Chain
    # ========================================================

    def buildChain(self):

        # ====================================================
        # 1. Load Embeddings
        # ====================================================

        embeddings = OllamaEmbeddings(
            model=EMBEDDING_MODEL,
            base_url=OLLAMA_HOST,
        )

        # ====================================================
        # 2. Load ChromaDB
        # ====================================================

        vectorstore = Chroma(
            persist_directory=CHROMA_PATH,
            embedding_function=embeddings,
        )

        self.vectorstore = vectorstore

        print(
            f"Vectorstore type: {type(vectorstore)}"
        )

        # ====================================================
        # 3. Create Retriever
        # ====================================================

        self.retriever = vectorstore.as_retriever(
            search_kwargs={
                "k": K,
            }
        )

        # ====================================================
        # 4. Create Ollama LLM
        # ====================================================

        self.llm = ChatOllama(
            model=LLM_MODEL,
            temperature=TEMP,
            base_url=OLLAMA_HOST,
            num_predict=NUM_PREDICT,
            num_ctx=NUM_CONTEXT,
        )

        # ====================================================
        # 5. Teacher Prompt
        # ====================================================

        final_prompt = ChatPromptTemplate.from_messages(
            [

                (
                    "system",
                    """
You are Echo, a professional biology teacher
helping a student learn biology.

Your job is to teach the student clearly and
confidently, like an experienced classroom teacher.

Use ONLY the retrieved biology context to answer
the student's question.

If the answer is not supported by the retrieved
context, say that you do not have enough information
from the provided biology material.

Do not invent information or add unsupported facts.

Your response will be spoken aloud using
text-to-speech.

Teaching style:

Explain concepts step by step, as a teacher would
explain them to a student in class.

Start with the main idea, then explain the important
details.

Use simple language when possible, but keep correct
biological terminology.

When an important biological term is introduced,
briefly explain what it means before using it
repeatedly.

Emphasize the key difference, relationship,
process, or concept that the student needs
to understand.

Use short examples or comparisons when they are
supported by the retrieved context and help the
student understand the concept.

Be calm, confident, patient, and instructional.

Do not sound like a casual friend.

Do not sound like a customer-service assistant.

Do not use phrases such as:
"I'm glad I could help."

"Feel free to ask."

"You're welcome."

Avoid unnecessary friendly comments.

Do not praise the student unnecessarily.

Do not repeat the student's question unless it
helps introduce the explanation.

Do not use Markdown.

Do not use bullet points.

Do not use numbered lists.

Do not use symbols or formatting.

Because your response is spoken aloud, use natural
sentences and short paragraphs.

Keep answers concise but educational.

If the student asks a simple question, give a
direct explanation.

If the student asks for more detail, expand the
explanation and teach the concept step by step.

Do not ask "Do you have any more questions?"
because the main application handles that separately.

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

        # ====================================================
        # 6. RAG Pipeline
        # ====================================================

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

        # ====================================================
        # 7. Add Conversation History
        # ====================================================

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
    # Ask the Assistant
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