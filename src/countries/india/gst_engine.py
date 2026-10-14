"""
GST (Goods & Services Tax) Engine
Covers: GSTR-3B, GSTR-1 Summary, ITC Reconciliation, Annual GST Summary
"""

# ======================== GST RATE MASTER ========================

GST_RATES = {
    "exempt": 0.0,
    "nil": 0.0,
    "5": 0.05,
    "12": 0.12,
    "18": 0.18,
    "28": 0.28,
}

COMPOSITION_RATES = {
    "manufacturer": 0.01,    # 1% (0.5% CGST + 0.5% SGST)
    "trader": 0.01,          # 1%
    "restaurant": 0.05,      # 5% (2.5% + 2.5%)
    "service_provider": 0.06 # 6% (3% + 3%) — for services ≤₹50L
}

# Common HSN/SAC codes for reference
HSN_SAC_EXAMPLES = {
    "9954": {"desc": "Construction Services", "rate": 18},
    "9971": {"desc": "Financial Services", "rate": 18},
    "9983": {"desc": "Professional Services", "rate": 18},
    "9985": {"desc": "Transport Services", "rate": 5},
    "9986": {"desc": "Logistics & Courier", "rate": 18},
    "9988": {"desc": "Manufacturing Services", "rate": 18},
    "9992": {"desc": "Education Services", "rate": 18},
    "9993": {"desc": "Healthcare Services", "rate": 0},
    "9997": {"desc": "IT & ITES Services", "rate": 18},
    "8471": {"desc": "Computers & Laptops", "rate": 18},
    "8517": {"desc": "Mobile Phones", "rate": 12},
    "6109": {"desc": "T-shirts & Apparel", "rate": 5},
    "0401": {"desc": "Milk & Dairy", "rate": 0},
    "1006": {"desc": "Rice", "rate": 5},
    "2202": {"desc": "Aerated Beverages", "rate": 28},
}

# ======================== HELPER FUNCTIONS ========================

def get_gst_rate(rate_key):
    """Returns GST rate as a decimal for a given rate key."""
    return GST_RATES.get(str(rate_key), 0.18)  # Default 18%


def split_gst(gst_amount, is_interstate):
    """
    Splits GST into IGST or CGST+SGST.
    Interstate → full IGST
    Intra-state → 50% CGST + 50% SGST
    """
    if is_interstate:
        return {"IGST": round(gst_amount, 2), "CGST": 0.0, "SGST": 0.0}
    else:
        half = round(gst_amount / 2, 2)
        return {"IGST": 0.0, "CGST": half, "SGST": half}


def check_registration_required(annual_turnover, is_services=False, is_northeast=False):
    """
    Checks if GST registration is mandatory.
    Goods: ₹40L (₹20L for NE/special states)
    Services: ₹20L (₹10L for NE/special states)
    """
    if is_services:
        threshold = 1000000 if is_northeast else 2000000
    else:
        threshold = 2000000 if is_northeast else 4000000
    
    return {
        "required": annual_turnover > threshold,
        "threshold": threshold,
        "turnover": annual_turnover,
        "message": (
            f"GST Registration {'REQUIRED' if annual_turnover > threshold else 'NOT required'}. "
            f"Turnover ₹{annual_turnover:,.0f} vs threshold ₹{threshold:,.0f}."
        )
    }


def compute_composition_tax(turnover, business_type="trader"):
    """
    Composition scheme: simple flat rate on turnover.
    Eligible if turnover ≤ ₹1.5Cr (goods) or ≤₹50L (services).
    """
    rate = COMPOSITION_RATES.get(business_type, 0.01)
    
    # Eligibility check
    limit = 5000000 if business_type == "service_provider" else 15000000
    eligible = turnover <= limit
    
    tax = turnover * rate if eligible else 0
    half = round(tax / 2, 2)
    
    return {
        "eligible": eligible,
        "limit": limit,
        "rate_pct": rate * 100,
        "total_tax": round(tax, 2),
        "cgst": half,
        "sgst": half,
        "message": (
            f"Composition Scheme: {'Eligible' if eligible else 'NOT Eligible (turnover exceeds limit)'}. "
            f"Rate: {rate*100}% → Tax: ₹{tax:,.0f}"
        )
    }


