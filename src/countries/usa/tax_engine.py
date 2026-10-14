import os
import pandas as pd
from typing import Dict, List, Any
from src.core.tax_interface import BaseTaxEngine

class USATaxEngine(BaseTaxEngine):
    """
    Tax Engine for the United States (Federal Income Tax).
    Implements standard vs itemized deduction logic, 401(k), HSA, and tax brackets.
    """
    
    @property
    def country_name(self) -> str:
        return "USA"

    @property
    def currency_symbol(self) -> str:
        return "$"

    def get_supported_years(self) -> list[str]:
        return ["2024"]

    def set_tax_year(self, year: str) -> None:
        pass

    def get_financial_summary(self, df: pd.DataFrame) -> dict:
        """Extracts and groups financial totals from a dataframe of transactions."""
        if df is None or df.empty:
            return {}
            
        summary = {
            "salary": df[df['Tax_Category'] == 'SALARY']['Deposit'].sum(),
            "business_inc": df[df['Tax_Category'] == 'BUSINESS_REV']['Deposit'].sum(),
            "business_exp": df[df['Tax_Category'] == 'BUSINESS_EXP']['Withdrawal'].sum(),
            "stcg": df[df['Tax_Category'] == 'STCG']['Deposit'].sum(),
            "ltcg": df[df['Tax_Category'] == 'LTCG']['Deposit'].sum(),
            "other_inc": df[df['Tax_Category'].isin(['UNCATEGORIZED', 'PERSONAL'])]['Deposit'].sum()
        }
        return summary


    def get_ui_tabs(self) -> List[Dict[str, Any]]:
        """Returns the dynamic UI components for the USA Tax system."""
        return [
            {
                "tab_name": "🏦 Filing Setup",
                "components": [
                    {
                        "type": "radio", 
                        "id": "filing_status", 
                        "label": "Select your Filing Status:", 
                        "options": ["Single", "Married Filing Jointly", "Head of Household"]
                    }
                ]
            },
            {
                "tab_name": "📈 Pre-Tax Contributions",
                "components": [
                    {"type": "number", "id": "401k", "label": "401(k) / 403(b) Contributions ($)", "help": "Max $23,000 for 2024"},
                    {"type": "number", "id": "hsa", "label": "Health Savings Account (HSA) ($)", "help": "Max $4,150 (Self) or $8,300 (Family)"},
                    {"type": "number", "id": "trad_ira", "label": "Traditional IRA ($)", "help": "Max $7,000 deductibility subject to income limits"}
                ]
            },
            {
                "tab_name": "📋 Itemized Deductions (Schedule A)",
                "components": [
                    {"type": "number", "id": "salt", "label": "State & Local Taxes (SALT) ($)", "help": "Capped at $10,000 automatically"},
                    {"type": "number", "id": "mortgage_int", "label": "Mortgage Interest ($)", "help": "Interest on up to $750k of mortgage debt"},
                    {"type": "number", "id": "charity", "label": "Charitable Donations ($)", "help": "Cash or property donated to 501(c)(3) orgs"},
                    {"type": "number", "id": "medical", "label": "Medical Expenses ($)", "help": "Only the amount exceeding 7.5% of AGI is deductible"}
                ]
            }
        ]

    def get_simulation_sliders(self) -> List[Dict[str, Any]]:
        """Returns the sliders for the sidebar What-If Simulation"""
        return [
            {"id": "401k", "label": "Additional 401(k) ($)", "min": 0, "max": 23000, "default": 0, "step": 1000},
            {"id": "hsa", "label": "Additional HSA ($)", "min": 0, "max": 4150, "default": 0, "step": 100},
            {"id": "trad_ira", "label": "Additional Trad IRA ($)", "min": 0, "max": 7000, "default": 0, "step": 500}
        ]

    def get_standard_deduction(self, filing_status: str, age: int) -> float:
        """Returns the 2024 Standard Deduction amount."""
        base_deduction = 14600  # Default Single
        if filing_status == "Married Filing Jointly":
            base_deduction = 29200
        elif filing_status == "Head of Household":
            base_deduction = 21900
            
        # Additional deduction for seniors (65+)
        if age >= 65:
            if filing_status == "Single" or filing_status == "Head of Household":
                base_deduction += 1950
            else:
                base_deduction += 1550 # per spouse, assuming single senior here for simplicity
                
        return float(base_deduction)

    def calculate_tax_brackets(self, taxable_income: float, filing_status: str) -> float:
        """Computes Federal Income Tax using 2024 progressive brackets."""
        tax = 0.0
        income = taxable_income
        
        # 2024 Single Brackets (Simplified)
        if filing_status == "Single":
            brackets = [
                (11600, 0.10),
                (47150, 0.12),
                (100525, 0.22),
                (191950, 0.24),
                (243725, 0.32),
                (609350, 0.35),
                (float('inf'), 0.37)
            ]
        elif filing_status == "Married Filing Jointly":
            brackets = [
                (23200, 0.10),
                (94300, 0.12),
                (201050, 0.22),
                (383900, 0.24),
                (487450, 0.32),
                (731200, 0.35),
                (float('inf'), 0.37)
            ]
        else: # HOH
            brackets = [
                (16550, 0.10),
                (63100, 0.12),
                (100500, 0.22),
                (191950, 0.24),
                (243700, 0.32),
                (609350, 0.35),
                (float('inf'), 0.37)
            ]

        previous_bracket_limit = 0
        for limit, rate in brackets:
            if income > previous_bracket_limit:
                taxable_amount_in_bracket = min(income, limit) - previous_bracket_limit
                tax += taxable_amount_in_bracket * rate
                previous_bracket_limit = limit
            else:
                break
                
        return tax

    def run_deduction_interview(self, age: int) -> dict:
        """CLI fallback interview. Not heavily used since UI drives this now."""
        print("USA CLI Interview not implemented. Use Streamlit UI.")
        return {}

    def compute_tax_liability(self, financial_summary: dict, age: int, cash_inc: float = 0.0, hra_exemption: float = 0.0, user_inputs: dict = None) -> dict:
        """
        Calculates US Federal Income Tax.
        Returns the data in the standardized format required by the UI/Reporter.
        """
        if user_inputs is None:
            user_inputs = {}

        # 1. Calculate Gross Income
        # Map Indian concepts of Salary/Business broadly to US Income for the parser
        salary = financial_summary.get("salary", 0)
        business = financial_summary.get("business_inc", 0) + cash_inc
        cap_gains = financial_summary.get("stcg", 0) + financial_summary.get("ltcg", 0)
        other_inc = financial_summary.get("other_inc", 0)
        
        gross_income = salary + business + cap_gains + other_inc

        # 2. Above-the-line Deductions (To find AGI - Adjusted Gross Income)
        v_401k = min(user_inputs.get("401k", 0), 23000)
        v_hsa = min(user_inputs.get("hsa", 0), 4150)
        v_ira = min(user_inputs.get("trad_ira", 0), 7000)
        
        above_the_line = v_401k + v_hsa + v_ira
        agi = max(0, gross_income - above_the_line)

        # 3. Standard vs Itemized Deduction
        status = user_inputs.get("filing_status", "Single")
        
        # Calculate Itemized
        v_salt = min(user_inputs.get("salt", 0), 10000) # Capped at 10k
        v_mortgage = user_inputs.get("mortgage_int", 0)
        v_charity = user_inputs.get("charity", 0)
        
        # Medical relies on AGI
        raw_medical = user_inputs.get("medical", 0)
        medical_floor = agi * 0.075
        v_medical_deductible = max(0, raw_medical - medical_floor)

        total_itemized = v_salt + v_mortgage + v_charity + v_medical_deductible
        
        # 4. Compare and select best deduction path
        standard_ded = self.get_standard_deduction(status, age)
        
        # The USA effectively has two options comparable to Old/New regime mapping
        # Option 1 ("Old" in our UI): Itemized Deductions
        opt1_taxable = max(0, agi - total_itemized)
        opt1_tax = self.calculate_tax_brackets(opt1_taxable, status)
        
        # Option 2 ("New" in our UI): Standard Deduction
        opt2_taxable = max(0, agi - standard_ded)
        opt2_tax = self.calculate_tax_brackets(opt2_taxable, status)

        # Recommendations Logic
        recs = []
        if total_itemized > standard_ded:
             recs.append(f"✅ Itemizing saves you more! Your itemized deductions (${total_itemized:,.0f}) beat the standard deduction (${standard_ded:,.0f}).")
        else:
             recs.append(f"💡 Take the Standard Deduction (${standard_ded:,.0f}) — it's higher than your Itemized total (${total_itemized:,.0f}).")
             
        if v_401k < 23000:
             recs.append(f"🚀 Max out your 401(k)! You can save up to ${23000 - v_401k:,.0f} more pre-tax.")
        if v_hsa == 0:
             recs.append("🏥 Consider opening an HSA if you have a High Deductible Health Plan for triple-tax benefits.")

        return {
            "gross_income": gross_income,
            "old_taxable": opt1_taxable,  # Mapped to Itemized
            "new_taxable": opt2_taxable,  # Mapped to Standard
            "old_final_tax": opt1_tax,    # Mapped to Itemized Tax
            "new_final_tax": opt2_tax,    # Mapped to Standard Tax
            "recommendations": recs,
            "deductions_breakdown": {
                "401(k) / 403(b)": v_401k,
                "Health Savings Account (HSA)": v_hsa,
                "Traditional IRA": v_ira,
                "State/Local Taxes (SALT)": v_salt,
                "Mortgage Interest": v_mortgage,
                "Charity": v_charity,
                "Deductible Medical": v_medical_deductible,
                f"Standard Deduction ({status})": standard_ded,
                f"Total Itemized": total_itemized
            }
        }
