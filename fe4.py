import streamlit as st
from your_rag_module import perform_rag
import datetime

# Page config
st.set_page_config(
    page_title="Document RAG System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject black-and-white theme
def inject_custom_css():
    st.markdown(f"""
    <style>
        html, body {{
            background-color: #ffffff;
            color: #000000;
        }}

        .stTextInput input {{
            background-color: #ffffff;
            color: #000000;
            border-radius: 5px;
            padding: 12px;
            border: 1px solid #000000;
        }}

        .stButton>button {{
            background-color: #000000;
            color: #ffffff;
            border-radius: 5px;
            padding: 10px 24px;
            border: none;
        }}

        .stButton>button:hover {{
            background-color: #444444;
        }}

        .chat-message {{
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
            max-width: 80%;
            border: 1px solid #000;
        }}

        .user-message {{
            background-color: #f5f5f5;
            margin-left: auto;
        }}

        .assistant-message {{
            background-color: #e0e0e0;
            margin-right: auto;
        }}

        .history-card {{
            background-color: #ffffff;
            border-radius: 8px;
            padding: 1rem;
            margin: 1rem 0;
            border: 1px solid #ccc;
        }}

        [data-testid="stSidebar"] {{
            background-color: #f8f8f8 !important;
        }}

        .stAlert {{
            border-radius: 8px;
            background-color: #f9f9f9;
            color: #000;
        }}

        .stSpinner>div {{
            border-color: #000000 transparent transparent transparent !important;
        }}
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# Initialize state
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

# Sidebar
with st.sidebar:
    st.markdown("<h1 style='color: black;'>⚙️ Configuration</h1>", unsafe_allow_html=True)
    top_k = st.slider("Number of search results", 1, 10, 3)
    
    st.markdown("---")
    if st.button("🗑️ Clear Conversation History"):
        st.session_state.conversation_history = []
        st.rerun()
    
    st.markdown("---")
    st.markdown("""
    <div style="color: #666;">
        <small>Powered by:</small>
        <br>
        <img src="https://upload.wikimedia.org/wikipedia/commons/9/93/Amazon_Web_Services_Logo.svg" 
             width="120" 
             style="margin-top: 10px;">
    </div>
    """, unsafe_allow_html=True)

# Header
st.markdown("<h1 style='text-align: center; color: black;'>📚 Document Intelligence Assistant</h1>", unsafe_allow_html=True)
st.markdown("<div style='text-align: center; margin-bottom: 2rem; color: #666;'>Ask questions about your documents</div>", unsafe_allow_html=True)

# Chat input
user_query = st.chat_input("Type your question here...")

# Process input
if user_query:
    with st.spinner("🔍 Searching documents..."):
        try:
            response = perform_rag(user_query, top_k=top_k)
            
            st.session_state.conversation_history.append({
                "content": user_query,
                "role": "user",
                "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
            })
            st.session_state.conversation_history.append({
                "content": response,
                "role": "assistant",
                "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
            })
        except Exception as e:
            st.session_state.conversation_history.append({
                "content": f"Error: {str(e)}",
                "role": "error",
                "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
            })

# Display history
if st.session_state.conversation_history:
    for msg in st.session_state.conversation_history:
        if msg["role"] == "user":
            st.markdown(f"""
            <div class="chat-message user-message">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
