# --------------------------------------------------------------------------
# RAG System using AWS Bedrock and Amazon DocumentDB (with MongoDB compat.)
# --------------------------------------------------------------------------
# Prerequisites:
# 1. Install libraries: pip install boto3 pymongo
# 2. Configure AWS credentials (IAM role, environment variables, etc.)
# 3. Download DocumentDB CA certificate (e.g., global-bundle.pem)
# 4. Replace placeholder values in the Configuration section below.
# 5. Ensure DocumentDB cluster is v5.0+ and supports vector search.
# 6. Ensure the vector index 'rag_vector_index' (or your configured name)
#    exists on the vector field in your collection.
# --------------------------------------------------------------------------

import boto3
import pymongo
import json
import os
import sys

# --- Configuration ---
# Replace these placeholders with your actual values or use environment variables
BEDROCK_REGION = 'us-east-1' # Or your preferred Bedrock region

# Best practice: Use environment variables or AWS Secrets Manager for credentials
DOCDB_USER = os.environ.get("DOCDB_USER", "your_docdb_user")
DOCDB_PASSWORD = os.environ.get("DOCDB_PASSWORD", "your_docdb_password")
DOCDB_ENDPOINT = os.environ.get("DOCDB_ENDPOINT", "your-docdb-cluster-endpoint:port") # e.g., mycluster.cluster-xxxx.us-east-1.docdb.amazonaws.com:27017
DOCDB_DB_NAME = "your_database_name"
DOCDB_COLLECTION_NAME = "your_collection_name"
DOCDB_CA_CERT_PATH = "global-bundle.pem" # Path to your downloaded CA certificate

# Vector Search Configuration
DOCDB_INDEX_NAME = "rag_vector_index"      # Name of your vector index in DocumentDB
DOCDB_VECTOR_FIELD = "embedding"           # Field in your documents storing the 1024-dim vector
DOCDB_TEXT_FIELD = "text_chunk"            # Field storing the original text chunk corresponding to the vector
DOCDB_METADATA_FIELD = "metadata"          # Optional: Field storing metadata (source, document_id, etc.)

# Bedrock Model IDs
EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v1" # Embedding model used

# --- Choose your LLM - PAY ATTENTION TO API DIFFERENCES IN get_llm_response ---
# LLM_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0" # Example: Claude 3 Sonnet
# LLM_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"  # Example: Claude 3 Haiku
LLM_MODEL_ID = "anthropic.claude-v2"                 # Example: Claude 2
# LLM_MODEL_ID = "amazon.titan-text-express-v1"       # Example: Titan Text Express
# LLM_MODEL_ID = "ai21.j2-ultra-v1"                   # Example: AI21 Jurassic-2 Ultra (Check API format)
# LLM_MODEL_ID = "cohere.command-text-v14"            # Example: Cohere Command (Check API format)

# --- End Configuration ---


# --- Initialize AWS Bedrock Client ---
try:
    bedrock_runtime = boto3.client(
        service_name='bedrock-runtime',
        region_name=BEDROCK_REGION
    )
    print(f"Bedrock runtime client initialized successfully in region '{BEDROCK_REGION}'.")
except Exception as e:
    print(f"ERROR: Failed to initialize Bedrock client: {e}")
    sys.exit(1) # Exit if Bedrock client fails

# --- Initialize DocumentDB Client ---
docdb_client = None # Initialize to None
try:
    if not os.path.exists(DOCDB_CA_CERT_PATH):
         print(f"ERROR: DocumentDB CA certificate not found at '{DOCDB_CA_CERT_PATH}'.")
         print("Please download it from AWS and place it in the correct path or update DOCDB_CA_CERT_PATH.")
         sys.exit(1)

    docdb_connection_string = (
        f"mongodb://{DOCDB_USER}:{DOCDB_PASSWORD}@"
        f"{DOCDB_ENDPOINT}/?tls=true&tlsCAFile={DOCDB_CA_CERT_PATH}"
        f"&replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false"
    )
    print("Connecting to DocumentDB...")
    docdb_client = pymongo.MongoClient(docdb_connection_string)
    db = docdb_client[DOCDB_DB_NAME]
    collection = db[DOCDB_COLLECTION_NAME]
    # Test connection by getting server info
    server_info = docdb_client.server_info()
    print(f"DocumentDB connection successful. Server version: {server_info.get('version')}")
    # Check if the specified collection exists (optional but good practice)
    if DOCDB_COLLECTION_NAME not in db.list_collection_names():
        print(f"Warning: Collection '{DOCDB_COLLECTION_NAME}' not found in database '{DOCDB_DB_NAME}'. Searches will likely fail.")

