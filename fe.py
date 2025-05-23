# Updated Streamlit code that works with your current implementation
import streamlit as st
from your_rag_module import perform_rag  # Import your existing function
import datetime

# Custom CSS styling
st.set_page_config(
    page_title="Document RAG System",
    page_icon="🔍",
    layout="wide"
)

def inject_custom_css():
    st.markdown("""
    <style>
        .stTextInput input {border-radius: 20px; padding: 12px;}
        .stButton button {border-radius: 20px; padding: 12px 24px;}
        .history-card {border: 1px solid #e0e0e0; border-radius: 10px; padding: 15px; margin: 10px 0;}
        .result-card {background-color: #f8f9fa; border-radius: 10px; padding: 20px; margin: 15px 0;}
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# Session state initialization
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

# Sidebar configuration
with st.sidebar:
    st.title("Configuration ⚙️")
    top_k = st.slider("Number of search results", 1, 10, 3)
    show_debug = st.checkbox("Show debug info")
    st.divider()
    
    if st.button("Clear History 🗑️"):
        st.session_state.conversation_history = []
        st.experimental_rerun()

# Main interface
st.title("Document RAG System 🔍")
st.markdown("### Ask questions about your documents")

# Chat input
user_query = st.text_input("Enter your question:", placeholder="Type your question here...")

# Process query
if user_query:
    with st.spinner("Searching documents and generating answer..."):
        try:
            # Execute your existing RAG pipeline
            response = perform_rag(user_query, top_k=top_k)
            
            # Store results in session state
            history_entry = {
                "query": user_query,
                "response": response,
                "timestamp": str(datetime.datetime.now())
            }
            
            st.session_state.conversation_history.append(history_entry)

        except Exception as e:
            st.error(f"Error processing query: {str(e)}")

# Display results
if st.session_state.conversation_history:
    st.markdown("---")
    st.markdown("### Latest Response")
    
    latest = st.session_state.conversation_history[-1]
    with st.container():
        st.markdown(f"**Question:** {latest['query']}")
        st.markdown(f"**Answer:** {latest['response']}")  # Directly access string response

# Instructions to run
# pip install streamlit
# streamlit run app.py