# ======================== GSTR-3B COMPUTATION ========================

def compute_gstr3b(sales_data, purchase_data, previous_credit=0):
    """
    Computes GSTR-3B (Monthly Summary Return).
    
    Args:
        sales_data: list of dicts with keys:
            - amount: taxable value
            - rate: GST rate (5/12/18/28/exempt)
            - is_interstate: bool
            - description: str (optional)
        purchase_data: list of dicts with keys:
            - amount: taxable value
            - gst_paid: GST amount on purchase
            - itc_eligible: bool (is ITC claimable?)
            - is_interstate: bool
        previous_credit: ITC carried forward from previous month
    
    Returns: dict with full GSTR-3B computation
    """
    # ---- OUTPUT TAX (on sales) ----
    total_taxable_sales = 0
    total_exempt_sales = 0
    output_igst = 0
    output_cgst = 0
    output_sgst = 0
    sales_by_rate = {}
    
    for sale in sales_data:
        amt = sale.get("amount", 0)
        rate_key = str(sale.get("rate", "18"))
        rate = get_gst_rate(rate_key)
        is_inter = sale.get("is_interstate", False)
        
        if rate == 0:
            total_exempt_sales += amt
        else:
            total_taxable_sales += amt
            gst = amt * rate
            split = split_gst(gst, is_inter)
            output_igst += split["IGST"]
            output_cgst += split["CGST"]
            output_sgst += split["SGST"]
        
        # Track by rate
        if rate_key not in sales_by_rate:
            sales_by_rate[rate_key] = {"taxable": 0, "tax": 0}
        sales_by_rate[rate_key]["taxable"] += amt
        sales_by_rate[rate_key]["tax"] += amt * rate
    
    total_output_tax = round(output_igst + output_cgst + output_sgst, 2)
    
    # ---- INPUT TAX CREDIT (on purchases) ----
    total_purchases = 0
    eligible_itc = 0
    ineligible_itc = 0
    itc_igst = 0
    itc_cgst = 0
    itc_sgst = 0
    
    for purchase in purchase_data:
        amt = purchase.get("amount", 0)
        gst_paid = purchase.get("gst_paid", 0)
        is_eligible = purchase.get("itc_eligible", True)
        is_inter = purchase.get("is_interstate", False)
        
        total_purchases += amt
        
        if is_eligible:
            eligible_itc += gst_paid
            split = split_gst(gst_paid, is_inter)
            itc_igst += split["IGST"]
            itc_cgst += split["CGST"]
            itc_sgst += split["SGST"]
        else:
            ineligible_itc += gst_paid
    
    total_itc = round(eligible_itc + previous_credit, 2)
    
    # ---- NET TAX PAYABLE ----
    # ITC utilization order: IGST first → CGST → SGST
    net_igst = max(0, round(output_igst - itc_igst, 2))
    remaining_igst_credit = max(0, round(itc_igst - output_igst, 2))
    
    # Apply remaining IGST credit to CGST, then SGST
    net_cgst = max(0, round(output_cgst - itc_cgst - remaining_igst_credit, 2))
    remaining_after_cgst = max(0, round(remaining_igst_credit - (output_cgst - itc_cgst), 2)) if remaining_igst_credit > 0 else 0
    
    net_sgst = max(0, round(output_sgst - itc_sgst - remaining_after_cgst, 2))
    
    net_payable = round(net_igst + net_cgst + net_sgst, 2)
    
    # Carry-forward credit
    carry_forward = max(0, round(total_itc - total_output_tax, 2))
    
    # ---- RECOMMENDATIONS ----
    recommendations = []
    
    if carry_forward > 0:
        recommendations.append(
            f"💰 **ITC Surplus**: ₹{carry_forward:,.0f} credit carried forward to next month."
        )
    
    if ineligible_itc > 0:
        recommendations.append(
            f"⚠️ **Blocked ITC**: ₹{ineligible_itc:,.0f} ITC not claimable (blocked items or missing invoices)."
        )
    
    itc_ratio = (eligible_itc / total_output_tax * 100) if total_output_tax > 0 else 0
    if itc_ratio < 50 and total_output_tax > 0:
        recommendations.append(
            f"📋 **Low ITC Ratio**: Only {itc_ratio:.0f}% of output tax covered by ITC. "
            f"Ensure all purchase invoices are captured."
        )
    
    if total_exempt_sales > 0:
        recommendations.append(
            f"ℹ️ **Exempt Sales**: ₹{total_exempt_sales:,.0f} in nil/exempt supplies (no GST charged)."
        )
    
    return {
        # Sales
        "total_taxable_sales": round(total_taxable_sales, 2),
        "total_exempt_sales": round(total_exempt_sales, 2),
        "total_sales": round(total_taxable_sales + total_exempt_sales, 2),
        "sales_by_rate": sales_by_rate,
        
        # Output Tax
        "output_igst": round(output_igst, 2),
        "output_cgst": round(output_cgst, 2),
        "output_sgst": round(output_sgst, 2),
        "total_output_tax": total_output_tax,
        
        # ITC
        "eligible_itc": round(eligible_itc, 2),
        "ineligible_itc": round(ineligible_itc, 2),
        "previous_credit": previous_credit,
        "total_itc": total_itc,
        "itc_igst": round(itc_igst, 2),
        "itc_cgst": round(itc_cgst, 2),
        "itc_sgst": round(itc_sgst, 2),
        
        # Net Payable
        "net_igst": net_igst,
        "net_cgst": net_cgst,
        "net_sgst": net_sgst,
        "net_payable": net_payable,
        "carry_forward_credit": carry_forward,
        
        # Purchases
        "total_purchases": round(total_purchases, 2),
        
        # Recommendations
        "recommendations": recommendations,
    }


