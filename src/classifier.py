import pandas as pd
import numpy as np
import re
from src.model import TransactionClassifier
from src.logger import logger

# Initialize AI Brain
ai_brain = TransactionClassifier()

def clean_statement_csv(file_path):
    """
    Super-Robust Cleaner: Finds the actual table using fuzzy matching, 
    fixes headers, and cleans numbers.
    """
    logger.info(f"Cleaning file: {file_path}")
    try:
        # Read without headers initially to capture everything
        df = pd.read_csv(file_path, header=None)
    except Exception as e:
        logger.error(f"Could not read CSV: {e}")
        return None

    # --- 1. SUPER-ROBUST HEADER DETECTION ---
    header_idx = -1
    for idx, row in df.iterrows():
        # Convert row to a single lowercase string (e.g., "date description withdrawal")
        row_text = " ".join(row.astype(str)).lower()
        
        # Check if it contains 'date' AND ('description' OR 'particulars')
        has_date = 'date' in row_text
        has_desc = any(x in row_text for x in ['description', 'particulars', 'narration', 'details'])
        
        if has_date and has_desc:
            header_idx = idx
            logger.debug(f"Found Header at Row {idx}: {row_text[:50]}...")
            break
    
    if header_idx != -1:
        # Set this row as the header
        df.columns = df.iloc[header_idx].astype(str).str.strip()
        df = df.iloc[header_idx+1:].reset_index(drop=True)
    else:
        logger.warning("Header not found. Using fallback column names.")
        df.columns = [f"Col_{i}" for i in range(len(df.columns))]

    # --- 2. SMART COLUMN MAPPING ---
    col_map = {}
    for col in df.columns:
        c = col.lower()
        if 'date' in c: col_map[col] = 'Date'
        elif any(x in c for x in ['description', 'particulars', 'narration', 'details']): col_map[col] = 'Description'
        # Check for 'dr' (debit) or 'withdrawal'
        elif any(x in c for x in ['debit', 'withdrawal', 'dr.']): col_map[col] = 'Withdrawal'
        # Check for 'cr' (credit) or 'deposit'
        elif any(x in c for x in ['credit', 'deposit', 'cr.']): col_map[col] = 'Deposit'

    df.rename(columns=col_map, inplace=True)

    # --- 3. SAFETY NET: Ensure Columns Exist ---
    if 'Withdrawal' not in df.columns: df['Withdrawal'] = 0.0
    if 'Deposit' not in df.columns: df['Deposit'] = 0.0
    
    # If Description is missing, pick the column with the longest text
    if 'Description' not in df.columns:
        desc_col = df.astype(str).apply(lambda x: x.str.len()).mean().idxmax()
        df.rename(columns={desc_col: 'Description'}, inplace=True)

    # --- 4. ROBUST NUMBER CLEANING ---
    def clean_money(val):
        if pd.isna(val) or val == '': return 0.0
        s = str(val).replace(',', '').strip()
        # Remove everything that isn't a digit or a dot
        s = re.sub(r'[^\d.]', '', s)
        try:
            return float(s)
        except:
            return 0.0

    df['Withdrawal'] = df['Withdrawal'].apply(clean_money)
    df['Deposit'] = df['Deposit'].apply(clean_money)

    # --- 5. REMOVE JUNK ROWS ---
    # Keep rows where at least one money column has a value > 0
    original_count = len(df)
    df = df[(df['Withdrawal'] > 0) | (df['Deposit'] > 0)]
    logger.info(f"Extracted {len(df)} valid transactions from {original_count} raw rows.")
    
    return df.reset_index(drop=True)