except pymongo.errors.ConfigurationError as e:
    print(f"ERROR: DocumentDB configuration error (check connection string, username, password, CA path): {e}")
    sys.exit(1)
except pymongo.errors.ConnectionFailure as e:
    print(f"ERROR: Could not connect to DocumentDB at '{DOCDB_ENDPOINT}'. Check endpoint, network access, credentials, and TLS settings. Details: {e}")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: An unexpected error occurred during DocumentDB connection: {e}")
    if docdb_client:
        docdb_client.close()
    sys.exit(1)


# --- Bedrock Embedding Function ---
def generate_embedding(text_input):
    """Generates embedding for the given text using Bedrock Titan Text."""
    if not text_input or not isinstance(text_input, str):
        print("ERROR: Invalid input provided for embedding generation.")
        return None
    try:
        payload = json.dumps({"inputText": text_input})
        response = bedrock_runtime.invoke_model(
            body=payload,
            modelId=EMBEDDING_MODEL_ID,
            accept='application/json',
            contentType='application/json'
        )
        response_body = json.loads(response.get('body').read())
        embedding = response_body.get('embedding')
        if not embedding or not isinstance(embedding, list):
             print(f"ERROR: Could not extract valid embedding from Bedrock response: {response_body}")
             return None
        # Optional: Add check for expected dimension (1024)
        # if len(embedding) != 1024:
        #    print(f"Warning: Embedding dimension mismatch. Expected 1024, got {len(embedding)}")
        return embedding
    except Exception as e:
        # Catch specific Bedrock exceptions if needed, e.g., botocore.exceptions.ClientError
        print(f"ERROR generating embedding using '{EMBEDDING_MODEL_ID}': {e}")
        return None


# --- DocumentDB Vector Search Function ---
def search_documentdb(query_embedding, k=5):
    """Performs vector search in DocumentDB using $vectorSearch."""
    if not query_embedding or not isinstance(query_embedding, list):
        print("ERROR: Invalid or missing query embedding provided for search.")
        return []

    # Define the aggregation pipeline
    pipeline = [
        {
            '$vectorSearch': {
                'index': DOCDB_INDEX_NAME,         # Your vector index name
                'path': DOCDB_VECTOR_FIELD,        # Field containing the vectors
                'queryVector': query_embedding,    # The vector generated from the user query
                'numCandidates': k * 15,           # Number of candidates to consider (adjust as needed)
                'limit': k                         # Number of top results to return
                # 'filter': { 'metadata.category': 'some_category' } # Optional: Add metadata filters here
            }
        },
        {
            '$project': {                          # Specify fields to return
                '_id': 0,                          # Exclude the default _id field
                'text': f'${DOCDB_TEXT_FIELD}',    # Retrieve the original text chunk
                'metadata': f'${DOCDB_METADATA_FIELD}', # Retrieve metadata (if field exists)
                'score': { '$meta': 'vectorSearchScore' } # Retrieve the similarity score
            }
        }
    ]

    try:
        results = list(collection.aggregate(pipeline))
        return results
    except pymongo.errors.OperationFailure as e:
        # Provide more specific feedback for common errors
        if "index not found" in str(e):
             print(f"ERROR: DocumentDB index '{DOCDB_INDEX_NAME}' not found on field '{DOCDB_VECTOR_FIELD}'. Please create the index. Details: {e}")
        elif "$vectorSearch is not allowed" in str(e) or "Unrecognized pipeline stage name" in str(e):
             print(f"ERROR: $vectorSearch may not be enabled or supported. Ensure you are using DocumentDB 5.0+ instance-based cluster and the feature is active. Details: {e}")
        elif "queryVector" in str(e) and "dimensionality does not match" in str(e):
             print(f"ERROR: Query vector dimension ({len(query_embedding)}) does not match index dimension. Check embedding model and index definition. Details: {e}")
        else:
            print(f"ERROR during DocumentDB vector search aggregation: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred during DocumentDB search: {e}")
        return []


