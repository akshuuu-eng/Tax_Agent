import pdfplumber
import pandas as pd
import re
import os
from getpass import getpass
from src.logger import logger

# Try importing OCR dependencies
try:
    import pytesseract
    from pdf2image import convert_from_path
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("OCR Dependencies (pytesseract/pdf2image) not found. Scanned PDFs cannot be processed.")

# Delayed import to avoid circular dependency
def get_classifier():
    from src.classifier import tag_transactions
    return tag_transactions

def parse_with_neural_engine(pdf_path):
    logger.info(f"🧠 NEURAL ENGINE: Scanning {pdf_path}...")
    
    transactions = []
    pdf = None
    
    try:
        # 1. ATTEMPT OPENING
        try:
            pdf = pdfplumber.open(pdf_path)
        except Exception as e:
            if "password" in str(e).lower() or "authenticate" in str(e).lower():
                logger.warning("File is encrypted.")
                user_pass = getpass(" [PROMPT] Enter PDF Password: ")
                pdf = pdfplumber.open(pdf_path, password=user_pass)
            else:
                logger.error(f"PDF Initialization Failed: {str(e)}")
                return None

        # 2. VALIDATE PAGES
        if not pdf.pages:
            logger.error("PDF contains no pages.")
            return None

        # 3. TEXT EXTRACTION (Hybrid: Text -> OCR)
        full_text = ""
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text and len(text.strip()) > 50:
                full_text += text + "\n"
            else:
                logger.warning(f"Page {i+1} seems to be an image. Attempting OCR...")
                
                if OCR_AVAILABLE:
                    try:
                        # Convert specific page to image
                        # Note: poppler_path might need to be configured on Windows, but on Linux usually auto-detected
                        images = convert_from_path(pdf_path, first_page=i+1, last_page=i+1)
                        for img in images:
                            ocr_text = pytesseract.image_to_string(img)
                            full_text += ocr_text + "\n"
                        logger.info(f"OCR extracted {len(ocr_text)} chars from Page {i+1}")
                    except Exception as ocr_e:
                        logger.error(f"OCR Failed for Page {i+1}: {ocr_e}")
                        logger.info("Ensure 'poppler-utils' and 'tesseract-ocr' are installed.")
                else:
                    logger.error("OCR is not available (dependencies missing). Skipping page.")

        if not full_text.strip():
            logger.error("No extractable text found. If this is a scanned photo, ensure OCR is set up.")
            return None
            
        lines = full_text.split('\n')
        logger.info(f"Analyzing {len(lines)} text lines...")

        # 4. PATTERN RECOGNITION (REGEX)
        # Enhanced to be more robust for OCR noise
        date_pattern = re.compile(r'\b(\d{1,2}[-/\s][A-Za-z]{3}[-/\s]\d{2,4})\b')
        money_pattern = re.compile(r'[\d,]+\.\d{2}') # Matches 12,345.00

        current_txn = {}

        for line in lines:
            # Cleanup noise
            cleaned_line = line.strip()
            if not cleaned_line: continue

            match = date_pattern.search(cleaned_line)
            if match:
                if current_txn: transactions.append(current_txn)
                
                date_str = match.group(0)
                remaining = cleaned_line.replace(date_str, "")
                money = money_pattern.findall(remaining)
                
                val = 0.0
                if money:
                    # Heuristic: Usually the last money amount is the balance, second last is transaction amount
                    # But in statements, sometimes it's Credit | Debit | Balance.
                    # This logic is simplistic but works for many standard formats.
                    # OCR might introduce commas or dots wrongly.
                    amt_str = money[-1] if len(money) == 1 else money[-2] if len(money) > 1 else "0"
                    try:
                        val = float(amt_str.replace(',', ''))
                    except:
                        val = 0.0
                
                # Determine Dr/Cr
                is_deposit = any(x in cleaned_line.lower() for x in ["cr", "credit", "deposit"])
                
                current_txn = {
                    "Date": date_str,
                    "Description": re.sub(r'\s+', ' ', remaining).strip(),
                    "Withdrawal": val if not is_deposit else 0.0,
                    "Deposit": val if is_deposit else 0.0
                }
            elif current_txn:
                current_txn['Description'] += " " + cleaned_line

        if current_txn: transactions.append(current_txn)
        
        df = pd.DataFrame(transactions)
        if not df.empty:
            logger.info(f"SUCCESS: Reconstructed {len(df)} transactions.")
            # Real-time categorization
            try:
                tagger = get_classifier()
                df = tagger(df)
                logger.info("🧠 NEURAL ENGINE: Auto-categorized transactions via AI.")
            except Exception as e:
                logger.warning(f"AI Categorization during parsing failed: {e}")
            return df
        else:
            logger.error("Logic failed to find dates in text.")
            return None

    except Exception as e:
        logger.critical(f"System Crash in Parser: {str(e)}")
        return None
    finally:
        if pdf:
            pdf.close()
