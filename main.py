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

def show_login_page():
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
        
        with st.expander("📄 Document Sources", expanded=not os.path.exists(vector_store_path)):
            st.markdown("**Upload documents for analysis**")
            
            # Check if user already has a document
            current_doc = get_user_uploaded_document(st.session_state.username)
            
            if current_doc:
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
                
                # Show replace mode interface
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
                            # Create progress indicators for replacement
                            progress_container = st.container()
                            with progress_container:
                                progress_bar = st.progress(0)
                                status_text = st.empty()
                                
                                try:
                                    # Step 1: Initialize replacement
                                    status_text.text("🔄 Initializing document replacement...")
                                    progress_bar.progress(10)
                                    
                                    # Step 2: Delete old document and index
                                    status_text.text("🗑️ Removing old document and index...")
                                    progress_bar.progress(25)
                                    
                                    # Step 3: Load and parse new document
                                    status_text.text("📄 Loading and parsing new document...")
                                    progress_bar.progress(45)
                                    
                                    # Step 4: Create embeddings and FAISS index
                                    status_text.text("🧠 Creating embeddings and building FAISS index...")
                                    progress_bar.progress(70)
                                    
                                    # Process the replacement
                                    process_and_store_single_doc(st.session_state.username, source_input)
                                    
                                    # Step 5: Verify index creation
                                    status_text.text("✅ Verifying FAISS index creation...")
                                    progress_bar.progress(85)
                                    
                                    # Check if vector store was created successfully
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
                                    
                                    # Complete
                                    status_text.text("🎉 Document replacement completed successfully!")
                                    progress_bar.progress(100)
                                    
                                    st.session_state.agent_executor = None
                                    st.session_state.replace_mode = False
                                    
                                    # Show success message
                                    doc_name = os.path.basename(source_input) if os.path.exists(source_input) else "Web content"
                                    st.success(f"✅ Document replaced with '{doc_name}' successfully!")
                                    st.info("💬 You can now start chatting with your new document.")
                                    
                                    st.rerun()
                                    
                                except Exception as e:
                                    progress_bar.progress(0)
                                    status_text.text("❌ Error occurred during replacement")
                                    st.error(f"Error replacing document: {str(e)}")
                                    
                                    # Show detailed error information
                                    with st.expander("🔍 Error Details", expanded=False):
                                        st.text("Full error traceback:")
                                        import traceback
                                        st.text(traceback.format_exc())
                    
                    with col2:
                        if st.button("❌ Cancel Replace", use_container_width=True):
                            st.session_state.replace_mode = False
                            st.rerun()
            
            else:
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
                            # Simple URL validation
                            if not url_input.startswith(('http://', 'https://')):
                                url_input = 'https://' + url_input
                            
                            # Create a simple filename from URL
                            from urllib.parse import urlparse
                            parsed_url = urlparse(url_input)
                            filename = f"web_content_{parsed_url.netloc.replace('.', '_')}.txt"
                            file_path = os.path.join(user_dir, filename)
                            
                            # Save URL as a text file for processing
                            with open(file_path, 'w') as f:
                                f.write(f"URL: {url_input}\n")
                                f.write("This file represents web content to be processed.")
                            
                            st.success(f"✅ URL '{url_input}' saved for processing!")
                            st.info("📁 Go to 'Current Document' section below to build the FAISS index.")
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error saving URL: {str(e)}")
        
        current_doc = get_user_uploaded_document(st.session_state.username)
        if current_doc:
            with st.expander("📁 Current Document", expanded=False):
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
                
                # Show FAISS index status
                st.markdown("---")
                st.markdown("**📊 FAISS Index Status:**")
                
                if os.path.exists(vector_store_path):
                    try:
                        files = os.listdir(vector_store_path)
                        if 'index.faiss' in files and 'index.pkl' in files:
                            # Get file sizes for display
                            faiss_size = os.path.getsize(os.path.join(vector_store_path, 'index.faiss'))
                            pkl_size = os.path.getsize(os.path.join(vector_store_path, 'index.pkl'))
                            
                            # Convert bytes to human readable format
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
                            
                            # Show creation time
                            creation_time = os.path.getctime(os.path.join(vector_store_path, 'index.faiss'))
                            creation_date = datetime.datetime.fromtimestamp(creation_time).strftime("%Y-%m-%d %H:%M:%S")
                            st.text(f"🕒 Created: {creation_date}")
                            
                            # Test index functionality
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
                    if st.button("� Build Index", key="rebuild_index", use_container_width=True):
                        with st.spinner("Building FAISS index..."):
                            try:
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
                            st.session_state.agent_executor = None  # Reset agent to use new KB
                        st.success("✅ Knowledge base built successfully!")
                        st.rerun()
                else:
                    st.info("📊 Knowledge base is ready and integrated")
                    if st.button("🔄 Rebuild Knowledge Base", use_container_width=True):
                        with st.spinner("Rebuilding global knowledge base..."):
                            create_global_knowledge_base()
                            st.session_state.agent_executor = None  # Reset agent to use new KB
                        st.success("✅ Knowledge base rebuilt successfully!")
                        st.rerun()
            else:
                st.warning("⚠️ No preloaded documents found")
                st.info("Place PDF files in the 'preloaded_docs' folder to create a knowledge base")

        # RBI Data Section
        with st.expander("🏦 RBI Updates", expanded=False):
            st.markdown("**Latest updates from Reserve Bank of India**")
            files = get_scraped_data_files("RBI")
            
            if files:
                if st.button(f"📋 RBI ({len(files)} updates)", key="website_RBI", use_container_width=True):
                    st.session_state.selected_website = "RBI"
                    st.session_state.viewing_scraped_data = True
                    st.session_state.current_chat_id = None  # Clear chat when viewing scraped data
                    st.session_state.viewing_file = None  # Clear file viewing
                    st.rerun()
            else:
                st.text("📋 RBI (No updates)")

    st.title("🤖 APMH ChatBot")

    # Handle knowledge base file viewing FIRST (before any other checks)
    if st.session_state.viewing_kb_file:
        kb_file_path = os.path.join("preloaded_docs", st.session_state.viewing_kb_file)
        
        # Add a back button and file info
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("← Back to Chat"):
                st.session_state.viewing_kb_file = None
                st.rerun()
        with col2:
            st.markdown(f"### 📚 Knowledge Base: {st.session_state.viewing_kb_file}")
        
        st.divider()
        
        try:
            # Knowledge base files are PDFs
            if st.session_state.viewing_kb_file.endswith('.pdf'):
                # Add download option for PDF
                with open(kb_file_path, "rb") as pdf_file:
                    pdf_bytes = pdf_file.read()
                
                st.download_button(
                    label="📥 Download PDF",
                    data=pdf_bytes,
                    file_name=st.session_state.viewing_kb_file,
                    mime="application/pdf"
                )
                
                # Extract and display PDF content as text
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
        return  # Exit early when viewing knowledge base file

    # Handle user file viewing SECOND (before any other checks)
    elif st.session_state.viewing_file:
        file_path = os.path.join(user_dir, st.session_state.viewing_file)
        
        # Add a back button and file info
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("← Back to Chat"):
                st.session_state.viewing_file = None
                st.rerun()
        with col2:
            st.markdown(f"### 📄 Viewing: {st.session_state.viewing_file}")
        
        st.divider()
        
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
                # Add download option for PDF
                with open(file_path, "rb") as pdf_file:
                    pdf_bytes = pdf_file.read()
                
                st.download_button(
                    label="📥 Download PDF",
                    data=pdf_bytes,
                    file_name=st.session_state.viewing_file,
                    mime="application/pdf"
                )
                
                # Extract and display PDF content as text
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
        return  # Exit early when viewing file

    # Handle scraped data viewing SECOND (before vector store check)
    elif st.session_state.get("viewing_scraped_data") and st.session_state.get("selected_website"):
        website = st.session_state.selected_website
        full_name = get_website_full_name(website)
        
        # Add a back button and website info
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("← Back to Chat"):
                st.session_state.viewing_scraped_data = None
                st.session_state.selected_website = None
                st.rerun()
        with col2:
            st.markdown(f"### 🌐 {website} - {full_name}")
        
        st.divider()
        
        # Get files for the selected website
        files = get_scraped_data_files(website)
        
        if files:
            st.markdown(f"**Latest updates from {full_name}:**")
            
            # Create tabs for each file
            if len(files) == 1:
                # If only one file, display it directly
                file_name = files[0]
                content = read_scraped_data_file(website, file_name)
                
                st.markdown(f"#### 📄 {file_name}")
                
                # Check if it's a markdown file and render accordingly
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
                # If multiple files, use tabs
                tab_names = [f"📄 {file_name}" for file_name in files]
                tabs = st.tabs(tab_names)
                
                for i, (tab, file_name) in enumerate(zip(tabs, files)):
                    with tab:
                        content = read_scraped_data_file(website, file_name)
                        
                        # Check if it's a markdown file and render accordingly
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
        return  # Exit early when viewing scraped data

    # Check if user has documents or is in chat mode
    has_documents = os.path.exists(vector_store_path)
    
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
            # Load user's vector store (if exists)
            user_vector_store = None
            if has_documents:
                user_vector_store = load_vector_store(vector_store_path)
            
            # Load global knowledge base
            global_vector_store = load_global_vector_store()
            
            # Use appropriate agent based on available data sources
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
                # No documents available - create a basic agent
                from langchain_google_genai import ChatGoogleGenerativeAI
                llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.7)
                st.session_state.agent_executor = llm
                st.warning("⚠️ No documents or knowledge base available. AI will provide general assistance only.")

    elif st.session_state.current_chat_id:
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
                        # Check if it's a combined agent or basic LLM
                        if hasattr(st.session_state.agent_executor, 'invoke') and hasattr(st.session_state.agent_executor, 'retrieval_fn'):
                            # Combined agent
                            response = st.session_state.agent_executor.invoke({"query": user_query})
                            answer = response["result"]
                        elif hasattr(st.session_state.agent_executor, 'invoke') and not hasattr(st.session_state.agent_executor, 'retrieval_fn'):
                            # Regular QA agent
                            response = st.session_state.agent_executor.invoke({
                                "input": user_query,
                                "chat_history": st.session_state.chat_history
                            })
                            answer = response.get("output", response.get("result", "I couldn't process your question."))
                        else:
                            # Basic LLM
                            response = st.session_state.agent_executor.invoke(user_query)
                            answer = response.content
                    except Exception as e:
                        # Fallback for any agent type
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
