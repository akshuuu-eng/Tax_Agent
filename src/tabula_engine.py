import tabula
import pandas as pd
import numpy as np

def parse_with_tabula(pdf_path):
    print(f" [TABULA ENGINE] 🧱 Scanning {pdf_path} using Grid Analysis...")
    
    try:
        # 1. THE MAGIC COMMAND
        # strict=True tells it to strictly follow grid lines (perfect for bank tables)
        # pages='all' scans the whole file
        # stream=True forces it to look for whitespace columns (solves the "merged text" bug)
        dfs = tabula.read_pdf(pdf_path, pages='all', stream=True, guess=True)
        
        if not dfs:
            print(" [ERROR] Tabula found no tables.")
            return None
            
        print(f" [TABULA ENGINE] Found {len(dfs)} table fragments. Merging...")
        
        # 2. MERGE ALL PAGES
        raw_df = pd.concat(dfs, ignore_index=True)
        
        # 3. CLEAN UP HEADERS (The "Smart" Part)
        # Tabula sometimes reads the header as the first row of data. 
        # We standardise it.
        
        # Create a clean bucket for data
        clean_rows = []
        
        # Iterate through what Tabula found
        for idx, row in raw_df.iterrows():
            row_list = row.astype(str).tolist()
            row_str = " ".join(row_list).lower()
            
            # Skip junk rows (Headers/Page Numbers)
            if "date" in row_str and "balance" in row_str:
                continue 
            if "opening balance" in row_str:
                continue
            if "page" in row_str and "of" in row_str:
                continue
                
            # EXTRACT DATA (Heuristic Mapping)
            # We look for the columns based on position (Index 0, 1, etc.)
            # This works because Tabula preserves column order perfectly.
            
            try:
                # Get the raw values, removing 'nan'
                vals = [x for x in row_list if x != 'nan' and x.lower() != 'nan']
                
                if len(vals) < 3: continue # Skip empty/short rows
                
                # Intelligent Column Guesser
                date_val = vals[0] # Date is usually first
                desc_val = " ".join(vals[1:-2]) # Description is in the middle
                
                # The last two numbers are usually Amount and Balance
                # We need to figure out which is Withdrawal/Deposit
                
                # Clean the money numbers
                def clean_money(v):
                    return float(str(v).replace(',', '').replace('Cr', '').replace('Dr', ''))
                
                money_1 = 0.0
                money_2 = 0.0
                
                try: money_1 = clean_money(vals[-2])
                except: pass
                
                try: money_2 = clean_money(vals[-1]) # Usually Balance
                except: pass
                
                # LOGIC: 
                # In most statements: [Withdrawal] [Deposit] [Balance]
                # If only one money column has a value, Tabula might shift it.
                # For this demo, let's assume the detected money is a Withdrawal unless it says "Cr"
                
                withdrawal = money_1
                deposit = 0.0
                
                # If the description says "Credit" or "Deposit", swap it
                if "credit" in row_str or "deposit" in row_str or "cr" in row_str:
                    deposit = money_1
                    withdrawal = 0.0
                
                clean_rows.append({
                    "Date": date_val,
                    "Description": desc_val,
                    "Withdrawal": withdrawal,
                    "Deposit": deposit
                })
                
            except:
                continue

        df_final = pd.DataFrame(clean_rows)
        print(f" [SUCCESS] Tabula extracted {len(df_final)} clean transactions.")
        return df_final

    except Exception as e:
        print(f" [ERROR] Tabula failed: {e}")
        return None