# ======================== GSTR-1 SUMMARY ========================

def compute_gstr1_summary(invoices):
    """
    Computes GSTR-1 summary (Outward Supplies).
    
    Args:
        invoices: list of dicts:
            - invoice_no: str
            - buyer_gstin: str (or "" for B2C)
            - amount: taxable value
            - rate: GST rate
            - is_interstate: bool
            - hsn_code: str (optional)
    
    Returns: B2B, B2C, HSN summary
    """
    b2b = []       # Business-to-Business (with GSTIN)
    b2c_large = [] # B2C Large (interstate > ₹2.5L)
    b2c_small = [] # B2C Small (all others)
    hsn_summary = {}
    
    total_invoices = 0
    total_value = 0
    total_tax = 0
    
    for inv in invoices:
        amt = inv.get("amount", 0)
        rate_key = str(inv.get("rate", "18"))
        rate = get_gst_rate(rate_key)
        gst = round(amt * rate, 2)
        is_inter = inv.get("is_interstate", False)
        gstin = inv.get("buyer_gstin", "")
        hsn = inv.get("hsn_code", "")
        
        total_invoices += 1
        total_value += amt
        total_tax += gst
        
        entry = {
            "invoice_no": inv.get("invoice_no", ""),
            "buyer_gstin": gstin,
            "taxable_value": amt,
            "rate": rate_key,
            "gst": gst,
            **split_gst(gst, is_inter)
        }
        
        if gstin:
            b2b.append(entry)
        elif is_inter and amt > 250000:
            b2c_large.append(entry)
        else:
            b2c_small.append(entry)
        
        # HSN Summary
        if hsn:
            if hsn not in hsn_summary:
                hsn_summary[hsn] = {
                    "description": HSN_SAC_EXAMPLES.get(hsn, {}).get("desc", ""),
                    "quantity": 0, "taxable_value": 0, "total_tax": 0
                }
            hsn_summary[hsn]["quantity"] += 1
            hsn_summary[hsn]["taxable_value"] += amt
            hsn_summary[hsn]["total_tax"] += gst
    
    return {
        "total_invoices": total_invoices,
        "total_taxable_value": round(total_value, 2),
        "total_tax": round(total_tax, 2),
        "b2b": {"count": len(b2b), "items": b2b},
        "b2c_large": {"count": len(b2c_large), "items": b2c_large},
        "b2c_small": {"count": len(b2c_small), "items": b2c_small},
        "hsn_summary": hsn_summary,
    }