# --- Bedrock LLM Invocation Function ---
def get_llm_response(prompt, model_id=LLM_MODEL_ID):
    """Gets response from the Bedrock LLM, handling different API formats."""
    if not prompt or not isinstance(prompt, str):
        print("ERROR: Invalid or missing prompt provided for LLM invocation.")
        return None

    try:
        # --- CLAUDE 3.x / 3.5 (Messages API) ---
        if "anthropic.claude-3" in model_id:
            messages = [{"role": "user", "content": prompt}]
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31", # Required for Messages API
                "max_tokens": 1024,         # Max tokens to generate
                "messages": messages,
                "temperature": 0.1,         # Controls randomness (lower means more deterministic)
                "top_p": 0.9,               # Controls diversity via nucleus sampling
                # "system": "Optional system prompt here" # Use if needed
            })
            accept = "application/json"
            contentType = "application/json"
            response = bedrock_runtime.invoke_model(body=body, modelId=model_id, accept=accept, contentType=contentType)
            response_body = json.loads(response.get("body").read())
            if response_body.get("content") and isinstance(response_body["content"], list) and len(response_body["content"]) > 0:
                 return response_body["content"][0].get("text")
            else:
                 print(f"ERROR: Unexpected Claude 3 response format: {response_body}")
                 return None

        # --- CLAUDE 1.x / 2.x (Text Completion API) ---
        elif "anthropic.claude-v" in model_id:
             formatted_prompt = f"\n\nHuman:{prompt}\n\nAssistant:"
             body = json.dumps({
                "prompt": formatted_prompt,
                "max_tokens_to_sample": 512, # Max tokens for Claude 1/2
                "temperature": 0.1,
                "top_p": 0.9,
                # "stop_sequences": ["\n\nHuman:"] # Optional stop sequences
             })
             accept = "application/json"
             contentType = "application/json"
             response = bedrock_runtime.invoke_model(body=body, modelId=model_id, accept=accept, contentType=contentType)
             response_body = json.loads(response.get('body').read())
             return response_body.get('completion')

        # --- AMAZON TITAN TEXT (Express / Lite / etc.) ---
        elif "amazon.titan-text" in model_id:
             body = json.dumps({
                "inputText": prompt,
                 "textGenerationConfig": {
                     "maxTokenCount": 512,
                     "stopSequences": [],
                     "temperature": 0.1,
                     "topP": 0.9
                 }
             })
             accept = "application/json"
             contentType = "application/json"
             response = bedrock_runtime.invoke_model(body=body, modelId=model_id, accept=accept, contentType=contentType)
             response_body = json.loads(response.get('body').read())
             if response_body.get("results") and len(response_body["results"]) > 0:
                 return response_body["results"][0].get("outputText")
             else:
                  print(f"ERROR: Unexpected Titan Text response format: {response_body}")
                  return None

        # --- Add other model families here (e.g., Cohere, AI21) ---
        # elif "cohere.command" in model_id:
        #     # Add Cohere specific invoke_model structure
        #     print(f"ERROR: Cohere API handling not implemented yet for {model_id}")
        #     return None
        # elif "ai21.j2" in model_id:
        #     # Add AI21 specific invoke_model structure
        #     print(f"ERROR: AI21 API handling not implemented yet for {model_id}")
        #     return None

        else:
            print(f"ERROR: Unsupported LLM Model ID or API structure not implemented: {model_id}")
            return None

    except Exception as e:
        # Catch specific Bedrock exceptions if needed
        # Example: botocore.exceptions.ClientError and check e.response['Error']['Code']
        print(f"ERROR invoking LLM '{model_id}': {e}")
        return None

