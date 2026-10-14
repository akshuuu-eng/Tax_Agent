from fpdf import FPDF
import os
from datetime import datetime

class TaxReportPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Intelligent Tax Assistant - Tax Report', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()} | Intelligent Tax Assistant (ITA)', 0, 0, 'C')

    def chapter_title(self, label):
        self.set_font("Helvetica", 'B', 14)
        self.set_fill_color(230, 230, 230)
        self.cell(0, 10, label, 0, 1, 'L', 1)
        self.ln(2)

def generate_pdf_report(user_name, age, summary_data, calculation_results, filename=None):
    if filename is None:
        filename = f"Tax_Report_{user_name}_{datetime.now().strftime('%Y%m%d')}.pdf"
    
    pdf = TaxReportPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # 1. User Info
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Taxpayer: {user_name} | Age: {age}", ln=True)
    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%d-%b-%Y')}", ln=True)
    pdf.ln(5)
    
    # 1. Income Details
    pdf.chapter_title("1. Income Summary")
    pdf.set_font("Helvetica", size=11)
    
    income_items = [
        ("Salary Income", summary_data.get('salary', 0)),
        ("Business Income (Net)", summary_data.get('business_inc', 0)),
        ("Short Term Capital Gains (STCG)", summary_data.get('stcg', 0)),
        ("Long Term Capital Gains (LTCG)", summary_data.get('ltcg', 0)),
        ("Other Source Income", summary_data.get('other_inc', 0)),
    ]
    
    pdf.set_fill_color(60, 60, 60)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(120, 10, "  Description", 1, 0, 'L', 1)
    pdf.cell(40, 10, "Amount (INR)  ", 1, 1, 'R', 1)
    
    pdf.set_text_color(0, 0, 0)
    total_income = calculation_results.get('gross_income', 0)
    
    for desc, amt in income_items:
        pdf.cell(120, 10, f"  {desc}", 1)
        pdf.cell(40, 10, f"{amt:,.2f}  ", 1, 1, 'R')
        
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(120, 10, "  Gross Total Income", 1)
    pdf.cell(40, 10, f"{total_income:,.2f}  ", 1, 1, 'R')
    pdf.ln(8)
    
    # 3. Tax Calculation
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "2. Tax Liability Comparison", ln=True)
    pdf.set_font("Arial", size=12)
    
    old_tax = calculation_results.get('old_final_tax', 0)
    new_tax = calculation_results.get('new_final_tax', 0)
    
    pdf.cell(95, 10, "Regime", 1, 0, 'C', 1)
    pdf.cell(95, 10, "Tax Payable", 1, 1, 'C', 1)
    
    pdf.cell(95, 10, "Old Regime (With Deductions)", 1)
    pdf.cell(95, 10, f"INR {old_tax:,.2f}", 1, 1, 'R')
    
    pdf.cell(95, 10, "New Regime (Lower Rates)", 1)
    pdf.cell(95, 10, f"INR {new_tax:,.2f}", 1, 1, 'R')
    pdf.ln(5)
    
    # Recommendation
    pdf.set_font("Arial", 'B', 12)
    if old_tax < new_tax:
        savings = new_tax - old_tax
        pdf.set_text_color(0, 100, 0)
        pdf.multi_cell(0, 10, f"RECOMMENDATION: Choose OLD REGIME. You save INR {savings:,.0f}")
    else:
        savings = old_tax - new_tax
        pdf.set_text_color(0, 100, 0)
        pdf.multi_cell(0, 10, f"RECOMMENDATION: Choose NEW REGIME. You save INR {savings:,.0f}")
        
    pdf.set_text_color(0, 0, 0)
    
    # 4. Deductions Breakdown (Old Regime)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "3. Deductions Breakdown (Old Regime)", ln=True)
    pdf.set_font("Arial", size=12)
    
    deds = calculation_results.get('deductions_breakdown', {})
    deds = calculation_results.get('deductions_breakdown', {})
    for k, v in deds.items():
        pdf.cell(100, 10, k, 1)
        pdf.cell(50, 10, f"{v:,.2f}", 1, 1, 'R')

    # 4. Agent Recommendations
    recs = calculation_results.get('recommendations', [])
    if recs:
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "4. Strategic Recommendations", ln=True)
        pdf.set_font("Arial", size=10)
        pdf.set_text_color(100, 0, 0) # Dark Red for attention
        
        for r in recs:
            # Strip markdown bolding for PDF
            clean_r = r.replace("**", "")
            pdf.multi_cell(0, 8, f"- {clean_r}")
            
        pdf.set_text_color(0, 0, 0)
    report_path = os.path.join("data", "reports", filename)
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    pdf.output(report_path)
    
    return report_path