# ======================== ANNUAL GST SUMMARY ========================

def compute_annual_gst(monthly_data):
    """
    Computes Annual GST Summary from monthly GSTR-3B results.
    
    Args:
        monthly_data: list of 12 GSTR-3B result dicts (from compute_gstr3b)
    
    Returns: Annual aggregates
    """
    annual = {
        "total_sales": 0,
        "total_taxable_sales": 0,
        "total_exempt_sales": 0,
        "total_output_tax": 0,
        "total_itc_claimed": 0,
        "total_tax_paid": 0,
        "total_purchases": 0,
        "months_filed": 0,
    }
    
    for month in monthly_data:
        annual["total_sales"] += month.get("total_sales", 0)
        annual["total_taxable_sales"] += month.get("total_taxable_sales", 0)
        annual["total_exempt_sales"] += month.get("total_exempt_sales", 0)
        annual["total_output_tax"] += month.get("total_output_tax", 0)
        annual["total_itc_claimed"] += month.get("total_itc", 0)
        annual["total_tax_paid"] += month.get("net_payable", 0)
        annual["total_purchases"] += month.get("total_purchases", 0)
        annual["months_filed"] += 1
    
    # Round all values
    for key in annual:
        if isinstance(annual[key], float):
            annual[key] = round(annual[key], 2)
    
    # Effective tax rate
    if annual["total_taxable_sales"] > 0:
        annual["effective_rate_pct"] = round(
            annual["total_tax_paid"] / annual["total_taxable_sales"] * 100, 2
        )
    else:
        annual["effective_rate_pct"] = 0
    
    # Registration check
    reg = check_registration_required(annual["total_sales"])
    annual["registration_status"] = reg
    
    # Composition eligibility
    comp = compute_composition_tax(annual["total_sales"])
    annual["composition_option"] = comp
    
    # Compare: regular vs composition
    if comp["eligible"] and annual["total_tax_paid"] > comp["total_tax"]:
        saving = annual["total_tax_paid"] - comp["total_tax"]
        annual["composition_saving"] = round(saving, 2)
        annual["composition_recommendation"] = (
            f"💡 **Composition Scheme** could save ₹{saving:,.0f}/year! "
            f"(Regular: ₹{annual['total_tax_paid']:,.0f} vs Composition: ₹{comp['total_tax']:,.0f})"
        )
    else:
        annual["composition_saving"] = 0
        annual["composition_recommendation"] = None
    
    return annual


# ======================== LATE FEES & INTEREST ========================

def compute_late_fees(days_late, is_nil_return=False):
    """
    Late fees for delayed GST return filing.
    - Nil return: ₹20/day (₹10 CGST + ₹10 SGST), max ₹500
    - Other: ₹50/day (₹25 CGST + ₹25 SGST), max ₹10,000
    """
    if days_late <= 0:
        return {"late_fee": 0, "cgst_fee": 0, "sgst_fee": 0, "days": 0, "message": "Filed on time ✅"}
    
    if is_nil_return:
        daily = 20
        cap = 500
    else:
        daily = 50
        cap = 10000
    
    total = min(days_late * daily, cap)
    half = round(total / 2, 2)
    
    return {
        "late_fee": total,
        "cgst_fee": half,
        "sgst_fee": half,
        "days": days_late,
        "message": f"Late by {days_late} days → Fee: ₹{total:,.0f} (₹{half:,.0f} CGST + ₹{half:,.0f} SGST)"
    }


