import streamlit as st
import os
import datetime
from utils import (
    verify_user,
    register_user,
    get_conversational_agent,
    get_combined_conversational_agent,
    process_and_store_docs,
    process_and_store_single_doc,
    load_vector_store,
    load_global_vector_store,
    create_global_knowledge_base,
    check_global_knowledge_base_status,
    list_preloaded_documents,
    get_user_uploaded_document,
    has_user_uploaded_document,
    delete_user_document_and_index,
    save_chat_history,
    load_chat_history,
    list_past_chats,
    delete_chat_history,
    extract_pdf_content,
    extract_docx_content,
    get_scraped_data_files,
    read_scraped_data_file,
    get_website_full_name
)
from langchain_core.messages import AIMessage, HumanMessage

st.set_page_config(page_title="APMH ChatBot", layout="wide", page_icon="🤖")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "agent_executor" not in st.session_state:
    st.session_state.agent_executor = None
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None
if "viewing_file" not in st.session_state:
    st.session_state.viewing_file = None
if "viewing_scraped_data" not in st.session_state:
    st.session_state.viewing_scraped_data = None
if "selected_website" not in st.session_state:
    st.session_state.selected_website = None
if "viewing_kb_file" not in st.session_state:
    st.session_state.viewing_kb_file = None
if "suggested_questions" not in st.session_state:
    st.session_state.suggested_questions = []
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