def tag_transactions(df):
    """Tags transactions using Regex Rules + AI Prediction + Pseudo-RAG Knowledge Base."""
    logger.info("Classifying transactions via Cognitive Pipeline...")
    
    # 1. Load Knowledge Base
    import json
    import os
    kb_path = os.path.join("data", "tax_knowledge.json")
    kb = {}
    if os.path.exists(kb_path):
        with open(kb_path, 'r') as f:
            kb = json.load(f)

    def get_category(desc):
        d = str(desc).upper()
        # Fast Regex Tier
        if any(x in d for x in ["AMITY", "LIC", "PPF", "TUITION", "SCHOOL"]): return "80C_INVEST"
        if any(x in d for x in ["AKSHAT", "NEFT", "IMPS", "CREDIT", "UPI-RECEIVE"]): return "BUSINESS_REV"
        if any(x in d for x in ["SALARY", "ACH CREDIT", "TCS", "WIPRO"]): return "SALARY"
        if any(x in d for x in ["SWIGGY", "NETFLIX", "ZOMATO", "UBER", "STARBUCKS", "STEAM"]): return "PERSONAL"
        if any(x in d for x in ["ZERODHA", "GROWW", "UPSTOX", "KITE"]): return "STCG"
        if any(x in d for x in ["SELF", "OWN A/C", "TRANSFER TO"]): return "SELF_TRANSFER"
        return "UNCATEGORIZED"

    # Initialize columns if they don't exist
    if 'Tax_Category' not in df.columns:
        df['Tax_Category'] = "UNCATEGORIZED"
    if 'Confidence_Score' not in df.columns:
        df['Confidence_Score'] = 0.0
    if 'Source' not in df.columns:
        df['Source'] = "Unknown"

    # Only process rows that are still UNCATEGORIZED
    mask = df['Tax_Category'] == 'UNCATEGORIZED'
    
    # 2. Heuristic Tier for Uncategorized
    df.loc[mask, 'Tax_Category'] = df.loc[mask, 'Description'].apply(get_category)
    df.loc[mask, 'Confidence_Score'] = 1.0
    df.loc[mask, 'Source'] = "Heuristic"

    # 3. Sequential Inference Tier (for items still uncategorized after regex)
    for idx, row in df[df['Tax_Category'] == 'UNCATEGORIZED'].iterrows():
        desc = str(row['Description'])
        
        # Tier A: Neural Prediction
        cat, conf = ai_brain.predict(desc)
        if conf > 0.85:
            df.at[idx, 'Tax_Category'] = cat
            df.at[idx, 'Confidence_Score'] = conf
            df.at[idx, 'Source'] = "Neural"
        else:
            # Tier B: Pseudo-RAG Semantic Search
            rag_cat, rag_sim = ai_brain.semantic_search(desc, kb)
            if rag_sim > 0.70:
                df.at[idx, 'Tax_Category'] = rag_cat
                df.at[idx, 'Confidence_Score'] = rag_sim
                df.at[idx, 'Source'] = "Knowledge-Augmented"
    
    # 4. Confidence Calibration (Entropy) for all AI-tagged rows
    ai_mask = df['Source'].isin(["Neural", "Knowledge-Augmented"])
    for idx, row in df[ai_mask].iterrows():
        desc = str(row['Description'])
        entropy = ai_brain.calculate_entropy(desc)
        if entropy > 1.5:  # High uncertainty threshold
            df.at[idx, 'Source'] += " (Uncertain)"

    logger.info(f"Classification complete. Sources: {df['Source'].value_counts().to_dict()}")
    return df

def train_model(texts, labels):
    """
    Exposes the training function to the GUI.
    texts: list of description strings
    labels: list of category strings
    """
    if not texts or not labels: return
    logger.info(f"Training AI with {len(texts)} new examples...")
    ai_brain.train(texts, labels)
    logger.info("AI Training Complete & Saved.")

def interactive_classification(df):
    """Human-in-the-Loop Training."""
    unknowns = df[df['Tax_Category'] == 'UNCATEGORIZED']
    
    if unknowns.empty:
        return df

    print(f"\n--- 🤖 Human Help Needed ({len(unknowns)} items) ---")
    
    TAX_CATS = {
        "1": "BUSINESS_REV", "2": "BUSINESS_EXP", "3": "SALARY",
        "4": "80C_INVEST", "5": "STCG", "6": "LTCG", 
        "7": "PERSONAL", "8": "SELF_TRANSFER"
    }
    
    updates = {}
    
    # Ask for max 5 items
    unique_desc = unknowns['Description'].unique()
    for desc in unique_desc[:5]: 
        print(f" ? What is: '{str(desc)[:50]}...'?")
        print("   [1] Biz Inc [2] Biz Exp [3] Salary [4] 80C")
        print("   [5] STCG    [6] LTCG    [7] Person [8] Self")
        
        choice = input(" > Choice: ").strip()
        if choice in TAX_CATS:
            selected_cat = TAX_CATS[choice]
            updates[desc] = selected_cat
            ai_brain.train([desc], [selected_cat])
            logger.info(f"User trained AI: {desc[:20]}... -> {selected_cat}")

    for idx, row in df.iterrows():
        if row['Description'] in updates:
            df.at[idx, 'Tax_Category'] = updates[row['Description']]
            
    return df
