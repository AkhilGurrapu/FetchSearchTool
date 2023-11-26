import streamlit as st
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer

indexName = "offer_search"

def create_es_index(es_client):
    # Defining index mappings
    indexMapping = {
        "properties": {
            "Offer": {
                "type": "text"
            },
            "Brand": {
                "type": "text"
            },
            "Category": {
                "type": "text"
            },
            "Retailer": {
                "type": "text"
            },
            "BRANDVECTOR": {
                "type": "dense_vector",
                "dims": 768,
                "index": True,
                "similarity": "l2_norm"
            },
            "CATEGORYVECTOR": {
                "type": "dense_vector",
                "dims": 768,
                "index": True,
                "similarity": "l2_norm"
            },
            "RETAILERVECTOR": {
                "type": "dense_vector",
                "dims": 768,
                "index": True,
                "similarity": "l2_norm"
            }
        }
    }
    # Create the index if it doesn't exist
    if not es_client.indices.exists(index=indexName):
        es_client.indices.create(index=indexName, mappings=indexMapping)

# Initializing Elasticsearch client
try:
    es = Elasticsearch(
        "https://localhost:9200",
        basic_auth=("elastic", "password"),
        ca_certs="path to http_ca.crt"
    )
    if not es.ping():
        st.error("Cannot connect to Elasticsearch!")
    else:
        create_es_index(es)
except Exception as e:
    st.error(f"Connection Error: {e}")

model = SentenceTransformer('all-mpnet-base-v2')

def search(input_keyword):
    
    vector_of_input_query = model.encode(input_keyword)

    # Performing KNN search for BrandVector
    brand_query = {
        "field": "BRANDVECTOR",
        "query_vector": vector_of_input_query,
        "k": 4,
        "num_candidates": 1000,
    }
    brand_hits = es.knn_search(index="offer_search", knn=brand_query, _source=["OFFER", 'BRAND'])["hits"]["hits"]

    # Performing KNN search for CategoryVector
    category_query = {
        "field": "CATEGORYVECTOR",
        "query_vector": vector_of_input_query,
        "k": 4,
        "num_candidates": 1000,
    }
    category_hits = es.knn_search(index="offer_search", knn=category_query, _source=["OFFER","CATEGORY"])["hits"]["hits"]

    # Performing KNN search for RetailerVector
    retailer_query = {
        "field": "RETAILERVECTOR",
        "query_vector": vector_of_input_query,
        "k": 4,
        "num_candidates": 1000,
    }
    retailer_hits = es.knn_search(index="offer_search", knn=retailer_query, _source=["OFFER","RETAILER"])["hits"]["hits"]

    # Combining results from all three searches
    combined_results = brand_hits + category_hits + retailer_hits

    aggregated_results = {}
    for hit in combined_results:
        doc_id = hit['_id']
        if doc_id not in aggregated_results:
            aggregated_results[doc_id] = {
                "score": hit['_score'],
                "source": hit['_source'],
                "count": 1
            }
        else:
            aggregated_results[doc_id]["score"] += hit['_score']
            aggregated_results[doc_id]["count"] += 1

    # Normalizes scores by count and sort the results
    final_results = sorted(aggregated_results.values(), key=lambda x: x["score"] / x["count"], reverse=True)
    return [result for result in final_results]

def main():
    st.title("Fetch Offers Search Engine")

    # Input: User enters search query
    search_query = st.text_input("Enter your search query")

    # Button: User triggers the search
    if st.button("Search"):
        if search_query:

            try:
            # Perform the search and get results
                results = search(search_query)

                # Display search results
                st.subheader("Search Results")
                table_data = []
                for result in results:
                    data_row = {}
                    if 'source' in result:
                        offer = result['source'].get('OFFER', 'No Offer Details')
                        data_row['Offer'] = offer

                        # if 'BRAND' in result['source']:
                        #     data_row['Brand'] = result['source']['BRAND']

                        # if 'CATEGORY' in result['source']:
                        #     data_row['Category'] = result['source']['CATEGORY']

                        # if 'RETAILER' in result['source']:
                        #     data_row['Retailer'] = result['source']['RETAILER']

                        data_row['Score'] = round(result['score'] / result['count'], 2)
                        table_data.append(data_row)

                # Display table
                if table_data:
                    st.table(table_data)
                else:
                    st.write("No results found")
            except Exception as e:
                st.error(f"Error: {e}")

if __name__ == "__main__":
    main()