# --- RAG Orchestration Function ---
def perform_rag(user_query, top_k=3):
    """Executes the full RAG pipeline."""
    if not user_query or not isinstance(user_query, str):
        print("ERROR: Invalid user query provided.")
        return "Error: Please provide a valid question."

    print(f"\n--- Starting RAG for Query: '{user_query}' ---")

    # 1. Generate Query Embedding
    print(f"1. Generating query embedding using '{EMBEDDING_MODEL_ID}'...")
    query_embedding = generate_embedding(user_query)
    if not query_embedding:
        return "Error: Failed to generate query embedding. Cannot proceed with search."
    print(f"   Embedding generated (dimension: {len(query_embedding)}).")

    # 2. Perform Vector Search
    print(f"2. Searching DocumentDB index '{DOCDB_INDEX_NAME}' (top {top_k})...")
    search_results = search_documentdb(query_embedding, k=top_k)

    # 3. Prepare Context
    print("3. Preparing context...")
    context = ""
    if not search_results:
        print("   No relevant documents found in DocumentDB or search failed.")
        context = "No relevant context found in the database." # Provide specific info to LLM
    else:
        print(f"   Retrieved {len(search_results)} relevant document(s):")
        context_pieces = []
        for i, res in enumerate(search_results):
            text_content = res.get('text', '[No text content found]')
            score = res.get('score', -1.0) # Default score if missing
            metadata_info = res.get('metadata', '{}') # Default empty metadata
            print(f"      Result {i+1}: Score={score:.4f}, Metadata={metadata_info}, Text Snippet='{text_content[:100]}...'")
            context_pieces.append(text_content)
        context = "\n\n".join(context_pieces)
        print(f"   Context prepared (total length: {len(context)} chars).")

    # 4. Construct Prompt for the LLM
    print("4. Constructing prompt for LLM...")
    # This prompt template works reasonably well, but customize it for your specific needs and LLM.
    prompt = f"""You are an AI assistant. Your task is to answer the user's question based *only* on the following context provided.
Do not use any prior knowledge.
If the context does not contain enough information to answer the question, state clearly that you cannot answer based on the provided context.
Be concise and directly address the question.

Context:
--- START CONTEXT ---
{context}
--- END CONTEXT ---

Question: {user_query}

Answer:"""
    print("   Prompt constructed.")
    # print(f"   Prompt Snippet:\n{prompt[:500]}...") # Uncomment for debugging prompt

    # 5. Get LLM Response
    print(f"5. Sending prompt to LLM '{LLM_MODEL_ID}'...")
    final_answer = get_llm_response(prompt, LLM_MODEL_ID)
    print("   LLM response received.")

    # 6. Format and Return Result
    print("--- RAG complete ---")
    if final_answer:
        return final_answer.strip()
    else:
        # Provide a more informative error if LLM failed
        if not search_results:
             return "Could not find relevant information in the database and failed to generate a fallback response."
        else:
             return "Found relevant information, but encountered an error generating the final answer."


# --- Main Execution Block ---
if __name__ == "__main__":
    # Example usage:
    # Replace this with your actual user query input mechanism
    # example_query = "What are the benefits of using vector search?"
    # example_query = "Summarize the document about project Alpha."
    example_query = "What did the analysis reveal about market trends?"

    if len(sys.argv) > 1:
        # Allow passing query as a command-line argument
        example_query = " ".join(sys.argv[1:])

    print(f"\nProcessing query: '{example_query}'")
    print("=======================================")

    # Perform the RAG operation
    response = perform_rag(example_query, top_k=3) # Adjust top_k as needed

    print("\n=======================================")
    print("Final Answer:")
    print("=======================================")
    print(response)

    # Clean up the DocumentDB connection
    if docdb_client:
        try:
            docdb_client.close()
            print("\nDocumentDB connection closed.")
        except Exception as e:
            print(f"Error closing DocumentDB connection: {e}")
