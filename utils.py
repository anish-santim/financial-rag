import os
import json
import hashlib
import streamlit as st
import google.generativeai as genai
from langchain_community.document_loaders import (
    PyPDFLoader,
    UnstructuredWordDocumentLoader,
    TextLoader,
    WebBaseLoader,
    CSVLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.messages import HumanMessage, AIMessage
from pypdf import PdfReader
from docx import Document

try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=GOOGLE_API_KEY)
    os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY
except KeyError:
    st.error("`GOOGLE_API_KEY` not found in `.streamlit/secrets.toml`. Please add it to your secrets file.")
    st.stop()


def get_user_db():
    if not os.path.exists("users.json"):
        with open("users.json", "w") as f:
            json.dump({}, f)
    with open("users.json", "r") as f:
        return json.load(f)

def save_user_db(db):
    with open("users.json", "w") as f:
        json.dump(db, f, indent=4)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_user(username, password):
    db = get_user_db()
    if username in db and db[username] == hash_password(password):
        return True
    return False

def _ensure_chat_dir(username):
    chat_dir = os.path.join("user_data", username, "chats")
    os.makedirs(chat_dir, exist_ok=True)
    return chat_dir

def register_user(username, password):
    db = get_user_db()
    if username in db:
        return False
    db[username] = hash_password(password)
    save_user_db(db)
    os.makedirs(os.path.join("user_data", username), exist_ok=True)
    _ensure_chat_dir(username)
    return True


def load_document(file_path_or_url):
    if os.path.exists(file_path_or_url): 
        _, file_extension = os.path.splitext(file_path_or_url)
        if file_extension.lower() == '.pdf':
            loader = PyPDFLoader(file_path_or_url)
        elif file_extension.lower() == '.docx':
            loader = UnstructuredWordDocumentLoader(file_path_or_url)
        elif file_extension.lower() == '.txt':
            loader = TextLoader(file_path_or_url)
        elif file_extension.lower() == '.csv':
            loader = CSVLoader(file_path_or_url)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
    else: 
        try:
            loader = WebBaseLoader(file_path_or_url)
        except Exception as e:
            raise ValueError(f"Could not load from URL. Error: {e}")

    return loader.load()


def get_conversational_agent(vector_store, source_description):
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=0.7
    )
    retriever = vector_store.as_retriever(search_kwargs={"k": 6})
    
    from langchain.chains import RetrievalQA
    from langchain.prompts import PromptTemplate
    
    template = """You are an intelligent document analysis AI assistant. Use the following document context to answer questions about the content, extract insights, and provide detailed information from the uploaded documents.

    Focus on providing:
    - Accurate information directly from the document content
    - Clear summaries and explanations of key points
    - Specific details and data when available
    - Context and background information
    - Relevant insights and analysis
    - Direct quotes when appropriate

    If you don't have enough information to answer completely, clearly state what information is missing and suggest what additional details might be helpful.

    Document Context: {context}

    Question: {question}
    
    Analysis: """
    
    prompt = PromptTemplate(
        template=template,
        input_variables=["context", "question"]
    )
    
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt}
    )
    
    return qa_chain

def process_and_store_docs(username, file_or_url):
    user_dir = os.path.join("user_data", username)
    vector_store_path = os.path.join(user_dir, "faiss_index")
    docs = load_document(file_or_url)
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    documents = RecursiveCharacterTextSplitter(
        chunk_size=1500, 
        chunk_overlap=300,
        separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
    ).split_documents(docs)
    vectordb = FAISS.from_documents(documents, embeddings)
    vectordb.save_local(vector_store_path)

def load_vector_store(path):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    return FAISS.load_local(path, embeddings, allow_dangerous_deserialization=True)


def save_chat_history(username, chat_id, chat_history):
    chat_dir = _ensure_chat_dir(username)
    history_file = os.path.join(chat_dir, f"{chat_id}.json")
    
    serializable_history = []
    for msg in chat_history:
        if isinstance(msg, HumanMessage):
            serializable_history.append({"type": "human", "content": msg.content})
        elif isinstance(msg, AIMessage):
            serializable_history.append({"type": "ai", "content": msg.content})

    title = "New Chat"
    if serializable_history and serializable_history[0]['type'] == 'human':
        first_message = serializable_history[0]['content']
        title = first_message[:50] + "..." if len(first_message) > 50 else first_message

    with open(history_file, "w") as f:
        json.dump({"title": title, "messages": serializable_history}, f, indent=4)

def load_chat_history(username, chat_id):
    chat_dir = _ensure_chat_dir(username)
    history_file = os.path.join(chat_dir, f"{chat_id}.json")
    if not os.path.exists(history_file):
        return []
    
    try:
        with open(history_file, "r") as f:
            data = json.load(f)
            serializable_history = data.get("messages", [])
        
        history = []
        for msg_data in serializable_history:
            if msg_data["type"] == "human":
                history.append(HumanMessage(content=msg_data["content"]))
            elif msg_data["type"] == "ai":
                history.append(AIMessage(content=msg_data["content"]))
        return history
    except (json.JSONDecodeError, KeyError):
        return [] 

