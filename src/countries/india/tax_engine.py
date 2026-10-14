import os
import json
import pandas as pd
from datetime import datetime
from src.core.tax_interface import BaseTaxEngine

class IndiaTaxEngine(BaseTaxEngine):
    def __init__(self):
        self.rules = {}
        supported = self.get_supported_years()
        default_year = supported[0] if supported else "2025"
        self.set_tax_year(default_year)

    def get_supported_years(self) -> list[str]:
        rules_dir = os.path.join(os.path.dirname(__file__), "rules")
        years = []
        if os.path.exists(rules_dir):
            for file in os.listdir(rules_dir):
                if file.startswith("india_") and file.endswith(".json"):
                    year = file.replace("india_", "").replace(".json", "")
                    years.append(year)
        return sorted(years, reverse=True)

    def set_tax_year(self, year: str) -> None:
        rules_path = os.path.join(os.path.dirname(__file__), "rules", f"india_{year}.json")
        if os.path.exists(rules_path):
            with open(rules_path, "r") as f:
                self.rules = json.load(f)
        else:
            self.rules = {}
    @property
    def country_name(self) -> str:
        return "India"

    @property
    def currency_symbol(self) -> str:
        return "₹"

    def get_ui_tabs(self):
        return [
            {
                "tab_name": "🏡 Housing",
                "components": [
                    {"type": "checkbox", "id": "24B", "label": "Section 24(b) — Home Loan Interest (Max 2L)"},
                    {"type": "checkbox", "id": "80EE", "label": "Section 80EE — First-Time Home Buyer"},
                    {"type": "checkbox", "id": "80GG", "label": "Section 80GG — Rent (No HRA)"},
                    {"type": "checkbox", "id": "HP_Loss", "label": "House Property Loss Set-off"}
                ]
            },
            {
                "tab_name": "💰 Investments",
                "components": [
                    {"type": "number", "id": "80C", "label": "Section 80C (PPF/ELSS/LIC/NSC)"},
                    {"type": "number", "id": "NPS", "label": "Section 80CCD(1B) — NPS Self"},
                    {"type": "number", "id": "80CCD2", "label": "Section 80CCD(2) — Employer NPS"},
                    {"type": "number", "id": "80G", "label": "Section 80G — Donations"},
                    {"type": "number", "id": "80G_100", "label": "Section 80G — 100% Donations"},
                    {"type": "number", "id": "80EEB", "label": "Section 80EEB — EV Loan"}
                ]
            },
            {
                "tab_name": "🏥 Health",
                "components": [
                    {"type": "number", "id": "80D_self", "label": "Section 80D — Premium (Self)"},
                    {"type": "number", "id": "80D_parents", "label": "Section 80D — Premium (Parents)"},
                    {"type": "toggle", "id": "parents_senior", "label": "Are Parents Senior Citizens?"},
                    {"type": "checkbox", "id": "80DD", "label": "Section 80DD — Disabled Dependent"},
                    {"type": "toggle", "id": "80DD_severe", "label": "Is Disability Severe?"},
                    {"type": "number", "id": "80DDB", "label": "Section 80DDB — Specific Disease"},
                    {"type": "checkbox", "id": "80U", "label": "Section 80U — Self Disability"},
                    {"type": "toggle", "id": "80U_severe", "label": "Is Disability Severe?"}
                ]
            },
            {
                "tab_name": "🎓 Education & Savings",
                "components": [
                    {"type": "number", "id": "80E", "label": "Section 80E — Education Loan Interest"},
                    {"type": "number", "id": "80TTA", "label": "Section 80TTA/80TTB — Savings Interest"},
                    {"type": "number", "id": "Other", "label": "Other Deductions"}
                ]
            },
            {
                "tab_name": "💼 Employment",
                "components": [
                    {"type": "number", "id": "ProfTax", "label": "Section 16(iii) — Professional Tax"},
                    {"type": "number", "id": "LTA", "label": "Section 10(5) — Leave Travel Allowance"},
                    {"type": "number", "id": "Gratuity", "label": "Section 10(10) — Gratuity Exemption"},
                    {"type": "number", "id": "LeaveEnc", "label": "Section 10(10AA) — Leave Encashment"}
                ]
            },
            {
                "tab_name": "📈 Capital Gains",
                "components": [
                    {"type": "number", "id": "Sec54", "label": "Section 54 — House to House"},
                    {"type": "number", "id": "Sec54EC", "label": "Section 54EC — CG Bonds"},
                    {"type": "number", "id": "Sec54F", "label": "Section 54F — Non-House Asset CG"}
                ]
            },
            {
                "tab_name": "🏢 Business",
                "components": [
                    {"type": "number", "id": "44AD_turnover", "label": "Section 44AD — Total Turnover"},
                    {"type": "toggle", "id": "44AD_digital", "label": "Mostly Digital Receipts?"},
                    {"type": "number", "id": "44ADA_receipts", "label": "Section 44ADA — Total Professional Receipts"},
                    {"type": "number", "id": "80QQB", "label": "Section 80QQB — Author Royalties"},
                    {"type": "number", "id": "80RRB", "label": "Section 80RRB — Patent Royalties"}
                ]
            }
        ]
        
    def get_simulation_sliders(self):
        """Returns the sliders for the sidebar What-If Simulation"""
        return [
            {"id": "80C", "label": "Additional 80C Investment (₹)", "min": 0, "max": self.rules.get('deduction_limits', {}).get('80C', 150000), "default": 0, "step": 5000},
            {"id": "80D_self", "label": "Additional 80D (Health) (₹)", "min": 0, "max": 50000, "default": 0, "step": 1000},
            {"id": "NPS", "label": "Additional NPS (Tier 1) (₹)", "min": 0, "max": 50000, "default": 0, "step": 5000}
        ]
    def run_deduction_interview(self, age):
        """
        Returns: (Total Extra Deduction, NPS Amount)
        """
        print("\n" + "="*50)
        print(" 🕵️  COMPREHENSIVE DEDUCTION INTERVIEW")
        print("="*50)
        
        total_deduction = 0.0
        nps_amount = 0.0
        
        # Q1: NPS (Section 80CCD(1B))
        print(" [1/7] Did you invest in NPS (National Pension Scheme)?")
        if input("       (y/n): ").lower() == 'y':
            amt = float(input("       Enter Amount invested: ") or 0)
            nps_amount = amt
            # Benefit: Max ₹50,000 extra deduction
            benefit = min(amt, 50000)
            total_deduction += benefit
            print(f"       ✅ Added ₹{benefit:,.0f} (Sec 80CCD(1B))")

        # Q2: Education Loan (80E)
        print("\n [2/7] Are you paying interest on an Education Loan?")
        if input("       (y/n): ").lower() == 'y':
            amt = float(input("       Enter Interest Amount: ") or 0)
            # Benefit: Unlimited interest deduction
            total_deduction += amt
            print(f"       ✅ Added ₹{amt:,.0f} (Sec 80E)")

        # Q3: Medical Treatment (80DDB)
        print("\n [3/7] Did you pay for treatment of specific diseases?")
        if input("       (y/n): ").lower() == 'y':
            amt = float(input("       Enter Expenditure: ") or 0)
            # Benefit: Max 40k (Regular) or 100k (Senior)
            limit = self.rules.get('deduction_limits', {}).get('80DDB', {}).get('senior', 100000) if age >= 60 else self.rules.get('deduction_limits', {}).get('80DDB', {}).get('under_60', 40000)
            benefit = min(amt, limit)
            total_deduction += benefit
            print(f"       ✅ Added ₹{benefit:,.0f} (Sec 80DDB)")

        # Q4: Disability (80U)
        print("\n [4/7] Do you (or a dependent) have a registered Disability?")
        if input("       (y/n): ").lower() == 'y':
            severe = input("       Is disability > 80% (Severe)? (y/n): ").lower() == 'y'
            # Benefit: Flat 75k (Normal) or 1.25L (Severe)
            benefit = 125000 if severe else 75000
            total_deduction += benefit
            print(f"       ✅ Added ₹{benefit:,.0f} (Sec 80U)")

        # Q5: Donations (80G)
        print("\n [5/7] Did you donate to Charity?")
        if input("       (y/n): ").lower() == 'y':
            amt = float(input("       Enter Amount: ") or 0)
            # Simplified: Assuming 50% eligibility
            benefit = amt * 0.50 
            total_deduction += benefit
            print(f"       ✅ Added ₹{benefit:,.0f} (Sec 80G)")

        # Q6: Savings Interest (80TTA/TTB)
        print("\n [6/7] Did you earn Savings Interest?")
        if input("       (y/n): ").lower() == 'y':
            amt = float(input("       Enter Interest: ") or 0)
            # Benefit: Max 10k (<60) or 50k (Senior)
            limit = self.rules.get('deduction_limits', {}).get('80TTB', 50000) if age >= 60 else self.rules.get('deduction_limits', {}).get('80TTA', 10000)
            benefit = min(amt, limit)
            total_deduction += benefit
            print(f"       ✅ Added ₹{benefit:,.0f} (Sec 80TTA/TTB)")
            
        # Q7: Catch-All
        print("\n [7/7] Any other deductions? (e.g., 80GG Rent)")
        if input("       (y/n): ").lower() == 'y':
            desc = input("       Enter Description: ")
            amt = float(input("       Enter Amount: ") or 0)
            total_deduction += amt
            print(f"       ✅ Added ₹{amt:,.0f} ({desc})")

        return total_deduction, nps_amount

