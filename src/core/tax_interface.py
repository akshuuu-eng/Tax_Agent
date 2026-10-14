from abc import ABC, abstractmethod

class BaseTaxEngine(ABC):
    """
    Abstract Base Class representing a Country's Tax Engine.
    All country plugins must implement these methods to be compatible with the ITA.
    """
    
    @property
    @abstractmethod
    def country_name(self) -> str:
        """Return the readable name of the country (e.g., 'United States')"""
        pass
        
    @property
    @abstractmethod
    def currency_symbol(self) -> str:
        """Return the currency symbol (e.g., '₹', '$')"""
        pass
        
    @abstractmethod
    def get_supported_years(self) -> list[str]:
        """Return a list of supported tax years (e.g., ['2024', '2025'])"""
        pass

    @abstractmethod
    def set_tax_year(self, year: str) -> None:
        """Load the tax rules configuration for the specified year."""
        pass
        
    @abstractmethod
    def get_ui_tabs(self):
        """
        Returns a list of dictionaries defining the required UI tabs and their fields.
        Format:
        [
            {
                "tab_name": "Housing",
                "components": [
                    {"type": "radio", "id": "q_hl", "label": "Do you pay Home Loan?", "options": ["No", "Yes"]},
                    {"type": "number", "id": "24B", "label": "Annual Interest Amount", "condition": ("q_hl", "Yes")}
                ]
            }, ...
        ]
        """
        pass

    @abstractmethod
    def run_deduction_interview(self, age: int):
        """
        Runs the command-line equivalent diagnostic interview.
        Returns a dictionary of gathered data.
        """
        pass
        
    @abstractmethod
    def compute_tax_liability(self, financial_summary: dict, age: int, user_inputs: dict) -> dict:
        """
        The core computation engine.
        Args:
            financial_summary: Extracted data from the OCR/Bank parsers
            age: Taxpayer age
            user_inputs: Data collected from the dynamic UI tabs
            
        Returns:
            A standardized dictionary containing:
            {
                "gross_income": float,
                "old_taxable": float,  # Or Regime A
                "new_taxable": float,  # Or Regime B
                "old_final_tax": float,
                "new_final_tax": float,
                "recommendations": list[str],
                "deductions_breakdown": dict[str, float]
            }
        """
        pass
