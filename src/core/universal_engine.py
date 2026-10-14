import os
import json
from src.core.tax_interface import BaseTaxEngine
from src.logger import logger

class UniversalTaxEngine(BaseTaxEngine):
    """
    A schema-driven tax engine that can represent any country's logic 
    based on a provided JSON configuration.
    """
    
    def __init__(self, country_name, currency_symbol, rules_path):
        self._country_name = country_name
        self._currency_symbol = currency_symbol
        self.rules_path = rules_path
        self.rules = {}
        self.current_year = "Universal"
        self.load_rules()

    def load_rules(self):
        if os.path.exists(self.rules_path):
            with open(self.rules_path, "r") as f:
                self.rules = json.load(f)
                self.current_year = self.rules.get("year", "Universal")
        else:
            logger.error(f"Rules not found at {self.rules_path}")

    @property
    def country_name(self) -> str:
        return self._country_name

    @property
    def currency_symbol(self) -> str:
        return self._currency_symbol

    def get_supported_years(self) -> list[str]:
        return [self.current_year]

    def set_tax_year(self, year: str) -> None:
        # For universal engines, we typically load a specific file
        pass

    def get_ui_tabs(self):
        """Generates UI tabs dynamically from deduction rules."""
        tabs = []
        deductions = self.rules.get("deduction_limits", {})
        
        # Categorize deductions into logical tabs
        investment_comps = []
        health_comps = []
        other_comps = []

        for key, value in deductions.items():
            comp = {"type": "number", "id": key, "label": f"Section {key}"}
            if "80C" in key: investment_comps.append(comp)
            elif "80D" in key: health_comps.append(comp)
            else: other_comps.append(comp)

        if investment_comps: tabs.append({"tab_name": "💰 Investments", "components": investment_comps})
        if health_comps: tabs.append({"tab_name": "🏥 Health", "components": health_comps})
        if other_comps: tabs.append({"tab_name": "🔍 Other", "components": other_comps})

        return tabs

    def calculate_slabs(self, income, regime="NEW"):
        tax = 0
        slabs = self.rules.get("tax_slabs", {}).get(regime.lower(), [])
        
        prev_limit = 0
        for slab in slabs:
            limit = slab.get("limit")
            rate = slab.get("rate", 0.0)
            
            if limit is None: # Top-most slab
                if income > prev_limit:
                    tax += (income - prev_limit) * rate
                break
            
            if income > prev_limit:
                tax_range = min(income, limit) - prev_limit
                tax += tax_range * rate
                prev_limit = limit
            else:
                break
        return tax

    def compute_tax_liability(self, financial_summary: dict, age: int, cash_inc: float = 0.0, hra_exemption: float = 0.0, user_inputs: dict = None) -> dict:
        user_inputs = user_inputs or {}
        
        # 1. Gross Income
        gross_income = sum(financial_summary.values()) + cash_inc
        
        # 2. Deductions
        total_deductions = 0
        deductions_breakdown = {}
        
        limits = self.rules.get("deduction_limits", {})
        for key, val in user_inputs.items():
            if key in limits:
                limit = limits[key]
                # Handle nested limits (like 80D) if they exist, else simple number
                if isinstance(limit, dict):
                    limit_val = limit.get("self", 25000) # Fallback
                else:
                    limit_val = limit
                
                actual_deduction = min(val, limit_val)
                total_deductions += actual_deduction
                deductions_breakdown[key] = actual_deduction

        # 3. Standard Deduction
        std_ded_old = self.rules.get("standard_deduction", {}).get("old_regime", 0)
        std_ded_new = self.rules.get("standard_deduction", {}).get("new_regime", 0)

        # 4. Net Taxable
        old_net = max(0, gross_income - total_deductions - std_ded_old - hra_exemption)
        new_net = max(0, gross_income - std_ded_new) # New regime usually has fewer deductions

        # 5. Slab Calculation
        old_tax = self.calculate_slabs(old_net, "OLD")
        new_tax = self.calculate_slabs(new_net, "NEW")

        # 6. Rebates, Surcharge, Cess
        rebate_rule = self.rules.get("rebate_87a", {})
        if old_net <= rebate_rule.get("old_regime", {}).get("limit", 0):
            old_tax = max(0, old_tax - rebate_rule.get("old_regime", {}).get("max_rebate", 0))
        if new_net <= rebate_rule.get("new_regime", {}).get("limit", 0):
            new_tax = max(0, new_tax - rebate_rule.get("new_regime", {}).get("max_rebate", 0))

        surcharge_rate = self.rules.get("surcharge", {}).get("rate", 0)
        surcharge_threshold = self.rules.get("surcharge", {}).get("threshold", 0)
        
        if old_net > surcharge_threshold: old_tax *= (1 + surcharge_rate)
        if new_net > surcharge_threshold: new_tax *= (1 + surcharge_rate)

        cess_rate = self.rules.get("cess_rate", 0)
        old_final = old_tax * (1 + cess_rate)
        new_final = new_tax * (1 + cess_rate)

        return {
            "gross_income": gross_income,
            "old_taxable": old_net,
            "new_taxable": new_net,
            "old_final_tax": old_final,
            "new_final_tax": new_final,
            "recommendations": [f"Standard optimization applied for {self.country_name}."],
            "deductions_breakdown": deductions_breakdown
        }

    def run_deduction_interview(self, age: int):
        # Interactive CLI mode (optional)
        return {}
