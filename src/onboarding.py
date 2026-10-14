import os
import sys
import platform
import time
from pathlib import Path

def get_desktop_path():
    """Finds the Desktop path safely on Windows/Mac/Linux."""
    return Path.home() / "Desktop"

def ask_choice(question):
    """
    Asks a Yes/No question using simple numbers (1 or 2).
    """
    print(f"\n{question}")
    print(" [1] Yes")
    print(" [2] No")
    
    while True:
        choice = input(" > Enter Choice (1-2): ").strip()
        if choice == '1':
            return True
        elif choice == '2':
            return False
        else:
            print(" [!] Invalid input. Please enter 1 or 2.")

def create_onboarding_kit():
    print("\n" + "="*60)
    print(" 👋 WELCOME TO YOUR TAX ASSISTANT")
    print("="*60)
    print(" I will prepare a custom document checklist for you.\n")
    
    client_name = input(" > First, what is your name? ").strip()
    if not client_name: client_name = "User"

    # --- 1. THE ADAPTIVE INTERVIEW ---
    checklist_data = []
    
    # --- MANDATORY DOCS ---
    # Only Bank Statement is required for the code to run
    checklist_data.append(("Bank Statement", ["bank", "stmt"], "bank_statement.pdf"))

    # --- OPTIONAL DOCS ---
    # Q1: KYC Documents (Optional)
    if ask_choice("[1/7] Do you want to upload KYC Docs (PAN/Aadhaar)?"):
        checklist_data.append(("PAN Card", ["pan"], "pan_card.pdf"))
        checklist_data.append(("Aadhaar Card", ["aadhaar", "uid"], "aadhaar.pdf"))

    # Q2: Salary
    if ask_choice("[2/7] Do you have a salaried job (Form 16)?"):
        checklist_data.append(("Form 16", ["16", "salary", "form16"], "form16.pdf"))
    
    # Q3: Business
    if ask_choice("[3/7] Do you run a Business?"):
        checklist_data.append(("GST Returns", ["gst", "3b"], "gst_return.pdf"))
        checklist_data.append(("Business Expenses", ["bill", "invoice", "expense"], "expenses.pdf"))
    
    # Q4: Freelance
    if ask_choice("[4/7] Do you do Freelance work?"):
        checklist_data.append(("Invoices/Receipts", ["invoice", "receipt"], "invoices.pdf"))
    
    # Q5: Stocks
    if ask_choice("[5/7] Did you sell Stocks/Crypto?"):
        checklist_data.append(("Capital Gains Report", ["capital", "gain", "zerodha"], "capital_gains.pdf"))

    # Q6: Rent
    if ask_choice("[6/7] Do you pay House Rent?"):
        checklist_data.append(("Rent Receipts", ["rent", "landlord"], "rent_receipts.pdf"))

    # Q7: Insurance
    if ask_choice("[7/7] Do you pay Life/Medical Insurance?"):
        checklist_data.append(("80C/80D Proofs", ["lic", "ppf", "insurance"], "insurance.pdf"))

    # --- 2. CREATE THE "MAGIC FOLDER" ---
    folder_name = f"Tax_Docs_{client_name.replace(' ', '_')}"
    folder_path = get_desktop_path() / folder_name
    
    try:
        os.makedirs(folder_path, exist_ok=True)
        
        # Create instructions
        with open(folder_path / "REQUIRED_DOCUMENTS.txt", "w") as f:
            f.write(f"DOCUMENT CHECKLIST FOR: {client_name.upper()}\n")
            f.write("="*60 + "\n")
            f.write(" IMPORTANT: Please rename your files as shown below before uploading.\n")
            f.write(" This helps our AI identify them correctly.\n")
            f.write("="*60 + "\n\n")
            
            for i, (item, _, target) in enumerate(checklist_data, 1):
                f.write(f"[ ] {item:<25} -> Rename to: {target}\n")

        # Open Folder Automatically
        if platform.system() == "Windows": os.startfile(folder_path)
        elif platform.system() == "Darwin": os.system(f"open '{folder_path}'")
        else: os.system(f"xdg-open '{folder_path}'")

        print(f"\n[*] Created folder: {folder_name}")
        print("[*] I have opened the folder for you.")
        print("-" * 60)
        print(" ⚠️  INSTRUCTION: Please rename your files before uploading!")
        print("    Example: Rename 'Scan_001.pdf' -> 'bank_statement.pdf'")
        print("-" * 60)

    except Exception as e:
        print(f"[!] Error creating folder: {e}")
        return str(folder_path)

    # --- 3. VERIFICATION LOOP ---
    while True:
        print("\n" + "="*50)
        print(" ⏳  Waiting for files... (Press [ENTER] to scan)")
        input("    (Make sure you renamed them correctly!)")
        print("=" * 50)
        
        try:
            uploaded_files = [f for f in os.listdir(folder_path) if f.endswith('.pdf')]
        except:
            print("[!] Folder missing!")
            break
        
        if not uploaded_files:
            print(" [!] Folder is empty.")
            continue
            
        print(f" [*] Found {len(uploaded_files)} file(s). Checking names...\n")
        
        missing_count = 0
        
        for doc_name, keywords, target_name in checklist_data:
            found = False
            match_name = ""
            
            for f in uploaded_files:
                if f.lower() == target_name.lower():
                    found = True; match_name = f; break
                elif any(k in f.lower() for k in keywords):
                    found = True; match_name = f; break
            
            if found:
                print(f" ✅ {doc_name:<25} -> Found ('{match_name}')")
            else:
                print(f" ❌ {doc_name:<25} -> MISSING (Expected: '{target_name}')")
                missing_count += 1
        
        print("-" * 50)
        
        if missing_count == 0:
            print("\n 🎉 PERFECT! All files match the naming convention.")
            time.sleep(1)
            break
        else:
            print(f"\n ⚠️  You are missing {missing_count} documents.")
            choice = input("    Try again? (y/n): ").lower()
            if choice == 'n':
                print("[*] Proceeding with what we have...")
                break
    
    return str(folder_path)

if __name__ == "__main__":
    create_onboarding_kit()

