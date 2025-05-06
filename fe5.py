import streamlit as st
from your_rag_module import perform_rag
import datetime

# Page setup
st.set_page_config(
    page_title="DocuQuery",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject minimalist, responsive styling
def apply_minimal_style():
    st.markdown("""
    <style>
        html, body, [class*="css"] {
            font-family: 'Segoe UI', sans-serif;
            color: #2c3e50;
        }

        .block-container {
            padding-left: 3rem !important;
            padding-right: 3rem !important;
            max-width: 100% !important;
        }

        .stTextInput input {
            border: 1px solid #ccc;
            border-radius: 6px;
            padding: 12px;
            width: 100%;
        }

        .stButton > button {
            background-color: #000;
            color: #fff;
            border: none;
            border-radius: 6px;
            padding: 0.5rem 1rem;
        }

        .user-message, .assistant-message {
            padding: 1rem;
            margin: 1rem 0;
            border-radius: 6px;
            border: 1px solid #ccc;
            width: 100%;
            word-wrap: break-word;
            white-space: pre-wrap;
        }

        .user-message {
            background-color: #f5f5f5;
        }

        .assistant-message {
            background-color: #eaeaea;
        }

        .history-item {
            padding: 0.5rem 0;
            border-bottom: 1px solid #ddd;
        }

        [data-testid="stSidebar"] {
            background-color: #f8f9fa;
            border-right: 1px solid #eee;
        }

        .stAlert {
            background-color: #f8d7da !important;
            border-color: #f5c6cb !important;
            color: #721c24 !important;
        }
    </style>
    """, unsafe_allow_html=True)

apply_minimal_style()

# Init history
if "history" not in st.session_state:
    st.session_state.history = []

# Sidebar: History
with st.sidebar:
    st.markdown("### Conversation History")
    if st.button("Clear History", use_container_width=True):
        st.session_state.history = []

    st.markdown("---")
    for item in reversed(st.session_state.history):
        st.markdown(f"""
        <div class="history-item">
            <small>{item['time']}</small><br>
            <strong>Q:</strong> {item['query']}<br>
            <strong>A:</strong> {item['response']}
        </div>
        """, unsafe_allow_html=True)

# Main interface
st.title("🔍 DocuQuery")
st.markdown("Ask questions about your documents below.")
st.markdown("---")

# Text input
query = st.text_input("Enter your question:", placeholder="Type your question here...", label_visibility="collapsed")

# If user submits a query
if query:
    with st.spinner("Analyzing documents..."):
        try:
            response = perform_rag(query)

            st.session_state.history.append({
                "query": query,
                "response": response,
                "time": datetime.datetime.now().strftime("%H:%M:%S")
            })

            # Display latest messages
            st.markdown(f"""
            <div class="user-message"><strong>👤 You:</strong><br>{query}</div>
            <div class="assistant-message"><strong>🤖 Assistant:</strong><br>{response}</div>
            """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error: {str(e)}")

# Initial prompt
if not st.session_state.history:
    st.markdown("""
    <div style='text-align: center; margin-top: 2rem; color: #888;'>
        <h3>🚀 Start by asking a question</h3>
        <p>This assistant can answer queries based on your documents.</p>
    </div>
    """, unsafe_allow_html=True)
