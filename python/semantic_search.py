
import os
import pickle
import sqlite3
import pandas as pd
import numpy as np
import sys
import json
import re

# Ensure project root is in path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

import config
from search_engine import tokenize, custom_tokenizer, DOMAIN_MAP
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class SemanticSearch:
    def __init__(self, vectorizer_path=None, matrix_path=None, shop_ids_path=None):
        # Use config for paths if not provided
        self.vectorizer_path = vectorizer_path or os.path.join(config.MODELS_DIR, "tfidf_vectorizer.pkl")
        self.matrix_path = matrix_path or os.path.join(config.MODELS_DIR, "tfidf_matrix.pkl")
        self.shop_ids_path = shop_ids_path or os.path.join(config.MODELS_DIR, "shop_ids.pkl")
        
        self.vectorizer = None
        self.tfidf_matrix = None
        self.shop_ids = None

    def get_data_from_db(self, db_path=None):
        db_path = db_path or config.DB_PATH
        conn = sqlite3.connect(db_path)
        query = """
            SELECT 
                s.id as shop_id,
                s.name as shop_name, 
                s.products as shop_products,
                GROUP_CONCAT(t.name, ' ') as tag_names,
                GROUP_CONCAT(t.name_bn, ' ') as tag_names_bn
            FROM shops s
            LEFT JOIN shop_tags st ON s.id = st.shop_id
            LEFT JOIN tags t ON st.tag_id = t.id
            GROUP BY s.id
        """
        try:
            df = pd.read_sql_query(query, conn)
        except Exception as e:
            print(f"Error reading from DB: {e}")
            df = pd.DataFrame()
        finally:
            conn.close()
        return df

    def prepare_data(self, df):
        # Index on Name + Products + Tags
        df['text'] = (
            df['shop_name'].fillna('') + " " + 
            df['shop_products'].fillna('') + " " + 
            df['tag_names'].fillna('') + " " + 
            df['tag_names_bn'].fillna('')
        )
        df = df[df['text'].str.strip() != ""]
        return df

    def build_index(self, db_path=None):
        db_path = db_path or config.DB_PATH
        print(f"Fetching data from live database ({db_path}) for semantic index...")
        df = self.get_data_from_db(db_path)
        
        if df.empty:
            print("No data found to build index.")
            return

        df_clean = self.prepare_data(df)
        X_text = df_clean['text'].tolist()
        self.shop_ids = df_clean['shop_id'].tolist()
        
        print(f"Indexing {len(X_text)} shops...")

        # Train Vectorizer
        self.vectorizer = TfidfVectorizer(
            tokenizer=custom_tokenizer, 
            token_pattern=None, 
            ngram_range=(1, 1), 
            max_features=10000
        )
        
        # Build TF-IDF Matrix
        self.tfidf_matrix = self.vectorizer.fit_transform(X_text)
        
        print("Indexing complete.")
        self.save()

    def search(self, query, top_k=20):
        """
        Returns list of dicts: {'shop_id': id, 'score': similarity_score}
        """
        if self.tfidf_matrix is None or self.vectorizer is None or self.shop_ids is None:
            self.load()
            if self.tfidf_matrix is None:
                return []

        query_vec = self.vectorizer.transform([query])
        
        # Calculate cosine similarity
        cosine_similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        
        # Get top indices
        related_docs_indices = cosine_similarities.argsort()[:-top_k:-1]
        
        results = []
        for idx in related_docs_indices:
            score = cosine_similarities[idx]
            if score > 0.001: 
                results.append({
                    "shop_id": self.shop_ids[idx],
                    "score": round(float(score), 4)
                })
        
        return results

    def save(self):
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.vectorizer_path), exist_ok=True)
        
        with open(self.vectorizer_path, 'wb') as f:
            pickle.dump(self.vectorizer, f)
        with open(self.matrix_path, 'wb') as f:
            pickle.dump(self.tfidf_matrix, f)
        with open(self.shop_ids_path, 'wb') as f:
            pickle.dump(self.shop_ids, f)
        print(f"Semantic Search Index saved to {os.path.dirname(self.vectorizer_path)}")

    def load(self):
        try:
            with open(self.vectorizer_path, 'rb') as f:
                self.vectorizer = pickle.load(f)
            with open(self.matrix_path, 'rb') as f:
                self.tfidf_matrix = pickle.load(f)
            with open(self.shop_ids_path, 'rb') as f:
                self.shop_ids = pickle.load(f)
        except Exception:
            # print("Index files not found or corrupted.")
            pass

if __name__ == "__main__":
    # Build index if run directly
    ss = SemanticSearch()
    ss.build_index()