def list_past_chats(username):
    chat_dir = _ensure_chat_dir(username)
    chats = {}
    
    files = [f for f in os.listdir(chat_dir) if f.endswith('.json')]
    files.sort(key=lambda x: os.path.getmtime(os.path.join(chat_dir, x)), reverse=True)

    for file_name in files:
        chat_id = os.path.splitext(file_name)[0]
        file_path = os.path.join(chat_dir, file_name)
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                chats[chat_id] = data.get("title", chat_id)
        except json.JSONDecodeError:
            chats[chat_id] = chat_id
            
    return chats

def delete_chat_history(username, chat_id):
    chat_dir = _ensure_chat_dir(username)
    history_file = os.path.join(chat_dir, f"{chat_id}.json")
    if os.path.exists(history_file):
        os.remove(history_file)

def extract_pdf_content(file_path):
    """Extract text content from PDF file"""
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

def extract_docx_content(file_path):
    """Extract text content from Word document"""
    try:
        doc = Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    except Exception as e:
        return f"Error reading Word document: {str(e)}"

def get_scraped_websites():
    """Get list of available scraped websites"""
    return ["RBI"]

def get_scraped_data_files(website):
    """Get list of scraped data files for a specific website"""
    website_dir = os.path.join("scraped_data", website)
    if not os.path.exists(website_dir):
        return []
    
    files = []
    for file_name in os.listdir(website_dir):
        if file_name.endswith(('.txt', '.pdf', '.csv', '.json', '.md', '.html')):
            file_path = os.path.join(website_dir, file_name)
            # Get file modification time for sorting
            mod_time = os.path.getmtime(file_path)
            files.append((file_name, mod_time))
    
    # Sort by modification time (newest first)
    files.sort(key=lambda x: x[1], reverse=True)
    return [file_name for file_name, _ in files]

def read_scraped_data_file(website, file_name):
    """Read content from a scraped data file"""
    file_path = os.path.join("scraped_data", website, file_name)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

def get_website_full_name(website_code):
    """Get full name of website from code"""
    website_names = {
        "RBI": "Reserve Bank of India"
    }
    return website_names.get(website_code, website_code)

def get_preloaded_docs_path():
    """Get path to preloaded documents directory"""
    return os.path.join("preloaded_docs")

def get_global_vector_store_path():
    """Get path to global vector store for preloaded documents"""
    return os.path.join("global_knowledge_base")

def load_preloaded_documents():
    """Load all preloaded PDF documents"""
    preloaded_path = get_preloaded_docs_path()
    if not os.path.exists(preloaded_path):
        return []
    
    documents = []
    pdf_files = [f for f in os.listdir(preloaded_path) if f.endswith('.pdf')]
    
    for pdf_file in pdf_files:
        file_path = os.path.join(preloaded_path, pdf_file)
        try:
            loader = PyPDFLoader(file_path)
            docs = loader.load()
            for doc in docs:
                doc.metadata['source_file'] = pdf_file
                doc.metadata['source_type'] = 'preloaded'
            documents.extend(docs)
        except Exception as e:
            print(f"Error loading {pdf_file}: {e}")
    
    return documents

def create_global_knowledge_base():
    """Create or update global knowledge base with preloaded documents"""
    global_vector_path = get_global_vector_store_path()
    
    preloaded_docs = load_preloaded_documents()
    
    if not preloaded_docs:
        print("No preloaded documents found")
        return None
    
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500, 
        chunk_overlap=300,
        separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
    )
    documents = text_splitter.split_documents(preloaded_docs)
    
    # Create vector store
    vectordb = FAISS.from_documents(documents, embeddings)
    
    # Save global vector store
    os.makedirs(global_vector_path, exist_ok=True)
    vectordb.save_local(global_vector_path)
    
    print(f"Global knowledge base created with {len(documents)} document chunks from {len(set([doc.metadata['source_file'] for doc in preloaded_docs]))} PDF files")
    return vectordb

def load_global_vector_store():
    """Load global vector store if it exists"""
    global_vector_path = get_global_vector_store_path()
    if not os.path.exists(global_vector_path):
        return None
    
    try:
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        return FAISS.load_local(global_vector_path, embeddings, allow_dangerous_deserialization=True)
    except Exception as e:
        print(f"Error loading global vector store: {e}")
        return None