def show_login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            st.image("logo.jpeg", width=200)
        except:
            st.title("🤖 APMH ChatBot")
    
    st.markdown("### Secure Login for Document Analysis")
    st.info("📄 Intelligent chatbot for analyzing and extracting insights from your documents")

    with st.sidebar:
        menu = ["Login", "Register"]
        choice = st.selectbox("Menu", menu)

    if choice == "Login":
        st.subheader("🔐 Secure Login")
        st.markdown("Access your document analysis dashboard")
        username = st.text_input("User Name")
        password = st.text_input("Password", type='password')

        if st.button("Login"):
            if verify_user(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.agent_executor = None
                st.session_state.chat_history = []
                st.session_state.current_chat_id = None
                st.rerun()
            else:
                st.error("Incorrect Username or Password")

    elif choice == "Register":
        st.subheader("📄 Create APMH ChatBot Account")
        st.markdown("Join our secure platform for document analysis")
        new_user = st.text_input("Username")
        new_password = st.text_input("Password", type='password')

        if st.button("Register"):
            if register_user(new_user, new_password):
                st.success("You have successfully created an account!")
                st.info("Go to the Login Menu to login")
            else:
                st.error("Username already exists.")

def show_chat_page():
    user_dir = os.path.join("user_data", st.session_state.username)
    vector_store_path = os.path.join(user_dir, "faiss_index")

    with st.sidebar:
        st.title(f"Welcome, {st.session_state.username}!")
        
        if st.button("Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        st.header("Your Chats")
        if st.button("➕ New Chat"):
            new_chat_id = f"chat_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            st.session_state.current_chat_id = new_chat_id
            st.session_state.chat_history = []
            st.session_state.viewing_file = None
            st.session_state.viewing_scraped_data = None
            st.session_state.selected_website = None
            st.rerun()

        st.subheader("Recent Chats")
        past_chats = list_past_chats(st.session_state.username)
        
        for chat_id, chat_title in past_chats.items():
            col1, col2 = st.columns([4, 1])
            with col1:
                if st.button(chat_title, key=f"load_{chat_id}", use_container_width=True):
                    st.session_state.current_chat_id = chat_id
                    st.session_state.chat_history = load_chat_history(st.session_state.username, chat_id)
                    st.session_state.viewing_file = None
                    st.session_state.viewing_scraped_data = None
                    st.session_state.selected_website = None
                    st.rerun()
            with col2:
                if st.button("🗑️", key=f"del_{chat_id}", use_container_width=True, help=f"Delete chat '{chat_title}'"):
                    delete_chat_history(st.session_state.username, chat_id)
                    if st.session_state.current_chat_id == chat_id:
                        st.session_state.current_chat_id = None
                        st.session_state.chat_history = []
                    st.rerun()
        
        current_doc = get_user_uploaded_document(st.session_state.username)
        
        if not current_doc:
            with st.expander("📄 Document Sources", expanded=True):
                st.markdown("**Upload documents for analysis**")
                
                source_type = st.radio("Choose data source:", ("📄 Upload Document", "🌐 Web URL"))
                
                if source_type == "📄 Upload Document":
                    st.markdown("*Supported: PDFs, Word documents, text files, CSV files*")
                    uploaded_file = st.file_uploader("Upload document", type=['pdf', 'docx', 'txt', 'csv'])
                    if uploaded_file:
                        file_path = os.path.join(user_dir, uploaded_file.name)
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        st.success(f"✅ Document '{uploaded_file.name}' uploaded successfully!")
                        st.info("📁 Go to 'Current Document' section below to build the FAISS index.")
                        st.rerun()
                else:
                    st.markdown("*Examples: Web pages, articles, online documents*")
                    url_input = st.text_input("Enter web URL")
                    if url_input and st.button("📥 Download from URL"):
                        try:
                            if not url_input.startswith(('http://', 'https://')):
                                url_input = 'https://' + url_input
                            
                            progress_container = st.container()
                            with progress_container:
                                progress_bar = st.progress(0)
                                status_text = st.empty()
                                
                                status_text.text("🔍 Validating URL...")
                                progress_bar.progress(20)
                                
                                status_text.text("📥 Downloading web content...")
                                progress_bar.progress(50)
                                
                                process_and_store_docs(st.session_state.username, url_input)
                                
                                status_text.text("✅ Verifying FAISS index creation...")
                                progress_bar.progress(80)
                                
                                vector_store_path = os.path.join(user_dir, "faiss_index")
                                if os.path.exists(vector_store_path):
                                    files = os.listdir(vector_store_path)
                                    if 'index.faiss' in files and 'index.pkl' in files:
                                        status_text.text("✅ FAISS index created successfully!")
                                        progress_bar.progress(100)
                                        
                                        from urllib.parse import urlparse
                                        parsed_url = urlparse(url_input)
                                        marker_filename = f"web_content_{parsed_url.netloc.replace('.', '_')}.url"
                                        marker_path = os.path.join(user_dir, marker_filename)
                                        with open(marker_path, 'w') as f:
                                            f.write(f"Source URL: {url_input}\n")
                                            f.write(f"Processed: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                                        
                                        st.success(f"✅ Web content from '{url_input}' processed and indexed successfully!")
                                        st.info("💬 You can now start chatting with the web content.")
                                    else:
                                        st.error("❌ FAISS index files not found after processing!")
                                        return
                                else:
                                    st.error("❌ Vector store directory not created!")
                                    return
                                
                                st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error processing URL: {str(e)}")
                            with st.expander("🔍 Error Details", expanded=False):
                                st.text("Full error traceback:")
                                import traceback
                                st.text(traceback.format_exc())
        else:
            with st.expander("📄 Document Management", expanded=False):
                st.markdown("**Manage your current document**")
                st.info(f"📄 Current document: **{current_doc}**")
                st.warning("⚠️ Only one document allowed at a time")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🗑️ Delete Document", use_container_width=True):
                        delete_user_document_and_index(st.session_state.username)
                        st.session_state.agent_executor = None
                        st.success("✅ Document deleted successfully!")
                        st.rerun()
                
                with col2:
                    if st.button("🔄 Replace Document", use_container_width=True):
                        st.session_state.replace_mode = True
                        st.rerun()
                
                if st.session_state.get("replace_mode", False):
                    st.markdown("---")
                    st.markdown("**Replace current document:**")
                    
                    source_type = st.radio("Choose data source:", ("📄 Upload Document", "🌐 Web URL"), key="replace_source")
                    
                    source_input = None
                    if source_type == "📄 Upload Document":
                        st.markdown("*Supported: PDFs, Word documents, text files, CSV files*")
                        uploaded_file = st.file_uploader("Upload new document", type=['pdf', 'docx', 'txt', 'csv'], key="replace_upload")
                        if uploaded_file:
                            file_path = os.path.join(user_dir, uploaded_file.name)
                            with open(file_path, "wb") as f:
                                f.write(uploaded_file.getbuffer())
                            source_input = file_path
                    else:
                        st.markdown("*Examples: Web pages, articles, online documents*")
                        source_input = st.text_input("Enter web URL", key="replace_url")

                    col1, col2 = st.columns(2)
                    with col1:
                        if source_input and st.button("✅ Confirm Replace", use_container_width=True):
                            progress_container = st.container()
                            with progress_container:
                                progress_bar = st.progress(0)
                                status_text = st.empty()
                                
                                try:
                                    status_text.text("🔄 Initializing document replacement...")
                                    progress_bar.progress(10)
                                    
                                    status_text.text("🗑️ Removing old document and index...")
                                    progress_bar.progress(25)
                                    
                                    status_text.text("📄 Loading and parsing new document...")
                                    progress_bar.progress(45)
                                    
                                    status_text.text("🧠 Creating embeddings and building FAISS index...")
                                    progress_bar.progress(70)
                                    
                                    process_and_store_single_doc(st.session_state.username, source_input)
                                    
                                    status_text.text("✅ Verifying FAISS index creation...")
                                    progress_bar.progress(85)
                                    
                                    if os.path.exists(vector_store_path):
                                        files = os.listdir(vector_store_path)
                                        if 'index.faiss' in files and 'index.pkl' in files:
                                            status_text.text("✅ FAISS index created successfully!")
                                            progress_bar.progress(95)
                                        else:
                                            st.error("❌ FAISS index files not found after replacement!")
                                            return
                                    else:
                                        st.error("❌ Vector store directory not created!")
                                        return
                                    
                                    status_text.text("🎉 Document replacement completed successfully!")
                                    progress_bar.progress(100)
                                    
                                    st.session_state.agent_executor = None
                                    st.session_state.replace_mode = False
                                    
                                    doc_name = os.path.basename(source_input) if os.path.exists(source_input) else "Web content"
                                    st.success(f"✅ Document replaced with '{doc_name}' successfully!")
                                    st.info("💬 You can now start chatting with your new document.")
                                    
                                    st.rerun()
                                    
                                except Exception as e:
                                    progress_bar.progress(0)
                                    status_text.text("❌ Error occurred during replacement")
                                    st.error(f"Error replacing document: {str(e)}")
                                    
                                    with st.expander("🔍 Error Details", expanded=False):
                                        st.text("Full error traceback:")
                                        import traceback
                                        st.text(traceback.format_exc())
                    
                    with col2:
                        if st.button("❌ Cancel Replace", use_container_width=True):
                            st.session_state.replace_mode = False
                            st.rerun()
        
        if current_doc:
            with st.expander("📁 Current Document", expanded=True):
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.text(f"📄 {current_doc}")
                with col2:
                    if st.button("👁️", key=f"view_{current_doc}", help=f"View {current_doc}"):
                        st.session_state.viewing_file = current_doc
                        st.session_state.current_chat_id = None  
                        st.session_state.viewing_scraped_data = None  
                        st.rerun()
                with col3:
                    if st.button("🗑️", key=f"delete_{current_doc}", help=f"Delete {current_doc}"):
                        delete_user_document_and_index(st.session_state.username)
                        st.session_state.agent_executor = None
                        st.success("✅ Document deleted!")
                        st.rerun()
                
                st.markdown("---")
                st.markdown("**📊 FAISS Index Status:**")
                
                if os.path.exists(vector_store_path):
                    try:
                        files = os.listdir(vector_store_path)
                        if 'index.faiss' in files and 'index.pkl' in files:
                            faiss_size = os.path.getsize(os.path.join(vector_store_path, 'index.faiss'))
                            pkl_size = os.path.getsize(os.path.join(vector_store_path, 'index.pkl'))
                         
                            def format_bytes(bytes_size):
                                for unit in ['B', 'KB', 'MB', 'GB']:
                                    if bytes_size < 1024.0:
                                        return f"{bytes_size:.1f} {unit}"
                                    bytes_size /= 1024.0
                                return f"{bytes_size:.1f} TB"
                            
                            st.success("✅ **FAISS Index Ready**")
                            col1, col2 = st.columns(2)
                            with col1:
                                st.text(f"🔍 index.faiss: {format_bytes(faiss_size)}")
                            with col2:
                                st.text(f"📦 index.pkl: {format_bytes(pkl_size)}")
                            
                            creation_time = os.path.getctime(os.path.join(vector_store_path, 'index.faiss'))
                            creation_date = datetime.datetime.fromtimestamp(creation_time).strftime("%Y-%m-%d %H:%M:%S")
                            st.text(f"🕒 Created: {creation_date}")
                            
                            try:
                                vector_store = load_vector_store(vector_store_path)
                                if vector_store:
                                    st.info("🤖 **Index is loaded and ready for chat**")
                                else:
                                    st.warning("⚠️ Index exists but failed to load")
                            except Exception as e:
                                st.warning(f"⚠️ Index exists but has loading issues: {str(e)}")
                        else:
                            st.error("❌ **FAISS Index Incomplete**")
                            st.text(f"Found files: {files}")
                            st.text("Missing required files: index.faiss or index.pkl")
                    except Exception as e:
                        st.error(f"❌ **Error reading index directory**: {str(e)}")
                else:
                    st.warning("⚠️ **No FAISS Index Found**")
                    st.text("Click 'Build Index' below to create the FAISS index")
                    if st.button("🔧 Build Index", key="rebuild_index", use_container_width=True):
                        with st.spinner("Building FAISS index..."):
                            try:
                                if "(Web Content)" in current_doc:
                                    url_files = [f for f in os.listdir(user_dir) if f.endswith('.url')]
                                    if url_files:
                                        marker_file_path = os.path.join(user_dir, url_files[0])
                                        with open(marker_file_path, 'r') as f:
                                            content = f.read()
                                            url_line = [line for line in content.split('\n') if line.startswith('Source URL:')]
                                            if url_line:
                                                source_url = url_line[0].replace('Source URL:', '').strip()
                                                process_and_store_docs(st.session_state.username, source_url)
                                            else:
                                                st.error("❌ Could not find source URL in marker file!")
                                                return
                                    else:
                                        st.error("❌ Could not find URL marker file!")
                                        return
                                else:
                                    file_path = os.path.join(user_dir, current_doc)
                                    process_and_store_docs(st.session_state.username, file_path)
                                
                                st.session_state.agent_executor = None
                                st.success("✅ Index rebuilt successfully!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error rebuilding index: {str(e)}")
        
        with st.expander("📚 Knowledge Base", expanded=False):
            st.markdown("**Preloaded documents available to all users**")
            kb_status = check_global_knowledge_base_status()
            
            if kb_status["preloaded_docs_count"] > 0:
                st.success(f"✅ {kb_status['preloaded_docs_count']} documents in knowledge base")
                for doc in kb_status["preloaded_docs"]:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.text(f"📄 {doc}")
                    with col2:
                        if st.button("👁️", key=f"view_kb_{doc}", help=f"View {doc}"):
                            st.session_state.viewing_kb_file = doc
                            st.session_state.current_chat_id = None
                            st.session_state.viewing_file = None
                            st.session_state.viewing_scraped_data = None
                            st.rerun()
                
                if not kb_status["exists"]:
                    if st.button("🔄 Build Knowledge Base", use_container_width=True):
                        with st.spinner("Building global knowledge base..."):
                            create_global_knowledge_base()
                            st.session_state.agent_executor = None
                        st.success("✅ Knowledge base built successfully!")
                        st.rerun()
                else:
                    st.info("📊 Knowledge base is ready and integrated")
                    if st.button("🔄 Rebuild Knowledge Base", use_container_width=True):
                        with st.spinner("Rebuilding global knowledge base..."):
                            create_global_knowledge_base()
                            st.session_state.agent_executor = None
                        st.success("✅ Knowledge base rebuilt successfully!")
                        st.rerun()
            else:
                st.warning("⚠️ No preloaded documents found")
                st.info("Place PDF files in the 'preloaded_docs' folder to create a knowledge base")

        with st.expander("🏦 RBI Updates", expanded=False):
            st.markdown("**Latest updates from Reserve Bank of India**")
            files = get_scraped_data_files("RBI")
            
            if files:
                if st.button(f"📋 RBI ({len(files)} updates)", key="website_RBI", use_container_width=True):
                    st.session_state.selected_website = "RBI"
                    st.session_state.viewing_scraped_data = True
                    st.session_state.current_chat_id = None
                    st.session_state.viewing_file = None
                    st.rerun()
            else:
                st.text("📋 RBI (No updates)")

        if st.session_state.current_chat_id and st.session_state.suggested_questions:
            with st.expander("💡 Suggested Questions", expanded=False):
                st.markdown("**Quick questions to explore your documents:**")
                
                for i, question in enumerate(st.session_state.suggested_questions[-6:]):
                    if st.button(f"💬 {question}", key=f"sidebar_suggestion_{i}", use_container_width=True):
                        st.session_state.chat_history.append(HumanMessage(content=question))
                        st.rerun()
                
                if len(st.session_state.suggested_questions) > 6:
                    st.caption(f"Showing latest 6 of {len(st.session_state.suggested_questions)} suggestions")
                
                if st.button("🗑️ Clear Suggestions", use_container_width=True):
                    st.session_state.suggested_questions = []
                    st.rerun()

    st.title("🤖 APMH ChatBot")

    if st.session_state.viewing_kb_file:
        kb_file_path = os.path.join("preloaded_docs", st.session_state.viewing_kb_file)
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("← Back to Chat"):
                st.session_state.viewing_kb_file = None
                st.rerun()
        with col2:
            st.markdown(f"### 📚 Knowledge Base: {st.session_state.viewing_kb_file}")
        
        st.divider()
        
        try:
            if st.session_state.viewing_kb_file.endswith('.pdf'):
                with open(kb_file_path, "rb") as pdf_file:
                    pdf_bytes = pdf_file.read()
                
                st.download_button(
                    label="📥 Download PDF",
                    data=pdf_bytes,
                    file_name=st.session_state.viewing_kb_file,
                    mime="application/pdf"
                )
                
                with st.spinner("Extracting PDF content..."):
                    content = extract_pdf_content(kb_file_path)
                if content and not content.startswith("Error"):
                    st.text_area("PDF Content:", content, height=500)
                    st.info(f"📄 Knowledge base PDF content extracted successfully. {len(content.split())} words found.")
                else:
                    st.error(content if content.startswith("Error") else "Could not extract content from PDF")
                    st.info("📄 This PDF is part of the global knowledge base and is indexed for analysis. Use the chat feature to ask questions about this document.")
            else:
                st.error("Only PDF files are supported in the knowledge base.")
                
        except Exception as e:
            st.error(f"Error reading knowledge base file: {str(e)}")
        return

    elif st.session_state.viewing_file:
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("← Back to Chat"):
                st.session_state.viewing_file = None
                st.rerun()
        with col2:
            st.markdown(f"### 📄 Viewing: {st.session_state.viewing_file}")
        
        st.divider()
        
        if "(Web Content)" in st.session_state.viewing_file:
            try:
                url_files = [f for f in os.listdir(user_dir) if f.endswith('.url')]
                if url_files:
                    marker_file_path = os.path.join(user_dir, url_files[0])
                    with open(marker_file_path, 'r') as f:
                        marker_content = f.read()
                        url_line = [line for line in marker_content.split('\n') if line.startswith('Source URL:')]
                        if url_line:
                            source_url = url_line[0].replace('Source URL:', '').strip()
                            
                            st.info(f"🌐 **Web Content Source**: {source_url}")
                            
                            with st.spinner("Fetching web content..."):
                                try:
                                    from langchain_community.document_loaders import WebBaseLoader
                                    loader = WebBaseLoader(source_url)
                                    docs = loader.load()
                                    
                                    if docs:
                                        content = docs[0].page_content
                                        st.text_area("Web Content:", content, height=500)
                                        st.info(f"🌐 Web content fetched successfully. {len(content.split())} words found.")
                                        
                                        if docs[0].metadata:
                                            with st.expander("📋 Content Metadata", expanded=False):
                                                for key, value in docs[0].metadata.items():
                                                    st.text(f"**{key}**: {value}")
                                    else:
                                        st.warning("⚠️ No content could be extracted from the web page.")
                                        
                                except Exception as e:
                                    st.error(f"❌ Error fetching web content: {str(e)}")
                                    st.info("💬 The web content has been processed and indexed for chat. Use the chat feature to ask questions about this content.")
                        else:
                            st.error("❌ Could not find source URL in marker file.")
                else:
                    st.error("❌ Could not find web content marker file.")
                    
            except Exception as e:
                st.error(f"❌ Error accessing web content information: {str(e)}")
                st.info("💬 The web content has been processed and indexed for chat. Use the chat feature to ask questions about this content.")
        else:
            file_path = os.path.join(user_dir, st.session_state.viewing_file)
            
            try:
                if st.session_state.viewing_file.endswith('.txt'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    st.text_area("File Content:", content, height=500)
                    
                elif st.session_state.viewing_file.endswith('.csv'):
                    import pandas as pd
                    df = pd.read_csv(file_path)
                    st.dataframe(df, use_container_width=True)
                    st.info(f"📊 CSV file with {len(df)} rows and {len(df.columns)} columns")
                    
                elif st.session_state.viewing_file.endswith('.pdf'):
                    with open(file_path, "rb") as pdf_file:
                        pdf_bytes = pdf_file.read()
                    
                    st.download_button(
                        label="📥 Download PDF",
                        data=pdf_bytes,
                        file_name=st.session_state.viewing_file,
                        mime="application/pdf"
                    )
                    
                    with st.spinner("Extracting PDF content..."):
                        content = extract_pdf_content(file_path)
                    if content and not content.startswith("Error"):
                        st.text_area("PDF Content:", content, height=500)
                        st.info(f"📄 PDF content extracted successfully. {len(content.split())} words found.")
                    else:
                        st.error(content if content.startswith("Error") else "Could not extract content from PDF")
                        st.info("📄 PDF files are processed and indexed for analysis. Use the chat feature to ask questions about this document.")
                    
                elif st.session_state.viewing_file.endswith('.docx'):
                    with st.spinner("Extracting Word document content..."):
                        content = extract_docx_content(file_path)
                    if content and not content.startswith("Error"):
                        st.text_area("Document Content:", content, height=500)
                        st.info(f"📝 Word document content extracted successfully. {len(content.split())} words found.")
                    else:
                        st.error(content if content.startswith("Error") else "Could not extract content from Word document")
                        st.info("📝 Word documents are processed and indexed for analysis. Use the chat feature to ask questions about this document.")
                    
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")
        return

    elif st.session_state.get("viewing_scraped_data") and st.session_state.get("selected_website"):
        website = st.session_state.selected_website
        full_name = get_website_full_name(website)
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("← Back to Chat"):
                st.session_state.viewing_scraped_data = None
                st.session_state.selected_website = None
                st.rerun()
        with col2:
            st.markdown(f"### 🌐 {website} - {full_name}")
        
        st.divider()
        
        files = get_scraped_data_files(website)
        
        if files:
            st.markdown(f"**Latest updates from {full_name}:**")
            
            if len(files) == 1:
                file_name = files[0]
                content = read_scraped_data_file(website, file_name)
                
                st.markdown(f"#### 📄 {file_name}")
                
                if file_name.endswith('.md'):
                    st.markdown(content, unsafe_allow_html=True)
                    st.info(f"📊 Markdown document contains {len(content.split())} words")
                elif file_name.endswith('.html'):
                    st.components.v1.html(content, height=600, scrolling=True)
                    st.info(f"📊 HTML document contains {len(content.split())} words")
                else:
                    st.text_area("Content:", content, height=500)
                    st.info(f"📊 Document contains {len(content.split())} words")
            else:
                tab_names = [f"📄 {file_name}" for file_name in files]
                tabs = st.tabs(tab_names)
                
                for i, (tab, file_name) in enumerate(zip(tabs, files)):
                    with tab:
                        content = read_scraped_data_file(website, file_name)
                        
                        if file_name.endswith('.md'):
                            st.markdown(content, unsafe_allow_html=True)
                            st.info(f"📊 Markdown document contains {len(content.split())} words")
                        elif file_name.endswith('.html'):
                            st.components.v1.html(content, height=600, scrolling=True)
                            st.info(f"📊 HTML document contains {len(content.split())} words")
                        else:
                            st.text_area("Content:", content, height=400, key=f"scraped_{website}_{i}")
                            st.info(f"📊 Document contains {len(content.split())} words")
        else:
            st.info(f"No updates available for {full_name}")
        return

    has_documents = os.path.exists(vector_store_path)
    
    has_faiss_index = False
    if has_documents:
        try:
            files = os.listdir(vector_store_path)
            has_faiss_index = 'index.faiss' in files and 'index.pkl' in files
        except:
            has_faiss_index = False
    
    if not has_documents and not st.session_state.current_chat_id:
        st.info("📄 Please upload documents (PDFs, Word docs, text files, etc.) or web URLs to begin analysis.")
        st.markdown("""
        **Supported Document Types:**
        - PDF Documents
        - Word Documents (.docx)
        - Text Files (.txt)
        - CSV Files
        - Web Pages and Articles
        - Any text-based content
        """)
        return

    if st.session_state.agent_executor is None:
        with st.spinner("Loading AI agent..."):
            user_vector_store = None
            if has_documents and has_faiss_index:
                try:
                    user_vector_store = load_vector_store(vector_store_path)
                    if user_vector_store is None:
                        st.error("❌ Failed to load vector store. Please rebuild the index.")
                except Exception as e:
                    st.error(f"❌ Error loading vector store: {str(e)}")
                    st.info("💡 Try rebuilding the index from the 'Current Document' section.")
            
            global_vector_store = load_global_vector_store()
            
            if user_vector_store and global_vector_store:
                st.session_state.agent_executor = get_combined_conversational_agent(
                    user_vector_store, 
                    global_vector_store, 
                    "user documents and global knowledge base"
                )
                st.info("🔗 AI agent loaded with access to your documents and global knowledge base")
            elif user_vector_store:
                st.session_state.agent_executor = get_conversational_agent(
                    user_vector_store, 
                    "the provided document or web page"
                )
                st.info("📄 AI agent loaded with access to your documents only")
            elif global_vector_store:
                st.session_state.agent_executor = get_combined_conversational_agent(
                    None, 
                    global_vector_store, 
                    "global knowledge base"
                )
                st.info("📚 AI agent loaded with access to global knowledge base only")
            else:
                from langchain_google_genai import ChatGoogleGenerativeAI
                llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.7)
                st.session_state.agent_executor = llm
                st.warning("⚠️ No documents or knowledge base available. AI will provide general assistance only.")

    elif st.session_state.current_chat_id:
        if st.session_state.pending_question:
            user_query = st.session_state.pending_question
            st.session_state.pending_question = None
            
            st.session_state.chat_history.append(HumanMessage(content=user_query))
            
            with st.chat_message("Human"):
                st.markdown(user_query)
            
            with st.chat_message("AI"):
                with st.spinner("Thinking..."):
                    try:
                        if hasattr(st.session_state.agent_executor, 'invoke') and hasattr(st.session_state.agent_executor, 'retrieval_fn'):
                            response = st.session_state.agent_executor.invoke({"query": user_query})
                            answer = response["result"]
                        elif hasattr(st.session_state.agent_executor, 'invoke') and not hasattr(st.session_state.agent_executor, 'retrieval_fn'):
                            response = st.session_state.agent_executor.invoke({
                                "input": user_query,
                                "chat_history": st.session_state.chat_history
                            })
                            answer = response.get("output", response.get("result", "I couldn't process your question."))
                        else:
                            response = st.session_state.agent_executor.invoke(user_query)
                            answer = response.content
                    except Exception as e:
                        try:
                            if hasattr(st.session_state.agent_executor, 'invoke'):
                                response = st.session_state.agent_executor.invoke(user_query)
                                if hasattr(response, 'content'):
                                    answer = response.content
                                else:
                                    answer = str(response)
                            else:
                                answer = "I'm sorry, I couldn't process your question. Please try again."
                        except:
                            answer = "I'm sorry, I encountered an error. Please try again."
                    
                    st.markdown(answer)
                    
            
            st.session_state.chat_history.append(AIMessage(content=answer))
            save_chat_history(st.session_state.username, st.session_state.current_chat_id, st.session_state.chat_history)
            st.rerun()
        
        for message in st.session_state.chat_history:
            role = "AI" if isinstance(message, AIMessage) else "Human"
            with st.chat_message(role):
                st.markdown(message.content)

        if user_query := st.chat_input("Ask questions about your documents or the knowledge base..."):
            st.session_state.chat_history.append(HumanMessage(content=user_query))
            with st.chat_message("Human"):
                st.markdown(user_query)

            with st.chat_message("AI"):
                with st.spinner("Thinking..."):
                    try:
                        if hasattr(st.session_state.agent_executor, 'invoke') and hasattr(st.session_state.agent_executor, 'retrieval_fn'):
                            response = st.session_state.agent_executor.invoke({"query": user_query})
                            answer = response["result"]
                        elif hasattr(st.session_state.agent_executor, 'invoke') and not hasattr(st.session_state.agent_executor, 'retrieval_fn'):
                            response = st.session_state.agent_executor.invoke({
                                "input": user_query,
                                "chat_history": st.session_state.chat_history
                            })
                            answer = response.get("output", response.get("result", "I couldn't process your question."))
                        else:
                            response = st.session_state.agent_executor.invoke(user_query)
                            answer = response.content
                    except Exception as e:
                        try:
                            if hasattr(st.session_state.agent_executor, 'invoke'):
                                response = st.session_state.agent_executor.invoke(user_query)
                                if hasattr(response, 'content'):
                                    answer = response.content
                                else:
                                    answer = str(response)
                            else:
                                answer = "I'm sorry, I couldn't process your question. Please try again."
                        except:
                            answer = "I'm sorry, I encountered an error. Please try again."
                    
                    st.markdown(answer)
                    
            
            st.session_state.chat_history.append(AIMessage(content=answer))
            
            save_chat_history(st.session_state.username, st.session_state.current_chat_id, st.session_state.chat_history)
    else:
        st.info("Select a past conversation or start a new one from the sidebar.")
        st.markdown("### Welcome to APMH ChatBot! 🤖")
        st.markdown("I'm ready to help you analyze your documents and extract key insights. Upload your documents and start asking questions!")
        
        st.markdown("""
        **Example Questions You Can Ask:**
        - What is the main topic of this document?
        - Can you summarize the key points?
        - What are the important details mentioned?
        - Extract specific information from the document
        - Explain the content in simple terms
        - What conclusions can be drawn from this document?
        """)

if not st.session_state.get("logged_in", False):
    show_login_page()
else:
    show_chat_page()
