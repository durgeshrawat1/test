# app.py
import streamlit as st
from your_rag_module import perform_rag
import datetime

# Custom dark theme styling
st.set_page_config(
    page_title="Document RAG System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

def inject_custom_css():
    st.markdown(f"""
    <style>
        /* Main theme colors */
        :root {{
            --primary: #2E86C1;
            --background: #1A1A1A;
            --secondary: #2C3E50;
            --text: #ECF0F1;
            --accent: #16A085;
        }}

        /* Base styling */
        body {{
            background-color: var(--background);
            color: var(--text);
        }}

        /* Text input styling */
        .stTextInput input {{
            background-color: {st.get_option('theme.secondaryBackgroundColor')};
            color: var(--text);
            border-radius: 15px;
            padding: 12px;
            border: 1px solid var(--primary);
        }}

        /* Button styling */
        .stButton>button {{
            background-color: var(--primary);
            color: white;
            border-radius: 15px;
            padding: 10px 24px;
            border: none;
            transition: all 0.3s;
        }}

        .stButton>button:hover {{
            background-color: #2471A3;
            transform: scale(1.05);
        }}

        /* Chat message styling */
        .chat-message {{
            padding: 1.5rem;
            border-radius: 15px;
            margin: 1rem 0;
            max-width: 80%;
        }}

        .user-message {{
            background-color: var(--secondary);
            margin-left: auto;
        }}

        .assistant-message {{
            background-color: #34495E;
            margin-right: auto;
        }}

        /* History card styling */
        .history-card {{
            background-color: {st.get_option('theme.backgroundColor')};
            border-radius: 15px;
            padding: 1.5rem;
            margin: 1rem 0;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s;
        }}

        .history-card:hover {{
            transform: translateY(-3px);
        }}

        /* Sidebar styling */
        [data-testid="stSidebar"] {{
            background-color: #2C3E50 !important;
        }}

        /* Error message styling */
        .stAlert {{
            border-radius: 15px;
        }}

        /* Spinner styling */
        .stSpinner>div {{
            border-color: var(--primary) transparent transparent transparent !important;
        }}
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# Initialize session state
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

# Sidebar configuration
with st.sidebar:
    st.markdown("<h1 style='color: var(--primary);'>⚙️ Configuration</h1>", unsafe_allow_html=True)
    top_k = st.slider("Number of search results", 1, 10, 3)
    
    st.markdown("---")
    
    if st.button("🗑️ Clear Conversation History"):
        st.session_state.conversation_history = []
        st.rerun()

    st.markdown("---")
    st.markdown("""
    <div style="color: #7F8C8D;">
        <small>Powered by:</small>
        <br>
        <img src="https://upload.wikimedia.org/wikipedia/commons/9/93/Amazon_Web_Services_Logo.svg" 
             width="120" 
             style="margin-top: 10px;">
    </div>
    """, unsafe_allow_html=True)

# Main interface
st.markdown("<h1 style='color: var(--primary); text-align: center;'>📚 Document Intelligence Assistant</h1>", unsafe_allow_html=True)
st.markdown("<div style='text-align: center; margin-bottom: 2rem; color: #7F8C8D;'>Ask questions about your documents</div>", unsafe_allow_html=True)

# Chat input
user_query = st.chat_input("Type your question here...")

# Process query
if user_query:
    with st.spinner("🔍 Searching documents..."):
        try:
            response = perform_rag(user_query, top_k=top_k)
            
            history_entry = {
                "query": user_query,
                "response": response,
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "type": "assistant"
            }
            
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
            st.error(f"Error processing query: {str(e)}")
            st.session_state.conversation_history.append({
                "content": f"Error: {str(e)}",
                "role": "error",
                "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
            })

# Display conversation
if st.session_state.conversation_history:
    for msg in st.session_state.conversation_history:
        if msg["role"] == "user":
            with st.container():
                st.markdown(f"""
                <div class="chat-message user-message">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <strong>👤 You</strong>
                        <small style="color: #7F8C8D;">{msg['timestamp']}</small>
                    </div>
                    <div>{msg['content']}</div>
                </div>
                """, unsafe_allow_html=True)
        
        elif msg["role"] == "assistant":
            with st.container():
                st.markdown(f"""
                <div class="chat-message assistant-message">
                    <div style="display: flex; justify-space-between; margin-bottom: 8px;">
                        <strong>🤖 Assistant</strong>
                        <small style="color: #7F8C8D;">{msg['timestamp']}</small>
                    </div>
                    <div>{msg['content']}</div>
                </div>
                """, unsafe_allow_html=True)
        
        elif msg["role"] == "error":
            st.error(f"""
            <div style="padding: 1rem; border-radius: 15px;">
                ⚠️ {msg['content']}
                <br>
                <small>{msg['timestamp']}</small>
            </div>
            """, unsafe_allow_html=True)

else:
    st.markdown("""
    <div style="text-align: center; margin-top: 3rem; color: #7F8C8D;">
        <h3>🚀 Get Started</h3>
        <p>Ask a question about your documents to begin!</p>
    </div>
    """, unsafe_allow_html=True)

# Instructions to run
# pip install streamlit
# streamlit run app.py