def get_combined_conversational_agent(user_vector_store, global_vector_store, source_description):
    """Create conversational agent that searches both user documents and global knowledge base"""
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=0.7
    )
    
    # Create retrievers
    retrievers = []
    if user_vector_store:
        user_retriever = user_vector_store.as_retriever(search_kwargs={"k": 3})
        retrievers.append(("user_docs", user_retriever))
    
    if global_vector_store:
        global_retriever = global_vector_store.as_retriever(search_kwargs={"k": 3})
        retrievers.append(("preloaded_docs", global_retriever))
    
    from langchain.prompts import PromptTemplate
    
    def combined_retrieval(query):
        """Retrieve from both user documents and global knowledge base"""
        all_docs = []
        sources = []
        
        for source_name, retriever in retrievers:
            try:
                docs = retriever.get_relevant_documents(query)
                for doc in docs:
                    doc.metadata['retrieval_source'] = source_name
                all_docs.extend(docs)
                sources.append(source_name)
            except Exception as e:
                print(f"Error retrieving from {source_name}: {e}")
        
        # Sort by relevance and limit total results
        return all_docs[:6]
    
    template = """You are an intelligent document analysis AI assistant. You have access to both user-uploaded documents and a preloaded knowledge base of important documents.

    Use the following document context to answer questions. The context includes documents from:
    - User uploaded documents (marked as 'user_docs')
    - Preloaded knowledge base (marked as 'preloaded_docs')

    Focus on providing:
    - Accurate information directly from the document content
    - Clear summaries and explanations of key points
    - Specific details and data when available
    - Context and background information from both sources
    - Relevant insights and analysis
    - Direct quotes when appropriate
    - Source identification (whether from user docs or knowledge base)

    If information is found in both sources, mention both and highlight any differences or complementary information.
    If you don't have enough information to answer completely, clearly state what information is missing.

    Document Context: {context}

    Question: {question}
    
    Analysis: """
    
    prompt = PromptTemplate(
        template=template,
        input_variables=["context", "question"]
    )
    
    # Create a custom chain that uses our combined retrieval
    class CombinedRetrievalQA:
        def __init__(self, llm, prompt, retrieval_fn):
            self.llm = llm
            self.prompt = prompt
            self.retrieval_fn = retrieval_fn
        
        def invoke(self, inputs):
            query = inputs.get("query") or inputs.get("input")
            docs = self.retrieval_fn(query)
            
            # Format context
            context = "\n\n".join([
                f"Source: {doc.metadata.get('retrieval_source', 'unknown')} - {doc.metadata.get('source_file', 'unknown file')}\n{doc.page_content}"
                for doc in docs
            ])
            
            # Generate response
            formatted_prompt = self.prompt.format(context=context, question=query)
            response = self.llm.invoke(formatted_prompt)
            
            return {
                "result": response.content,
                "source_documents": docs
            }
    
    return CombinedRetrievalQA(llm, prompt, combined_retrieval)

def list_preloaded_documents():
    """List all preloaded PDF documents"""
    preloaded_path = get_preloaded_docs_path()
    if not os.path.exists(preloaded_path):
        return []
    
    pdf_files = [f for f in os.listdir(preloaded_path) if f.endswith('.pdf')]
    return sorted(pdf_files)

def check_global_knowledge_base_status():
    """Check if global knowledge base exists and get info about it"""
    global_vector_path = get_global_vector_store_path()
    preloaded_docs = list_preloaded_documents()
    
    return {
        "exists": os.path.exists(global_vector_path),
        "preloaded_docs_count": len(preloaded_docs),
        "preloaded_docs": preloaded_docs
    }

def get_user_uploaded_document(username):
    """Get the currently uploaded document for a user (only one allowed)"""
    user_dir = os.path.join("user_data", username)
    if not os.path.exists(user_dir):
        return None
    
    # Look for uploaded documents
    uploaded_files = [f for f in os.listdir(user_dir) if f.endswith(('.pdf', '.docx', '.txt', '.csv'))]
    
    if uploaded_files:
        return uploaded_files[0]  # Return the first (and should be only) document
    return None

def delete_user_document_and_index(username, filename=None):
    """Delete user's uploaded document and vector index"""
    user_dir = os.path.join("user_data", username)
    vector_store_path = os.path.join(user_dir, "faiss_index")
    
    # If filename not provided, get the current document
    if filename is None:
        filename = get_user_uploaded_document(username)
    
    if filename:
        # Delete the document file
        file_path = os.path.join(user_dir, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted document: {filename}")
    
    # Delete the vector index directory
    if os.path.exists(vector_store_path):
        import shutil
        shutil.rmtree(vector_store_path)
        print(f"Deleted vector index for user: {username}")
    
    return True

def has_user_uploaded_document(username):
    """Check if user has already uploaded a document"""
    return get_user_uploaded_document(username) is not None

def process_and_store_single_doc(username, file_or_url):
    """Process and store a single document (replaces any existing document)"""
    # First, delete any existing document and index
    delete_user_document_and_index(username)
    
    # Then process the new document
    process_and_store_docs(username, file_or_url)
