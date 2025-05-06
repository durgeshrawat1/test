import streamlit as st
from your_rag_module import perform_rag
import datetime
import json
import os

HISTORY_FILE = "chat_history.json"

# Load chat history from file
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

# Save chat history to file
def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

# Page config
st.set_page_config(
    page_title="Document RAG System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Black-and-white theme
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
            width: 100%;
            border: 1px solid #000;
            box-sizing: border-box;
        }}

        .user-message {{
            background-color: #f5f5f5;
        }}

        .assistant-message {{
            background-color: #e0e0e0;
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
    st.session_state.conversation_history = load_history()

# Sidebar
with st.sidebar:
    st.markdown("<h1 style='color: black;'>⚙️ Configuration</h1>", unsafe_allow_html=True)
    top_k = st.slider("Number of search results", 1, 10, 3)

    st.markdown("---")
    if st.button("🗑️ Clear Conversation History"):
        st.session_state.conversation_history = []
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
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

            # Append to conversation
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

            # Save
            save_history(st.session_state.conversation_history)

        except Exception as e:
            st.session_state.conversation_history.append({
                "content": f"Error: {str(e)}",
                "role": "error",
                "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
            })
            save_history(st.session_state.conversation_history)

# Display history
if st.session_state.conversation_history:
    for msg in st.session_state.conversation_history:
        role_class = "user-message" if msg["role"] == "user" else "assistant-message"
        if msg["role"] == "error":
            st.error(f"""
            <div style="padding: 1rem;">
                ⚠️ {msg['content']}<br><small>{msg['timestamp']}</small>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="chat-message {role_class}">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <strong>{'👤 You' if msg['role'] == 'user' else '🤖 Assistant'}</strong>
                    <small style="color: #666;">{msg['timestamp']}</small>
                </div>
                <div>{msg['content']}</div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="text-align: center; margin-top: 3rem; color: #666;">
        <h3>🚀 Get Started</h3>
        <p>Ask a question about your documents to begin!</p>
    </div>
    """, unsafe_allow_html=True)
