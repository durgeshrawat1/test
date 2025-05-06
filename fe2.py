# streamlit_app.py

import streamlit as st
import os

# --- Import backend logic ---
# Ensure rag_backend.py is in the same directory or Python path
try:
    import rag_backend
except ImportError:
    st.error("Failed to import rag_backend.py. Make sure it's in the same directory.")
    st.stop()


# --- Page Configuration ---
st.set_page_config(
    page_title="AWS RAG Chatbot UI",
    page_icon="🚀",
    layout="centered",
)
st.title("🚀 RAG Chatbot Interface")
st.caption("Powered by AWS Bedrock and Amazon DocumentDB")

# --- Initialize Clients via Backend Functions (Cached by Streamlit) ---
# Streamlit uses st.secrets to provide environment variables to the imported backend.
# The backend's os.environ.get() will pick these up.

@st.cache_resource # Cache the client objects for the session
def get_backend_clients():
    """Gets initialized Bedrock and DocumentDB clients from the backend script."""
    st.write("Attempting to initialize backend clients (Bedrock & DocumentDB)...")
    # The backend script's init functions use print statements for logging.
    # Streamlit will capture these if run from the same process or you can adapt logging.
    bedrock_client = rag_backend.init_bedrock_client_backend()
    docdb_collection = rag_backend.init_docdb_collection_backend()

    if bedrock_client:
        st.success("Bedrock client connected successfully.")
    else:
        st.error("Failed to connect to Bedrock. Check backend logs/configurations and Streamlit secrets.")

    if docdb_collection:
        st.success("DocumentDB collection connected successfully.")
    else:
        st.error("Failed to connect to DocumentDB. Check backend logs/configurations, CA cert, and Streamlit secrets.")
    return bedrock_client, docdb_collection

bedrock_runtime_client, docdb_collection_client = get_backend_clients()


# --- Streamlit Chat UI ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I assist you with the information in our database today?"}]

# Display existing messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# Only enable chat input if clients are ready
chat_input_disabled = not (bedrock_runtime_client and docdb_collection_client)
if chat_input_disabled:
    st.warning("Chat is disabled because one or more backend services (AWS Bedrock, DocumentDB) could not be initialized. Please check configurations in `secrets.toml` and ensure backend services are accessible.")

if prompt := st.chat_input("Your question:", disabled=chat_input_disabled):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking... (Performing RAG search and generation)"):
            # Call the backend's RAG function
            response = rag_backend.perform_rag_backend(
                bedrock_runtime=bedrock_runtime_client,
                docdb_collection=docdb_collection_client,
                user_query=prompt
            )
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})


# --- Sidebar for Configuration Info (from backend's perspective) ---
with st.sidebar:
    st.header("Backend Configuration Info")
    st.caption("Values are read from environment variables by the backend script, informed by Streamlit secrets.")
    st.markdown(f"**Bedrock Region:** `{os.environ.get('BEDROCK_REGION', 'Not Set')}`")
    st.markdown(f"**Embedding Model:** `{os.environ.get('EMBEDDING_MODEL_ID', 'Not Set')}`")
    st.markdown(f"**LLM Model:** `{os.environ.get('LLM_MODEL_ID', 'Not Set')}`")
    st.markdown(f"**DocDB Endpoint:** `{os.environ.get('DOCDB_ENDPOINT', 'Not Set')}`")
    st.markdown(f"**DocDB Database:** `{os.environ.get('DOCDB_DB_NAME', 'Not Set')}`")
    st.markdown(f"**DocDB Collection:** `{os.environ.get('DOCDB_COLLECTION_NAME', 'Not Set')}`")
    st.markdown(f"**CA Cert Path:** `{os.environ.get('DOCDB_CA_CERT_PATH', 'Not Set')}`")
    st.markdown(f"**DocDB Vector Index:** `{os.environ.get('DOCDB_INDEX_NAME', 'Not Set')}`")

    if not bedrock_runtime_client or not docdb_collection_client:
        st.warning("Review client initialization messages above.")
    else:
        st.success("Backend clients appear to be initialized.")