def compute_interest(tax_amount, days_late, rate_pct=18):
    """
    Interest on late payment of GST.
    Section 50(1): 18% p.a. on net tax liability.
    Section 50(3): 24% p.a. on undue/excess ITC claimed.
    """
    if days_late <= 0 or tax_amount <= 0:
        return {"interest": 0, "message": "No interest applicable"}
    
    interest = round(tax_amount * (rate_pct / 100) * (days_late / 365), 2)
    
    return {
        "interest": interest,
        "tax_amount": tax_amount,
        "days": days_late,
        "rate": rate_pct,
        "message": f"Interest @ {rate_pct}% p.a. for {days_late} days on ₹{tax_amount:,.0f} = ₹{interest:,.2f}"
    }


# ======================== REVERSE CHARGE MECHANISM ========================

def compute_reverse_charge(rcm_purchases):
    """
    Reverse Charge Mechanism (RCM) — buyer pays GST directly.
    Applies to: legal services, GTA, import of services, etc.
    
    Args:
        rcm_purchases: list of dicts with:
            - amount: taxable value
            - rate: GST rate
            - description: str
            - is_interstate: bool
    
    Returns: RCM liability
    """
    total_rcm_liability = 0
    rcm_igst = 0
    rcm_cgst = 0
    rcm_sgst = 0
    items = []
    
    for purchase in rcm_purchases:
        amt = purchase.get("amount", 0)
        rate_key = str(purchase.get("rate", "18"))
        rate = get_gst_rate(rate_key)
        is_inter = purchase.get("is_interstate", False)
        
        gst = round(amt * rate, 2)
        split = split_gst(gst, is_inter)
        
        total_rcm_liability += gst
        rcm_igst += split["IGST"]
        rcm_cgst += split["CGST"]
        rcm_sgst += split["SGST"]
        
        items.append({
            "description": purchase.get("description", ""),
            "amount": amt,
            "rate": rate_key,
            "gst": gst,
            **split
        })
    
    return {
        "total_rcm_liability": round(total_rcm_liability, 2),
        "rcm_igst": round(rcm_igst, 2),
        "rcm_cgst": round(rcm_cgst, 2),
        "rcm_sgst": round(rcm_sgst, 2),
        "items": items,
        "itc_available": round(total_rcm_liability, 2),  # RCM paid is eligible for ITC
        "message": f"RCM Liability: ₹{total_rcm_liability:,.0f} (eligible for ITC after payment)"
    }


# ======================== E-INVOICE & COMPLIANCE ========================

def check_einvoice_required(annual_turnover):
    """E-invoice mandatory if turnover > ₹5Cr (from Oct 2023)."""
    threshold = 50000000  # ₹5 Crore
    required = annual_turnover > threshold
    return {
        "required": required,
        "threshold": threshold,
        "message": (
            f"E-Invoice {'REQUIRED' if required else 'NOT required'}. "
            f"Turnover ₹{annual_turnover:,.0f} vs threshold ₹{threshold/10000000:.0f}Cr."
        )
    }


# ======================== FILING CALENDAR ========================

GST_FILING_CALENDAR = {
    "GSTR-1": {
        "desc": "Outward Supplies",
        "frequency": "Monthly (>₹5Cr) / Quarterly (IFF)",
        "due_date": "11th of next month",
        "penalty": "₹50/day (₹20 nil)"
    },
    "GSTR-3B": {
        "desc": "Summary Return + Tax Payment",
        "frequency": "Monthly / Quarterly (QRMP)",
        "due_date": "20th of next month",
        "penalty": "₹50/day + 18% interest"
    },
    "GSTR-9": {
        "desc": "Annual Return",
        "frequency": "Yearly",
        "due_date": "31st December",
        "penalty": "₹200/day, max 0.5% of turnover"
    },
    "GSTR-9C": {
        "desc": "Reconciliation Statement (if >₹5Cr)",
        "frequency": "Yearly",
        "due_date": "31st December",
        "penalty": "Same as GSTR-9"
    },
    "CMP-08": {
        "desc": "Composition Scheme Return",
        "frequency": "Quarterly",
        "due_date": "18th of month after quarter",
        "penalty": "₹50/day"
    },
}


