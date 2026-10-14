import time
from src.logger import logger

class TaxAdvisorAgent:
    """
    An Agentic Tax Advisor that follows a Reason-Act-Observe loop.
    Even without a live LLM API, it simulates an agentic workflow 
    by analyzing engine data and constructing multi-step strategies.
    Now includes Wealth Simulation logic.
    """
    
    def __init__(self, tax_results):
        self.results = tax_results
        self.memory = []
        self.plan = []

    def reason(self):
        """Phase 1: Analyze current tax state and identify gaps."""
        logger.info("🤖 ADVISOR: Reasoning over tax data...")
        
        income = self.results.get('gross_income', 0)
        old_tax = self.results.get('old_final_tax', 0)
        new_tax = self.results.get('new_final_tax', 0)
        deductions = self.results.get('deductions_breakdown', {})
        
        # Identification of Goals
        if old_tax > new_tax:
            self.plan.append("Goal: Optimize New Regime (Already better than Old).")
            self.plan.append("Opportunity: 80CCD(2) Employer NPS can reduce New Regime tax further.")
        else:
            self.plan.append("Goal: Optimize Old Regime to maximize core tax savings.")
            self.plan.append("Strategy: Bridge the gap between Old and New regimes using Section 80 and Section 24.")

        # Specific Deduction Reasoning (Exhaustive)
        current_80c = deductions.get('80C (Investments)', 0)
        if current_80c < 150000:
            self.plan.append(f"Gap Detection: Section 80C is underutilized by ₹{150000 - current_80c:,.0f}.")
        
        current_80d = deductions.get('80D (Health Self)', 0) + deductions.get('80D (Health Parents)', 0)
        if current_80d == 0:
            self.plan.append("Risk Detection: No Health Insurance deduction found. High medical risk + lost tax benefit.")

        if deductions.get('80CCD(1B) NPS Self', 0) < 50000:
            self.plan.append("Strategy: Section 80CCD(1B) provides an exclusive ₹50k deduction for NPS.")

        if income > 5000000: # Surcharge territory
            self.plan.append("Critical Alert: High income surcharge detected. Every ₹1 of deduction saves >₹0.35.")

    def act(self):
        """Phase 2: Generate specific actionable advice."""
        logger.info("🤖 ADVISOR: Formulating execution steps...")
        actions = []
        deductions = self.results.get('deductions_breakdown', {})
        
        for item in self.plan:
            if "80C" in item:
                gap = 150000 - deductions.get('80C (Investments)', 0)
                if gap > 0:
                    actions.append({
                        "step": f"Invest ₹{gap:,.0f} in ELSS/PPF",
                        "instrument": "Equity Linked Savings Scheme (ELSS)",
                        "impact": f"Immediate tax reduction and potential ~12% long-term wealth growth."
                    })
            elif "80D" in item:
                actions.append({
                    "step": "Secure Comprehensive Health Insurance",
                    "instrument": "Family Floater Policy",
                    "impact": "Tax saving up to ₹75k and protection against medical inflation."
                })
            elif "NPS" in item:
                actions.append({
                    "step": "Contribute ₹50,000 to NPS Tier 1",
                    "instrument": "National Pension System",
                    "impact": "Tier-1 contribution is 100% additional deduction over 80C."
                })
            elif "80CCD(2)" in item:
                actions.append({
                    "step": "Restructure Salary for Employer NPS",
                    "instrument": "Corporate NPS Model",
                    "impact": "Up to 10% of Basic salary becomes tax-free in BOTH regimes."
                })
        
        return actions

    def simulate_wealth_impact(self, years=10):
        """Simulates how much wealth the tax savings could create if invested."""
        tax_saved = max(0, abs(self.results.get('old_final_tax', 0) - self.results.get('new_final_tax', 0)))
        # Assuming 10% CAGR on reinvested savings
        future_value = 0
        annual_saving = tax_saved
        for _ in range(years):
            future_value = (future_value + annual_saving) * 1.10
        return future_value

    def execute_strategy(self):
        """Main loop: Reason -> Plan -> Output."""
        self.reason()
        advice = self.act()
        wealth_impact = self.simulate_wealth_impact()
        
        return {
            "thoughts": self.plan,
            "actions": advice,
            "wealth_impact": wealth_impact,
            "final_recommendation": "Switch to New Regime" if self.results.get('new_final_tax', 0) < self.results.get('old_final_tax', 0) else "Stay with Old Regime"
        }

class TaxAuditorAgent:
    """
    The 'Legal Critic' agent. 
    It reviews Advisor's plans for audit risks and regulatory compliance.
    """
    def __init__(self, advisor_plan):
        self.plan = advisor_plan
        self.critiques = []

    def critique(self):
        logger.info("🕵️ AUDITOR: Reviewing Advisor's strategy for risks...")
        for step in self.plan:
            if "80CCD(2)" in step:
                self.critiques.append({
                    "issue": "Aggressive Restructuring",
                    "comment": "Employer NPS requires HR policy alignment. High implementation friction.",
                    "risk_level": "Medium"
                })
            if "Restructure" in step:
                self.critiques.append({
                    "issue": "Compliance Audit Trigger",
                    "comment": "Frequent salary restructuring may trigger Scrutiny under Section 143(2).",
                    "risk_level": "High"
                })
        return self.critiques

