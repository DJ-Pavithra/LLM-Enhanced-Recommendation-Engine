import pickle
import asyncio
import os
import numpy as np
import faiss
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.decomposition import TruncatedSVD
from scipy.sparse import csr_matrix
from app.core.config import settings

class HybridRecommender:
    def __init__(self):
        self.svd_model = None
        self.sentence_model = None
        self.faiss_index = None
        self.product_map = {}  # Map internal ID (index) to StockCode
        self.reverse_product_map = {} # StockCode to internal ID
        self.product_data = {} # Metadata
        self.user_map = {} # UserID to internal Index
        self.reverse_user_map = {} # Internal Index to UserID
        self.initialized = False

    def load_models(self):
        """Load pre-trained models from disk."""
        try:
            print("Loading ML models...")
            # Load SVD
            with open(os.path.join(settings.MODEL_PATH, "svd_model.pkl"), "rb") as f:
                model_data = pickle.load(f)
                self.svd_model = model_data["model"]
                self.user_factors = model_data["user_factors"]
                self.user_map = model_data["user_map"]
                self.reverse_user_map = model_data["reverse_user_map"]
            
            # Load FAISS
            self.faiss_index = faiss.read_index(os.path.join(settings.MODEL_PATH, "product.index"))
            
            # Load Metadata/Mappings
            with open(os.path.join(settings.MODEL_PATH, "mappings.pkl"), "rb") as f:
                mappings = pickle.load(f)
                self.product_map = mappings["product_map"]
                self.reverse_product_map = mappings["reverse_product_map"]
                self.product_data = mappings["product_data"]
            
            # Load Sentence Transformer (cached)
            self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            self.initialized = True
            print("Models loaded successfully.")
        except FileNotFoundError:
            print("Models not found. Training needed.")
            # Initialize with basics if training not done
            self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')

    async def train(self, transactions_df, products_df):
        """Train SVD (sklearn) and build FAISS index."""
        print("Starting training (in thread)...")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._train_sync, transactions_df, products_df)

    def _train_sync(self, transactions_df, products_df):
        # ... logic moved here ...
        print("Starting synchronous training...")
        
        # 1. Collaborative Filtering (SVD via Scikit-Learn)
        unique_users = transactions_df['user_id'].unique()
        
        # Map User and Item IDs
        self.user_map = {uid: i for i, uid in enumerate(unique_users)}
        self.reverse_user_map = {i: uid for i, uid in enumerate(unique_users)}
        
        item_codes = products_df['_id'].tolist()
        self.reverse_product_map = {code: i for i, code in enumerate(item_codes)}
        self.product_map = {i: code for i, code in enumerate(item_codes)}
        
        transactions_df = transactions_df[transactions_df['stock_code'].isin(self.reverse_product_map)]
        
        user_indices = transactions_df['user_id'].map(self.user_map).fillna(-1).astype(int)
        item_indices = transactions_df['stock_code'].map(self.reverse_product_map).fillna(-1).astype(int)
        quantities = transactions_df['quantity'].apply(lambda x: np.log1p(x) if x > 0 else 0).values
        
        valid_mask = (user_indices >= 0) & (item_indices >= 0)
        
        interaction_matrix = csr_matrix(
            (quantities[valid_mask], (user_indices[valid_mask], item_indices[valid_mask])),
            shape=(len(unique_users), len(item_codes))
        )
        
        self.svd_model = TruncatedSVD(n_components=50, random_state=42)
        user_factors = self.svd_model.fit_transform(interaction_matrix)
        
        # 2. Content-Based (Embeddings + FAISS)
        products_df['description'] = products_df['description'].fillna("").astype(str)
        descriptions = products_df['description'].tolist()
        
        if not self.sentence_model:
            self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
            
        embeddings = self.sentence_model.encode(descriptions, show_progress_bar=True)
        dimension = embeddings.shape[1]
        
        self.faiss_index = faiss.IndexFlatL2(dimension)
        self.faiss_index.add(np.array(embeddings).astype('float32'))
        
        self.product_data = products_df.set_index('_id').to_dict(orient='index')
        self.user_factors = user_factors
        
        os.makedirs(settings.MODEL_PATH, exist_ok=True)
        
        with open(os.path.join(settings.MODEL_PATH, "svd_model.pkl"), "wb") as f:
            pickle.dump({
                "model": self.svd_model,
                "user_factors": user_factors,
                "user_map": self.user_map,
                "reverse_user_map": self.reverse_user_map
            }, f)
            
        faiss.write_index(self.faiss_index, os.path.join(settings.MODEL_PATH, "product.index"))
        
        with open(os.path.join(settings.MODEL_PATH, "mappings.pkl"), "wb") as f:
            pickle.dump({
                "product_map": self.product_map,
                "reverse_product_map": self.reverse_product_map,
                "product_data": self.product_data
            }, f)
            
        print("Training complete and models saved.")
        self.initialized = True

    def recommend(self, user_id, top_k=10):
        """Hybrid Recommendation."""
        if not self.initialized:
            print("Recommender not initialized.")
            try:
                self.load_models()
            except:
                pass
            if not self.initialized:
                return []
            
        if user_id not in self.user_map:
            return [] 
            
        user_idx = self.user_map[user_id]
        
        # User Factors (1, 50) @ Item Factors (50, n_items) => (1, n_items)
        if not hasattr(self, 'user_factors'):
            return []
            
        user_vector = self.user_factors[user_idx]
        item_matrix = self.svd_model.components_
        
        scores = np.dot(user_vector, item_matrix)
        
        # Get Top K indices
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            stock_code = self.product_map.get(idx)
            if stock_code:
                results.append({
                    "stock_code": stock_code,
                    "score": float(scores[idx]),
                    "name": self.product_data.get(stock_code, {}).get('description')
                })
        return results

    def search(self, query, top_k=5):
        """Semantic search using FAISS."""
        if not self.initialized:
            print("Recommender not initialized.")
            try:
                self.load_models()
            except:
                pass
            if not self.initialized:
                return []
            
        if not self.sentence_model or not self.faiss_index:
             return []

        query_vector = self.sentence_model.encode([query])
        distances, indices = self.faiss_index.search(np.array(query_vector).astype('float32'), top_k)
        
        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx in self.product_map: # Check if index is valid
                stock_code = self.product_map[idx]
                results.append({
                    "stock_code": stock_code,
                    "description": self.product_data.get(stock_code, {}).get('description', 'Unknown'),
                    "score": float(dist) 
                })
        return results

recommender = HybridRecommender()
