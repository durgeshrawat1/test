def search_documentdb(query_embedding, k=5):
    if not query_embedding or not isinstance(query_embedding, list):
        print("ERROR: Invalid query embedding")
        return []

    pipeline = [
        {
            '$search': {
                'vectorSearch': {
                    'index': DOCDB_INDEX_NAME,
                    'path': DOCDB_VECTOR_FIELD,
                    'vector': query_embedding,
                    'similarity': 'cosine',  # Must match index metric
                    'k': k,
                    'efSearch': 64           # For HNSW (remove if using IVFFlat)
                }
            }
        },
        {
            '$project': {
                '_id': 0,
                'text': f'${DOCDB_TEXT_FIELD}',
                'metadata': f'${DOCDB_METADATA_FIELD}'
            }
        }
    ]

    try:
        results = list(collection.aggregate(pipeline))
        # Add manual similarity calculation here
        return results
    except pymongo.errors.OperationFailure as e:
        # Handle errors...
