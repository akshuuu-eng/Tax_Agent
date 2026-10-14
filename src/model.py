import os
import pickle
import numpy as np
from sklearn.linear_model import SGDClassifier

# Try to use Transformers for Embeddings
try:
    from sentence_transformers import SentenceTransformer
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

# Path where the "Brain" is saved
MODEL_PATH = os.path.join("data", "model.pkl")

class TransactionClassifier:
    def __init__(self):
        # Transformer-based Feature Extractor
        if HAS_TRANSFORMERS:
            # Using a lightweight transformer model (all-MiniLM-L6-v2)
            self.transformer = SentenceTransformer('all-MiniLM-L6-v2')
        else:
            self.transformer = None
            
        self.clf = SGDClassifier(loss='log_loss', penalty='l2')
        self.is_trained = False
        
        # --- THE 8 CORE CATEGORIES ---
        self.classes_ = [
            "BUSINESS_REV",    # Business Income
            "BUSINESS_EXP",    # Business Expense
            "SALARY",          # Form 16 Income
            "80C_INVEST",      # LIC/PPF/Tuition
            "STCG",            # Short Term Capital Gains
            "LTCG",            # Long Term Capital Gains
            "PERSONAL",        # Netflix/Swiggy
            "SELF_TRANSFER"    # Contra Entries
        ]
        
        # Load existing brain if it exists
        if os.path.exists(MODEL_PATH):
            try:
                with open(MODEL_PATH, 'rb') as f:
                    self.pipeline, self.is_trained = pickle.load(f)
            except:
                pass

    def train(self, X_text_list, y_category_list):
        """Teaches the AI with new examples using Transformer embeddings."""
        if not X_text_list:
            return

        if HAS_TRANSFORMERS and self.transformer:
            # 1. Transform text into Transformer Embeddings
            X_vectors = self.transformer.encode(X_text_list)
        else:
            # Simple fallback for training (rarely used if deps are present)
            return

        # 2. Now feed the EMBEDDINGS into the classifier
        self.clf.partial_fit(X_vectors, y_category_list, classes=self.classes_)
        
        self.is_trained = True
        
        # Save the updated brain
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        with open(MODEL_PATH, 'wb') as f:
            # We don't pickle the transformer itself (too big), just the head
            pickle.dump((self.clf, self.is_trained), f)

    def semantic_search(self, query, knowledge_base):
        """
        Pseudo-RAG: Performs a high-dimensional similarity search 
        between the query and the knowledge base.
        """
        if not HAS_TRANSFORMERS or not self.transformer:
            return None, 0.0

        query_vec = self.transformer.encode([query])[0]
        best_match = None
        max_sim = -1.0

        for cat, info in knowledge_base.items():
            # Combine description and keywords for a rich semantic target
            target_text = f"{info['description']} {' '.join(info['keywords'])}"
            target_vec = self.transformer.encode([target_text])[0]
            
            # Cosine Similarity
            sim = np.dot(query_vec, target_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(target_vec))
            
            if sim > max_sim:
                max_sim = sim
                best_match = cat
        
        return best_match, float(max_sim)

    def calculate_entropy(self, text):
        """
        Calculates the Predictor Entropy to determine classification uncertainty.
        High entropy = Low confidence.
        """
        if not self.is_trained:
            return 1.0
        
        X_vector = self.transformer.encode([text])
        probs = self.clf.predict_proba(X_vector)[0]
        # Shannon Entropy
        entropy = -np.sum(probs * np.log2(probs + 1e-9))
        return float(entropy)

    def predict(self, text):
        """Guesses the category using Transformer + SGD Head."""
        if not self.is_trained or not HAS_TRANSFORMERS or not self.transformer:
            return "UNCATEGORIZED", 0.0
        
        try:
            X_vector = self.transformer.encode([text])
            prediction = self.clf.predict(X_vector)[0]
            confidence = self.clf.predict_proba(X_vector).max()
            return prediction, float(confidence)
        except Exception as e:
            from src.logger import logger
            logger.error(f"Prediction error: {e}")
            return "UNCATEGORIZED", 0.0
