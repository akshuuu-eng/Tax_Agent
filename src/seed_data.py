import sys
import os

# --- FIX: Add the project root to Python's path ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.model import TransactionClassifier

def initialize_brain():
    print("🧠 Waking up the AI Brain...")
    brain = TransactionClassifier()
    
    # --- 1. PERSONAL EXPENSES (Based on your statement) ---
    personal_keywords = [
        "SWIGGY", "ZOMATO", "BLINKIT", "ZEPTO", "COUNTRY DELIGHT",
        "BURGER KING", "DOMINOS", "SUBWAY", "MCDONALDS", "KFC", "PIZZA",
        "STEAMGAMES", "VALVE", "PLAYSTATION", "NETFLIX", "SPOTIFY",
        "FLIPKART", "AMAZON", "MYNTRA", "UNIQLO", "AJIO", "H&M",
        "UBER", "OLA", "RAPIDO", "METRO",
        "BSES", "AIRTEL", "JIO", "VI", "SMARTQ", "AMITYTULIP", "CANVA",
        "TransportDepartment"
    ]
    
    # --- 2. BUSINESS REVENUE (Inflows) ---
    biz_rev_keywords = [
        "AKSHAT TIMBER", 
        "NEFT", "IMPS", "RTGS", 
        "BHARATPE", "PAYTMQR", 
        "VINAY VERMA", "SUNIL KUMAR", "MADHUBALA", "SACHIN SHARMA"
    ]

    # --- 3. 80C INVESTMENTS (Education & Tax) ---
    invest_keywords = [
        "AMITY UNIVERSITY", "AMITY", "TUITION",
        "LIC", "MAX LIFE", "HDFC LIFE", "INSURANCE",
        "PPF", "PROVIDENT FUND"
    ]

    # --- 4. PREPARE TRAINING DATA ---
    X_train = []
    y_train = []

    print(f" [*] Loading {len(personal_keywords)} Personal patterns...")
    for k in personal_keywords:
        X_train.append(k)
        y_train.append("PERSONAL")

    print(f" [*] Loading {len(biz_rev_keywords)} Business patterns...")
    for k in biz_rev_keywords:
        X_train.append(k)
        y_train.append("BUSINESS_REV")

    print(f" [*] Loading {len(invest_keywords)} Investment patterns...")
    for k in invest_keywords:
        X_train.append(k)
        y_train.append("80C_INVEST")

    # --- 5. EXECUTE TRAINING ---
    brain.train(X_train, y_train)
    print(" ✅ AI Training Complete! It now knows your specific vendors.")

if __name__ == "__main__":
    initialize_brain()
