import pandas as pd
import re

def parse_bank_statement(file_path):
    # Read the file
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Identify header - Line 2 seems to be the header
    # # D,ate,,Description,Chq/Ref. No.,Withdraw,al (Dr.) Deposit,(Cr.) Balanc,e
    
    data = []
    # Simple extraction: look for date patterns (e.g., 30,Sep,2025)
    date_regex = re.compile(r'^\d+\s+\d+,\w{3},202\d')
    
    current_row = None
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # Check if line starts with a sequence number followed by a date
        if date_regex.match(line):
            if current_row:
                data.append(current_row)
            
            parts = line.split(',')
            # Basic split: Seq Date (3 parts) Desc (rest)
            # This is hard due to bad CSV quoting
            # Manual patch for this specific format:
            current_row = {"Raw": line}
        elif current_row:
            # Append wrapped line to description
            current_row["Raw"] += " " + line
            
    if current_row:
        data.append(current_row)
        
    # More robust parsing for specific descriptions
    parsed_data = []
    for item in data:
        raw = item["Raw"]
        
        # Extract amount (usually the second to last or last numeric value)
        amounts = re.findall(r'(\d+[\.,]\d{2})', raw)
        desc = raw
        
        # Try to find vendor
        vendor = "Unknown"
        if "SWIGGY" in raw.upper(): vendor = "Swiggy"
        elif "BURGER KING" in raw.upper(): vendor = "Burger King"
        elif "STEAMGAMES" in raw.upper() or "STEAM PURCHASE" in raw.upper(): vendor = "Steam"
        elif "ORACLE" in raw.upper(): vendor = "Oracle Cloud"
        elif "COUNTRYDELIGHT" in raw.upper(): vendor = "Country Delight"
        elif "PAYTM" in raw.upper(): vendor = "Paytm"
        elif "AMITY" in raw.upper(): vendor = "Amity University"
        elif "CASHBACK" in raw.upper(): vendor = "Cashback"
        elif "KOTAK811" in raw.upper(): vendor = "Self/Kotak"
        
        parsed_data.append({"Description": raw, "Vendor": vendor})
        
    df = pd.DataFrame(parsed_data)
    summary = df['Vendor'].value_counts()
    print("--- Vendor Summary ---")
    print(summary)
    
    print("\n--- Potentially Unrecognized (Tech/Cloud) ---")
    tech = df[df['Vendor'] == 'Oracle Cloud']
    for d in tech['Description'].unique():
        print(f"- {d[:100]}...")

if __name__ == "__main__":
    parse_bank_statement("/home/sloth/educational/ita-tax-project/data/processed/Bank Statement.csv")