class AgentOrchestrator:
    """
    The 'Cognitive Governor'. 
    Coordinates the dialogue between Advisor and Auditor to find the Optimal Fiscal Equilibrium.
    """
    def __init__(self, tax_results):
        self.advisor = TaxAdvisorAgent(tax_results)
        self.deliberation_history = []

    def orchestrate(self):
        logger.info("🧠 ORCHESTRATOR: Initiating Multi-Agent Deliberation...")
        
        # 1. Advisor generates initial plan
        self.advisor.reason()
        initial_actions = self.advisor.act()
        self.deliberation_history.append("Advisor: Generated initial optimization manifold.")
        
        # 2. Auditor critiques the plan
        auditor = TaxAuditorAgent([a['step'] for a in initial_actions])
        critiques = auditor.critique()
        self.deliberation_history.append(f"Auditor: Identified {len(critiques)} regulatory friction points.")
        
        # 3. Refinement Phase (Advisor adjusts based on Auditor)
        refined_actions = []
        for action in initial_actions:
            matching_critique = next((c for c in critiques if c['issue'] in action['step'] or any(k in action['step'] for k in ["NPS", "Restructure"])), None)
            if matching_critique:
                action['risk_alert'] = matching_critique['comment']
                action['step'] = f"[CONSIDER REFINED] {action['step']}"
                self.deliberation_history.append(f"System: Calibrated {action['instrument']} for risk alignment.")
            refined_actions.append(action)

        wealth_impact = self.advisor.simulate_wealth_impact()
        
        return {
            "thoughts": self.advisor.plan,
            "deliberation": self.deliberation_history,
            "actions": refined_actions,
            "wealth_impact": wealth_impact,
            "final_recommendation": self.advisor.execute_strategy()["final_recommendation"],
            "agent_status": "Consensus Reached" if not critiques else "Cautionary Equilibrium"
        }

class LawSynthesizerAgent:
    """
    The 'Legal Ingestor'. 
    Uses semantic extraction to convert raw tax laws/budgets into structured JSON rules.
    """
    def __init__(self, document_text):
        self.text = document_text.upper()
        self.extracted_schema = {
            "year": "FY 2026-27 (Synthesized)",
            "currency_symbol": "¤",
            "tax_slabs": {"old": [], "new": []},
            "deduction_limits": {}
        }

    def synthesize_rule_schema(self):
        logger.info("🧠 SYNTHESIZER: Extracting latent tax constraints from document...")
        
        # 1. Slab Extraction (Heuristic/Semantic Simulation)
        import re
        # Look for patterns like "income up to 300,000" or "slab 5%"
        slabs = re.findall(r"(\d+,?\d+)\s*TO\s*(\d+,?\d+)\s*TAXED\s*AT\s*(\d+)%", self.text)
        for start, end, rate in slabs:
            clean_end = int(end.replace(",", ""))
            self.extracted_schema["tax_slabs"]["new"].append({"limit": clean_end, "rate": int(rate)/100})
        
        # Add a default top-tier if none found or to complete the chain
        if not self.extracted_schema["tax_slabs"]["new"]:
             self.extracted_schema["tax_slabs"]["new"] = [
                 {"limit": 500000, "rate": 0.0},
                 {"limit": 1000000, "rate": 0.10},
                 {"limit": None, "rate": 0.30}
             ]
        
        # 2. Deduction Extraction
        if "SECTION 80C" in self.text or "INVESTMENT LIMIT" in self.text:
            self.extracted_schema["deduction_limits"]["80C"] = 150000
        
        if "HEALTH" in self.text or "80D" in self.text:
            self.extracted_schema["deduction_limits"]["80D"] = 25000

        # Simulate "Deep Semantic" discovery
        if "ELECTRIC VEHICLE" in self.text:
            self.extracted_schema["deduction_limits"]["80EEB"] = 150000
            logger.info("✨ SYNTHESIZER: Discovered 'Clean Energy' tax incentive (Sec 80EEB).")

        return self.extracted_schema

    def calibrate_budget(self, existing_rules):
        """Updates an existing regime based on a new budget document."""
        logger.info("🧠 SYNTHESIZER: Calibrating existing regime for Budget 2026...")
        new_schema = self.synthesize_rule_schema()
        # Merge logic
        existing_rules["tax_slabs"] = new_schema["tax_slabs"]
        existing_rules["year"] = "Post-Budget 2026 Update"
        return existing_rules

if __name__ == "__main__":
    sample_results = {
        'gross_income': 1200000,
        'old_final_tax': 150000,
        'new_final_tax': 90000,
        'deductions_breakdown': {'80C (Investments)': 100000}
    }
    orchestrator = AgentOrchestrator(sample_results)
    print(orchestrator.orchestrate())