def get_filing_calendar():
    """Returns the GST filing calendar."""
    return GST_FILING_CALENDAR


# ======================== GST REPORT GENERATOR ========================

def generate_gst_report(profile, gstr3b_result, month_label=""):
    """
    Generates a text-based GST summary report.
    """
    r = gstr3b_result
    lines = []
    lines.append("=" * 60)
    lines.append("          GST RETURNS SUMMARY REPORT")
    lines.append("=" * 60)
    
    if profile:
        lines.append(f"Business    : {profile.get('name', 'N/A')}")
        lines.append(f"GSTIN       : {profile.get('gstin', 'N/A')}")
        lines.append(f"State       : {profile.get('state', 'N/A')}")
        lines.append(f"Type        : {profile.get('type', 'Regular')}")
    
    if month_label:
        lines.append(f"Period      : {month_label}")
    
    lines.append("-" * 60)
    lines.append("SECTION 1: OUTWARD SUPPLIES")
    lines.append("-" * 60)
    lines.append(f"  Taxable Sales     : ₹{r['total_taxable_sales']:>14,.2f}")
    lines.append(f"  Exempt Sales      : ₹{r['total_exempt_sales']:>14,.2f}")
    lines.append(f"  TOTAL SALES       : ₹{r['total_sales']:>14,.2f}")
    
    lines.append("")
    lines.append("-" * 60)
    lines.append("SECTION 2: OUTPUT TAX")
    lines.append("-" * 60)
    lines.append(f"  IGST              : ₹{r['output_igst']:>14,.2f}")
    lines.append(f"  CGST              : ₹{r['output_cgst']:>14,.2f}")
    lines.append(f"  SGST              : ₹{r['output_sgst']:>14,.2f}")
    lines.append(f"  TOTAL OUTPUT TAX  : ₹{r['total_output_tax']:>14,.2f}")
    
    lines.append("")
    lines.append("-" * 60)
    lines.append("SECTION 3: INPUT TAX CREDIT (ITC)")
    lines.append("-" * 60)
    lines.append(f"  Eligible ITC      : ₹{r['eligible_itc']:>14,.2f}")
    lines.append(f"  Ineligible ITC    : ₹{r['ineligible_itc']:>14,.2f}")
    lines.append(f"  Previous CF       : ₹{r['previous_credit']:>14,.2f}")
    lines.append(f"  TOTAL ITC         : ₹{r['total_itc']:>14,.2f}")
    
    lines.append("")
    lines.append("-" * 60)
    lines.append("SECTION 4: NET TAX PAYABLE")
    lines.append("-" * 60)
    lines.append(f"  Net IGST          : ₹{r['net_igst']:>14,.2f}")
    lines.append(f"  Net CGST          : ₹{r['net_cgst']:>14,.2f}")
    lines.append(f"  Net SGST          : ₹{r['net_sgst']:>14,.2f}")
    lines.append(f"  ─────────────────────────────────────")
    lines.append(f"  NET PAYABLE       : ₹{r['net_payable']:>14,.2f}")
    lines.append(f"  Carry Forward     : ₹{r['carry_forward_credit']:>14,.2f}")
    
    if r.get('recommendations'):
        lines.append("")
        lines.append("-" * 60)
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 60)
        for rec in r['recommendations']:
            lines.append(f"  • {rec}")
    
    lines.append("")
    lines.append("=" * 60)
    lines.append("  Generated by Intelligent Tax Assistant (ITA)")
    lines.append("=" * 60)
    
    return "\n".join(lines)
