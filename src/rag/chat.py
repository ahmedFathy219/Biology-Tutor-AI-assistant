from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import FileChatMessageHistory
import os
from dotenv import load_dotenv

load_dotenv()
#configuration

CHROMA_PATH = "data/chromadb"
LLM_MODEL = os.getenv("LLM_MODEL","llama3.2:3b")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL","nomic-embed-text")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
historyDir = "data/chat_histories"

#number of closest documents retrieved
K = int(os.getenv("RAG_K","3"))

#LLM temperature ( 0.0 -> 1.0, higher -> more creative)
TEMP = float(os.getenv("RAG_TEMP","0.8"))

class BioAssistant:

    def __init__(self):
        self.chain = self.buildChain()
        os.makedirs(historyDir, exist_ok=True)

    def getSessionHistory(self, session_id: str) -> BaseChatMessageHistory:
        file_path = os.path.join(historyDir, f"{session_id}.json")
        return FileChatMessageHistory(file_path)


    #combines k retrieved chunks into one text
    def formatDocs(self, docs):
        #combine documents into one string and print their sources

        print("]n Retrieved documents:")
        for i, doc in enumerate(docs, 1):
            meta = doc.metadata
            source = meta.get("source", "unknown")
            page = meta.get("page", "?")
            chunk_type = meta.get("type", "text")
            # Build a short preview of the content (first 100 chars)
            preview = doc.page_content.strip().replace('\n', ' ')[:100]
            print(f"   {i}. {source} | page {page} | {chunk_type}")
            print(f"      \"{preview}...\"")
        print()

        #combine all page content for the llm
        return "\n\n".join(doc.page_content for doc in docs)

    #build RAG pipeline
    def buildChain(self):
        #1- load vector embedings and retriever
        embeddings = OllamaEmbeddings(
            model=EMBEDDING_MODEL,
            base_url=OLLAMA_HOST
        )
        vectorstore = Chroma(
            persist_directory=CHROMA_PATH,
            embedding_function=embeddings
        )
        retriever = vectorstore.as_retriever(search_kwargs={"k": K})

        #2- use LLM (ChatOllama) to  handle message
        llm = ChatOllama(
            model=LLM_MODEL, 
            temperature=TEMP,
            base_url=OLLAMA_HOST
            )

    
        #3- final prompt that uses the retrieved documents and history as context, and user prompt query to be used as input to the LLM

        final_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful biology study assistant. " "Use only the following pieces of retrieved context to answer the question. " "If you don't know the answer, say that you don't know. " "format your response as a script to be used in text to speach" "keep the answer understandable, and accurate\n\n{context}"),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}")
        ])

        #4- build Full pipeline
        # 1. retrieve documents
        # 2. format documents, history and question as text
        # 3. Send Prompt to LLM

        rag_chain = (
            RunnablePassthrough.assign(
                context=RunnableLambda(lambda x: x["input"]) | retriever | RunnableLambda(self.formatDocs)
            )
            | final_prompt
            | llm
            | StrOutputParser() #may need to change to text-to-speach
        )

        #5- add history management to pipeline
        conversation_chain = RunnableWithMessageHistory(
            rag_chain,
            self.getSessionHistory,
            input_messages_key="input",
            history_messages_key="chat_history"
        )

        return conversation_chain

    def answer(self, question: str, session_id: str = "bio_study") -> str:
          response = self.chain.invoke(
                {"input": question},
                config={"configurable": {"session_id": session_id}}
          )
          return response
