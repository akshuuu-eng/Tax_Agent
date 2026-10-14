import pdfplumber
import pandas as pd
import os

def detect_bank_strategy(pdf):
    """
    Scans the first page to guess the Bank and returns specific table settings.
    """
    try:
        text = pdf.pages[0].extract_text().upper()
    except:
        # If extraction fails, assume standard text
        return {"vertical_strategy": "text", "horizontal_strategy": "lines"}

    if "KOTAK" in text:
        return {"vertical_strategy": "text", "horizontal_strategy": "lines"}
    elif "HDFC" in text:
        return {"vertical_strategy": "lines", "horizontal_strategy": "lines"}
    elif "SBI" in text:
        return {"vertical_strategy": "text", "horizontal_strategy": "text"}
    
    # Default Fallback for unknown banks
    return {"vertical_strategy": "text", "horizontal_strategy": "lines"}

def convert_pdf_to_csv(pdf_path):
    """
    Converts PDF to CSV. 
    Feature 1: Handles Passwords 
    Feature 2: Detects Scanned Files
    """
    base_name = os.path.basename(pdf_path).replace(".pdf", ".csv")
    output_path = os.path.join("data", "processed", base_name)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    print(f"[*] Extracting: {os.path.basename(pdf_path)}")
    all_rows = []
    password = None # Start with no password
    
    while True:
        try:
            # Try opening (with password if set)
            with pdfplumber.open(pdf_path, password=password) as pdf:
                
                # --- CHECK 1: IS IT SCANNED? ---
                try:
                    first_page_text = pdf.pages[0].extract_text()
                except:
                    first_page_text = ""
                    
                if not first_page_text or len(first_page_text.strip()) < 10:
                    print(" [!] ERROR: This looks like a Scanned Image PDF.")
                    print("     This system requires digital PDFs from Net Banking.")
                    return None
                
                # --- CHECK 2: DETECT BANK ---
                settings = detect_bank_strategy(pdf)
                
                # --- EXTRACT TABLES ---
                for page in pdf.pages:
                    table = page.extract_table(table_settings=settings)
                    if table:
                        # Clean empty rows/cells
                        clean_rows = [
                            row for row in table 
                            if any(cell and str(cell).strip() != "" for cell in row)
                        ]
                        all_rows.extend(clean_rows)
            
            # If successful, break the loop
            break

        except Exception as e:
            # --- CHECK 3: HANDLE PASSWORDS ---
            error_msg = str(e).lower()
            if "password" in error_msg or "decryption" in error_msg:
                print(f" 🔒 This PDF is Password Protected.")
                password = input("    Enter PDF Password to unlock: ").strip()
                print("    Retrying...")
                continue # Loop back and try again with the new password
            else:
                print(f"[ERROR] Extraction failed: {e}")
                return None

    if not all_rows:
        print("[!] No table data found in PDF. Format might be unsupported.")
        return None

    # Save Raw Data
    df = pd.DataFrame(all_rows)
    df.to_csv(output_path, index=False, header=False)
    return output_path