# --- 2. HRA CALCULATION ---
    def calculate_hra_exemption(self, basic, hra_rec, rent, metro):
        if hra_rec <= 0 or rent <= 0: return 0.0
        val1 = hra_rec
        val2 = basic * (0.50 if metro else 0.40)
        val3 = rent - (0.10 * basic)
        return max(0, min(val1, val2, val3))

# --- 3. TAX SLABS (FY 2025-26 Logic) ---
    def calculate_slabs(self, income, regime, age):
        """Calculates tax with slabs, 87A rebate, surcharge, and 4% cess."""
        tax = 0
        if regime == "NEW":
            # New Regime Slabs (Section 115BAC)
            if income > 300000: tax += (min(income, 700000) - 300000) * 0.05
            if income > 700000: tax += (min(income, 1000000) - 700000) * 0.10
            if income > 1000000: tax += (min(income, 1200000) - 1000000) * 0.15
            if income > 1200000: tax += (min(income, 1500000) - 1200000) * 0.20
            if income > 1500000: tax += (income - 1500000) * 0.30
            
            # Section 87A Rebate — New Regime: Full rebate if income ≤ 7L
            if income <= 700000:
                tax = 0
        else:
            # Old Regime Age-Based Limits
            basic_limit = 500000 if age >= 80 else (300000 if age >= 60 else 250000)
            
            if income > basic_limit:
                tax += (min(income, 500000) - basic_limit) * 0.05
            if income > 500000:
                tax += (min(income, 1000000) - 500000) * 0.20
            if income > 1000000:
                tax += (income - 1000000) * 0.30
            
            # Section 87A Rebate — Old Regime: Full rebate if income ≤ 5L
            if income <= 500000:
                tax = 0

        # --- SURCHARGE (applied on tax before cess) ---
        surcharge = 0
        if income > 50000000:    # > 5 Cr
            surcharge = tax * 0.37
        elif income > 20000000:  # > 2 Cr
            surcharge = tax * 0.25
        elif income > 10000000:  # > 1 Cr
            surcharge = tax * 0.15
        elif income > 5000000:   # > 50 L
            surcharge = tax * 0.10
        
        # Marginal Relief: Tax + surcharge should not exceed income above threshold
        if surcharge > 0:
            thresholds = [
                (50000000, 0.37), (20000000, 0.25),
                (10000000, 0.15), (5000000, 0.10)
            ]
            for threshold, rate in thresholds:
                if income > threshold:
                    excess = income - threshold
                    max_tax_at_lower = self.calculate_slab_only(threshold, regime, age)
                    # Tax + surcharge should not exceed: tax at threshold + excess
                    if (tax + surcharge) > (max_tax_at_lower * (1 + rate) + excess):
                        surcharge = max(0, (max_tax_at_lower * (1 + rate) + excess) - tax)
                    break

        total_tax = tax + surcharge
        cess = total_tax * 0.04  # 4% Health & Education Cess
        return total_tax + cess

    def calculate_slab_only(self, income, regime, age):
        """Helper: returns raw slab tax using dynamic rules without surcharge/cess."""
        tax = 0
        if regime == "NEW":
            slabs = self.rules.get('tax_slabs', {}).get('new', [])
        else:
            slabs = self.rules.get('tax_slabs', {}).get('old', [])
            if len(slabs) > 0 and slabs[0]['limit'] == 250000:
                if age >= 80: slabs[0]['limit'] = 500000
                elif age >= 60: slabs[0]['limit'] = 300000

        previous_limit = 0
        for slab in slabs:
            limit = slab.get("limit")
            rate = slab.get("rate", 0.0)
            if limit is None:
                if income > previous_limit:
                    tax += (income - previous_limit) * rate
                break
            if income > previous_limit:
                tax += (min(income, limit) - previous_limit) * rate
                previous_limit = limit
            else:
                break
        return tax

    # --- 4. DATA PARSING HELPERS ---
    def get_financial_summary(self, df):
        if 'Tax_Category' not in df.columns: return {}
        summary = df.groupby('Tax_Category')[['Withdrawal', 'Deposit']].sum()
        def get(idx, col): return summary.loc[idx, col] if idx in summary.index else 0.0
        return {
            "salary": get('SALARY', 'Deposit'),
            "business_inc": get('BUSINESS_REV', 'Deposit') - get('BUSINESS_EXP', 'Withdrawal'),
            "stcg": get('STCG', 'Deposit'),
            "ltcg": get('LTCG', 'Deposit'),
            "other_inc": get('OTHER_INCOME', 'Deposit'),
            "ded_80c_stmt": min(get('80C_INVEST', 'Withdrawal'), self.rules.get('deduction_limits', {}).get('80C', 150000)),
            "ded_80d_stmt": get('80D_MEDICAL', 'Withdrawal') 
        }

    def compute_tax_liability(self, comps, age, cash_inc=0.0, hra_exemption=0.0, interview_deductions_map=None):
        """
        Computes tax liability with EXHAUSTIVE Income Tax Act coverage.
        
        Chapter VI-A Deductions:
          80C, 80CCD(1B), 80CCD(2), 80D, 80DD, 80DDB, 80E, 80EE, 80EEB,
          80G, 80GG, 80QQB, 80RRB, 80TTA/TTB, 80U
        
        Section 10 Exemptions: LTA 10(5), Gratuity 10(10), Leave Encashment 10(10AA)
        Section 16: Professional Tax 16(iii)
        Section 24(b): Home Loan Interest
        Capital Gains: Sec 54, 54EC, 54F
        Presumptive Taxation: 44AD, 44ADA
        Loss Set-off: House Property Loss (max ₹2L)
        87A Rebate, Surcharge (10%-37%), 4% Cess
        """
        if interview_deductions_map is None:
            interview_deductions_map = {}
            
        salary = comps.get("salary", 0)
        business_inc = comps.get("business_inc", 0) + cash_inc
        stcg = comps.get("stcg", 0)
        ltcg = comps.get("ltcg", 0)
        other_inc = comps.get("other_inc", 0)
        
        # --- DEDUCTIONS FROM DOCUMENTS ---
        ded_80c_doc = min(comps.get("ded_80c_stmt", 0), self.rules.get('deduction_limits', {}).get('80C', 150000))
        ded_80d_doc = comps.get("ded_80d_stmt", 0)

        # --- MANUAL DEDUCTIONS (FROM WIZARD) ---
        manual_80c = interview_deductions_map.get("80C", 0)
        manual_80d_self = interview_deductions_map.get("80D_self", 0)
        manual_80d_parents = interview_deductions_map.get("80D_parents", 0)
        manual_nps = interview_deductions_map.get("NPS", 0)
        manual_80e = interview_deductions_map.get("80E", 0)
        manual_80g = interview_deductions_map.get("80G", 0)
        manual_80g_100 = interview_deductions_map.get("80G_100", 0)
        manual_24b = interview_deductions_map.get("24B", 0)
        manual_80dd = interview_deductions_map.get("80DD", 0)
        manual_80dd_severe = interview_deductions_map.get("80DD_severe", False)
        manual_80ddb = interview_deductions_map.get("80DDB", 0)
        manual_80ee = interview_deductions_map.get("80EE", 0)
        manual_80gg = interview_deductions_map.get("80GG", 0)
        manual_80tta = interview_deductions_map.get("80TTA", 0)
        manual_80u = interview_deductions_map.get("80U", 0)
        manual_80u_severe = interview_deductions_map.get("80U_severe", False)
        manual_other = interview_deductions_map.get("Other", 0)

        # --- NEW: Group A — Additional Chapter VI-A ---
        manual_80ccd2 = interview_deductions_map.get("80CCD2", 0)      # Employer NPS
        manual_80eeb = interview_deductions_map.get("80EEB", 0)         # EV Loan interest
        manual_80qqb = interview_deductions_map.get("80QQB", 0)         # Author royalty
        manual_80rrb = interview_deductions_map.get("80RRB", 0)         # Patent royalty

        # --- NEW: Group B — Section 10 Exemptions ---
        manual_lta = interview_deductions_map.get("LTA", 0)             # 10(5)
        manual_gratuity = interview_deductions_map.get("Gratuity", 0)   # 10(10)
        manual_leave_enc = interview_deductions_map.get("LeaveEnc", 0)  # 10(10AA)

        # --- NEW: Group C — Section 16 ---
        manual_prof_tax = interview_deductions_map.get("ProfTax", 0)    # 16(iii)

        # --- NEW: Group D — Capital Gains Exemptions ---
        manual_sec54 = interview_deductions_map.get("Sec54", 0)         # House reinvestment
        manual_sec54ec = interview_deductions_map.get("Sec54EC", 0)     # CG in bonds
        manual_sec54f = interview_deductions_map.get("Sec54F", 0)       # Non-house CG

        # --- NEW: Group E — Presumptive Taxation ---
        manual_44ad_turnover = interview_deductions_map.get("44AD_turnover", 0)
        manual_44ad_digital = interview_deductions_map.get("44AD_digital", False)
        manual_44ada_receipts = interview_deductions_map.get("44ADA_receipts", 0)

        # --- NEW: Group F — House Property Loss ---
        manual_hp_loss = interview_deductions_map.get("HP_Loss", 0)

        # ================================================================
        #                 SECTION-WISE COMPUTATION
        # ================================================================

        # ---- SECTION 10 EXEMPTIONS (reduce gross income) ----
        # 10(5) LTA: Actual amount claimed (must have travel proof)
        final_lta = max(0, manual_lta)
        # 10(10) Gratuity: Max ₹20L exemption
        final_gratuity = min(manual_gratuity, 2000000)
        # 10(10AA) Leave Encashment: Max ₹25L
        final_leave_enc = min(manual_leave_enc, 2500000)
        total_sec10_exemptions = final_lta + final_gratuity + final_leave_enc

        # ---- SECTION 16: SALARY DEDUCTIONS ----
        # 16(iii) Professional Tax: Max ₹2,500
        final_prof_tax = min(manual_prof_tax, 2500)

        # ---- SECTION 24(b): HOME LOAN INTEREST ----
        ded_24b = min(manual_24b, 200000)

        # ---- HOUSE PROPERTY LOSS SET-OFF ----
        # Max ₹2L loss from house property can be set off against other income
        final_hp_loss = min(manual_hp_loss, 200000)

        # ---- SECTION 80C: INVESTMENTS (limit 1.5L) ----
        total_80c = ded_80c_doc + manual_80c
        final_80c = min(total_80c, self.rules.get('deduction_limits', {}).get('80C', 150000))

        # ---- SECTION 80CCD(1B): NPS SELF (extra 50k) ----
        final_nps = min(manual_nps, self.rules.get('deduction_limits', {}).get('80CCD1B_NPS', 50000))

        # ---- SECTION 80CCD(2): EMPLOYER NPS ----
        # Allowed in BOTH regimes! Limit: 10% of salary (14% for Central Govt)
        limit_80ccd2 = salary * 0.10  # Default 10%
        final_80ccd2 = min(manual_80ccd2, limit_80ccd2)

        # ---- SECTION 80D: HEALTH INSURANCE ----
        limit_80d_self = self.rules.get('deduction_limits', {}).get('80D', {}).get('self_senior', 50000) if age >= 60 else self.rules.get('deduction_limits', {}).get('80D', {}).get('self', 25000)
        total_80d_self = ded_80d_doc + manual_80d_self
        final_80d_self = min(total_80d_self, limit_80d_self)
        parents_senior = interview_deductions_map.get("parents_senior", False)
        limit_80d_parents = self.rules.get('deduction_limits', {}).get('80D', {}).get('parents_senior', 50000) if parents_senior else self.rules.get('deduction_limits', {}).get('80D', {}).get('parents', 25000)
        final_80d_parents = min(manual_80d_parents, limit_80d_parents)
        final_80d = final_80d_self + final_80d_parents

        # ---- SECTION 80DD: DISABLED DEPENDENT ----
        if manual_80dd > 0:
            final_80dd = self.rules.get('deduction_limits', {}).get('80DD', {}).get('severe', 125000) if manual_80dd_severe else self.rules.get('deduction_limits', {}).get('80DD', {}).get('normal', 75000)
        else:
            final_80dd = 0

        # ---- SECTION 80DDB: SPECIFIED DISEASE ----
        limit_80ddb = self.rules.get('deduction_limits', {}).get('80DDB', {}).get('senior', 100000) if age >= 60 else self.rules.get('deduction_limits', {}).get('80DDB', {}).get('under_60', 40000)
        final_80ddb = min(manual_80ddb, limit_80ddb)

        # ---- SECTION 80E: EDUCATION LOAN INTEREST ----
        final_80e = manual_80e  # Unlimited

        # ---- SECTION 80EE: FIRST-TIME HOME BUYER ----
        final_80ee = min(manual_80ee, self.rules.get('deduction_limits', {}).get('80EE', 50000))

        # ---- SECTION 80EEB: ELECTRIC VEHICLE LOAN ----
        # Max ₹1.5L deduction on EV loan interest
        final_80eeb = min(manual_80eeb, self.rules.get('deduction_limits', {}).get('80C', 150000))

        # ---- SECTION 80G: DONATIONS ----
        final_80g = manual_80g_100 + (manual_80g * 0.50)

        # ---- SECTION 80GG: RENT WITHOUT HRA ----
        gross_income_raw = salary + max(0, business_inc) + other_inc + stcg + ltcg
        if manual_80gg > 0 and hra_exemption == 0:
            option_1 = manual_80gg - (0.10 * gross_income_raw)
            option_2 = 60000
            option_3 = 0.25 * gross_income_raw
            final_80gg = max(0, min(option_1, option_2, option_3))
        else:
            final_80gg = 0

        # ---- SECTION 80QQB: AUTHOR ROYALTIES ----
        # Max ₹3L deduction on royalty income from books
        final_80qqb = min(manual_80qqb, self.rules.get('deduction_limits', {}).get('80QQB', 300000))

        # ---- SECTION 80RRB: PATENT ROYALTIES ----
        # Max ₹3L deduction on patent royalty income
        final_80rrb = min(manual_80rrb, self.rules.get('deduction_limits', {}).get('80RRB', 300000))

        # ---- SECTION 80TTA / 80TTB: SAVINGS INTEREST ----
        limit_80tta = self.rules.get('deduction_limits', {}).get('80TTB', 50000) if age >= 60 else self.rules.get('deduction_limits', {}).get('80TTA', 10000)
        final_80tta = min(manual_80tta, limit_80tta)

        # ---- SECTION 80U: SELF-DISABILITY ----
        if manual_80u > 0:
            final_80u = self.rules.get('deduction_limits', {}).get('80U', {}).get('severe', 125000) if manual_80u_severe else self.rules.get('deduction_limits', {}).get('80U', {}).get('normal', 75000)
        else:
            final_80u = 0

        # ---- PRESUMPTIVE TAXATION: 44AD / 44ADA ----
        # 44AD: Business income = 6% (digital) or 8% (cash) of turnover (≤₹2Cr/3Cr)
        if manual_44ad_turnover > 0:
            rate_44ad = 0.06 if manual_44ad_digital else 0.08
            presumptive_business = manual_44ad_turnover * rate_44ad
        else:
            presumptive_business = 0
        # 44ADA: Professional income = 50% of receipts (≤₹50L)
        if manual_44ada_receipts > 0:
            presumptive_professional = manual_44ada_receipts * 0.50
        else:
            presumptive_professional = 0

        # ---- CAPITAL GAINS EXEMPTIONS: SEC 54, 54EC, 54F ----
        # Sec 54: Exempt LTCG on house if reinvested in new house
        final_sec54 = min(manual_sec54, ltcg)
        # Sec 54EC: Exempt CG up to ₹50L if invested in specified bonds
        final_sec54ec = min(manual_sec54ec, 5000000)
        # Sec 54F: Exempt LTCG on non-house asset if net proceeds reinvested in house
        final_sec54f = min(manual_sec54f, ltcg)
        total_cg_exemption = final_sec54 + final_sec54ec + final_sec54f

        # ================================================================
        #                 GROSS INCOME COMPUTATION
        # ================================================================
        
        # Apply Section 10 exemptions to salary
        adjusted_salary = max(0, salary - total_sec10_exemptions)
        
        # Apply presumptive taxation (replaces regular business income if opted in)
        if presumptive_business > 0 or presumptive_professional > 0:
            effective_business_inc = presumptive_business + presumptive_professional
        else:
            effective_business_inc = max(0, business_inc)

        # Gross Total Income
        gross_income = adjusted_salary + effective_business_inc + other_inc + stcg + ltcg

        # Apply house property loss set-off (max ₹2L)
        gross_income = max(0, gross_income - final_hp_loss)

        # Apply CG exemptions to reduce taxable capital gains
        effective_stcg = max(0, stcg)  # STCG exemptions are rare
        effective_ltcg = max(0, ltcg - total_cg_exemption)

        # ================================================================
        #                 CHAPTER VI-A TOTALS
        # ================================================================
        
        # Old Regime deductions (all Chapter VI-A)
        old_regime_deductions = (
            final_80c +
            final_nps +
            final_80ccd2 +
            final_80d +
            final_80dd +
            final_80ddb +
            final_80e +
            final_80ee +
            final_80eeb +
            final_80g +
            final_80gg +
            final_80qqb +
            final_80rrb +
            final_80tta +
            final_80u +
            manual_other
        )

        # ================================================================
        #                 TAXABLE INCOME
        # ================================================================
        
        # Old Regime: Std Deduction (50k) + Prof Tax + HRA + Chapter VI-A + Sec 24(b)
        old_net_taxable = max(0,
            gross_income - hra_exemption - self.rules.get('standard_deduction', {}).get('old_regime', 50000) - final_prof_tax
            - old_regime_deductions - ded_24b
        )
        
        # New Regime: Std Deduction (75k) + 80CCD(2) only
        # Note: 80CCD(2) employer NPS is one of the few deductions allowed in New Regime!
        new_net_taxable = max(0, gross_income - self.rules.get('standard_deduction', {}).get('new_regime', 75000) - final_80ccd2)
        
        # ================================================================
        #                 TAX CALCULATION
        # ================================================================
        
        # Special rate taxes on capital gains (after CG exemptions)
        tax_stcg = effective_stcg * 0.20
        tax_ltcg = max(0, effective_ltcg - 125000) * 0.125
        
        old_slab_tax = self.calculate_slabs(
            old_net_taxable - effective_stcg - effective_ltcg, "OLD", age
        )
        new_slab_tax = self.calculate_slabs(
            new_net_taxable - effective_stcg - effective_ltcg, "NEW", age
        )
        
        old_final_tax = old_slab_tax + tax_stcg + tax_ltcg
        new_final_tax = new_slab_tax + tax_stcg + tax_ltcg
        
        # ================================================================
        #                 RECOMMENDATION ENGINE
        # ================================================================
        recommendations = []
        
        # 80C Gap
        if total_80c < self.rules.get('deduction_limits', {}).get('80C', 150000):
            gap = self.rules.get('deduction_limits', {}).get('80C', 150000) - total_80c
            save = gap * 0.30
            recommendations.append(f"🔴 **80C Alert**: Unused limit ₹{gap:,.0f}. Invest in PPF/ELSS to save ~₹{save:,.0f}.")

        # 80D Gap (Self)
        if total_80d_self < limit_80d_self:
            gap = limit_80d_self - total_80d_self
            save = gap * 0.30
            recommendations.append(f"🟠 **Health Ins (Self)**: Claim ₹{gap:,.0f} more for yourself. Save ~₹{save:,.0f}.")

        # 80D Gap (Parents)
        if final_80d_parents < limit_80d_parents:
            gap = limit_80d_parents - final_80d_parents
            save = gap * 0.30
            recommendations.append(f"🟠 **Health Ins (Parents)**: Buy parents' policy for ₹{gap:,.0f} more. Save ~₹{save:,.0f}.")
            
        # NPS Gap (Self)
        if final_nps < 50000:
            gap = 50000 - final_nps
            save = gap * 0.30
            recommendations.append(f"🔵 **NPS Power**: Invest ₹{gap:,.0f} in NPS (Tier 1) for extra ~₹{save:,.0f} savings.")

        # 80CCD(2) Awareness
        if final_80ccd2 == 0 and salary > 0:
            potential = salary * 0.10
            recommendations.append(f"💼 **Employer NPS 80CCD(2)**: Ask employer for NPS contribution. Up to ₹{potential:,.0f} deductible in BOTH regimes!")

        # 80TTA Awareness
        if final_80tta == 0:
            limit_label = "80TTB ₹50k" if age >= 60 else "80TTA ₹10k"
            recommendations.append(f"💡 **Savings Interest**: You may claim up to {limit_label} deduction on savings account interest.")

        # 80GG Awareness
        if hra_exemption == 0 and final_80gg == 0 and salary > 0:
            recommendations.append(f"🏠 **Sec 80GG**: If you pay rent but don't receive HRA, you can claim up to ₹60,000/yr.")

        # Home Loan Awareness
        if ded_24b == 0:
            recommendations.append(f"🏡 **Home Loan**: Sec 24(b) allows up to ₹2L deduction on home loan interest.")

        # EV Loan Awareness
        if final_80eeb == 0:
            recommendations.append(f"🚗 **EV Loan (80EEB)**: Buying an EV? Claim up to ₹1.5L on loan interest.")

        # Professional Tax
        if final_prof_tax == 0 and salary > 0:
            recommendations.append(f"📋 **Professional Tax**: Don't forget to claim up to ₹2,500 under Sec 16(iii).")

        return {
            "gross_income": gross_income,
            "old_taxable": old_net_taxable,
            "new_taxable": new_net_taxable,
            "old_final_tax": old_final_tax,
            "new_final_tax": new_final_tax,
            "recommendations": recommendations,
            "deductions_breakdown": {
                "80C (Investments)": final_80c,
                "80CCD(1B) NPS Self": final_nps,
                "80CCD(2) Employer NPS": final_80ccd2,
                "80D (Health Self)": final_80d_self,
                "80D (Health Parents)": final_80d_parents,
                "80DD (Disabled Dep)": final_80dd,
                "80DDB (Spec Disease)": final_80ddb,
                "80E (Edu Loan Int)": final_80e,
                "80EE (1st Home Extra)": final_80ee,
                "80EEB (EV Loan)": final_80eeb,
                "80G (Donations)": final_80g,
                "80GG (Rent w/o HRA)": final_80gg,
                "80QQB (Author Royalty)": final_80qqb,
                "80RRB (Patent Royalty)": final_80rrb,
                "80TTA/TTB (Savings)": final_80tta,
                "80U (Self Disability)": final_80u,
                "HRA Exemption": hra_exemption,
                "Std Deduction": 50000,
                "Professional Tax 16(iii)": final_prof_tax,
                "Sec 24(b) Home Loan": ded_24b,
                "House Property Loss": final_hp_loss,
                "LTA Exemption 10(5)": final_lta,
                "Gratuity Exemption 10(10)": final_gratuity,
                "Leave Encash 10(10AA)": final_leave_enc,
                "Sec 54 (House CG)": final_sec54,
                "Sec 54EC (CG Bonds)": final_sec54ec,
                "Sec 54F (Non-House CG)": final_sec54f,
                "44AD Presumptive Biz": presumptive_business,
                "44ADA Presumptive Prof": presumptive_professional,
                "Other": manual_other,
            }
        }
