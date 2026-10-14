import os
import sys
import glob
import pandas as pd

# Setup Path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

try:
    from src.onboarding import create_onboarding_kit
    # --- SWITCH TO NEURAL PARSER (Crucial Change) ---
    from src.neural_parser import parse_with_neural_engine
    from src.classifier import tag_transactions, interactive_classification
    from src.tax_engine import calculate_tax
except ImportError as e:
    print(f"[CRITICAL] Import failed: {e}")
    sys.exit(1)

def main():
    print("\n" + "="*50)
    print(" 🏛️  INTELLIGENT TAX ASSISTANT (NEURAL ENGINE)")
    print("="*50)
    
    # --- STEP 1: SMART ONBOARDING ---
    target_path = create_onboarding_kit()
    if not target_path: return

    # --- STEP 2: SCAN DOCUMENTS ---
    pdf_files = glob.glob(os.path.join(target_path, "*.pdf"))
    if not pdf_files:
        print(f"[!] No PDFs found in {target_path}")
        return

    full_financial_data = []

    for pdf in pdf_files:
        try:
            print(f"--- Processing: {os.path.basename(pdf)} ---")
            
            # A. Extract using Neural Pattern Recognition
            # This ignores invisible columns and reads text flow (Perfect for your PDF)
            df_clean = parse_with_neural_engine(pdf)
            
            if df_clean is None or df_clean.empty: 
                print(" [!] No transactions found.")
                continue

            # B. Classification (AI + Regex)
            df_tagged = tag_transactions(df_clean)
            
            # C. Human Verification
            df_final = interactive_classification(df_tagged)
            
            full_financial_data.append(df_final)

        except Exception as e:
            print(f"[ERROR] Failed on {os.path.basename(pdf)}: {e}")

    # --- STEP 3: CALCULATE TAX ---
    if full_financial_data:
        print("\n[*] Consolidating all data...")
        master_df = pd.concat(full_financial_data, ignore_index=True)
        calculate_tax(master_df)
    else:
        print("[!] No data available.")

if __name__ == "__main__":
    main()
