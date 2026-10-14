import streamlit as st
import pandas as pd
import os
import sys
import numpy as np

try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# Add project root to path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

from src.logger import logger


try:
    from src.neural_parser import parse_with_neural_engine
    from src.classifier import tag_transactions, train_model
    from src.core.country_manager import CountryManager
    from src.reporter import generate_pdf_report
    from src.agent import TaxAdvisorAgent, AgentOrchestrator, LawSynthesizerAgent
    from src.countries.india.gst_engine import (
        compute_gstr3b, compute_gstr1_summary, compute_annual_gst,
        check_registration_required, compute_composition_tax,
        split_gst, get_gst_rate, HSN_SAC_EXAMPLES,
        compute_late_fees, compute_interest, compute_reverse_charge,
        check_einvoice_required, get_filing_calendar, generate_gst_report
    )
except ImportError as e:
    logger.critical(f"Failed to import modules: {e}")
    st.error(f"Failed to import modules: {e}")
    st.stop()

st.set_page_config(
    page_title="Intelligent Tax Assistant | AI CA",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for Premium Look & Responsive Design
st.markdown("""
<style>
    /* Base Styles */
    .main {
        padding: 2rem;
    }
    
    /* Responsive Metrics */
    .stMetric {
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        text-align: center;
        margin-bottom: 10px;
        border: 1px solid rgba(128,128,128,0.1);
    }
    
    /* Responsive Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        flex-wrap: wrap; /* Allow tabs to wrap on smaller screens */
    }
    .stTabs [data-baseweb="tab"] {
        height: auto;
        min-height: 50px;
        white-space: pre-wrap;
        border-radius: 5px 5px 0 0;
        gap: 1px;
        padding: 10px 15px;
        flex-grow: 1; /* Make tabs fill available space optimally */
        text-align: center;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4CAF50 !important;
        color: white !important;
    }
    
    /* Responsive Dataframes */
    .stDataFrame {
        width: 100% !important;
        overflow-x: auto;
    }
    
    /* Make buttons full width on small screens (<768px) */
    @media (max-width: 768px) {
        .stButton button {
            width: 100%;
        }
        
        /* Stack columns vertically on mobile */
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
            margin-bottom: 15px;
        }
        
        /* Reduce header sizes slightly on mobile */
        h1 { font-size: 2rem !important; }
        h2 { font-size: 1.5rem !important; }
        h3 { font-size: 1.25rem !important; }
    }
    
    /* Hyper-optimize for portrait mobile (<480px) */
    @media (max-width: 480px) {
        .main .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            padding-top: 2rem !important;
        }
        
        /* Tighter metrics for very small screens */
        .stMetric {
            padding: 10px !important;
            margin-bottom: 8px !important;
        }
        
        /* Compact tabs */
        .stTabs [data-baseweb="tab"] {
            padding: 8px 10px !important;
            font-size: 0.85rem !important;
            min-height: 40px !important;
        }
        
        /* Even smaller headers */
        h1 { font-size: 1.75rem !important; }
        h2 { font-size: 1.35rem !important; }
        h3 { font-size: 1.15rem !important; }
        
        /* More compact typography overall */
        p, span, div {
            font-size: 0.95rem;
        }
    }
    
    /* Improve Sidebar accessibility */
    .css-1d391kg {
        padding: 2rem 1rem;
    }
</style>
""", unsafe_allow_html=True)

def process_file_list(files, label, default_category=None):
    if not files: return []
    processed_dfs = []
    for f in files:
        temp_dir = os.path.join(root_dir, "data", "temp_uploads")
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, f.name)
        with open(temp_path, "wb") as file_obj:
            file_obj.write(f.getbuffer())
        
        logger.info(f"Processing {label}: {f.name}")
        df = parse_with_neural_engine(temp_path)
        
        if df is not None and not df.empty:
            if default_category: df['Tax_Category'] = default_category
            else: df = tag_transactions(df)
            df['Source_File'] = f.name
            processed_dfs.append(df)
        else:
            logger.error(f"Failed to extract text from {f.name}")
            st.warning(f"⚠️ Could not read transactions from {f.name} ({label})")
        
        if os.path.exists(temp_path): os.remove(temp_path)
    return processed_dfs

def main():
    st.title("🏛️ Intelligent Tax Assistant (ITA)")
    st.markdown("### FY 2025-26 Interactive Tax Wizard")

    if "processed_data" not in st.session_state: st.session_state.processed_data = None
    if "step" not in st.session_state: st.session_state.step = 1
    
    # Session State for User Inputs
    if "age" not in st.session_state: st.session_state.age = 30
    if "cash_inc" not in st.session_state: st.session_state.cash_inc = 0.0
    if "country" not in st.session_state: st.session_state.country = "India"
    if "hra_exemption" not in st.session_state: st.session_state.hra_exemption = 0.0
    if "deductions_extra" not in st.session_state: st.session_state.deductions_extra = 0.0
    
    manager = CountryManager()
    supported_countries = manager.get_supported_countries()

    # --- SIDEBAR: Uploads remain accessible always ---
    with st.sidebar:
        st.header("📂 1. Upload Documents")
        bank_files = st.file_uploader("Bank Stmts", type=["pdf"], accept_multiple_files=True, key="bank")
        salary_files = st.file_uploader("Form 16/Salary", type=["pdf"], accept_multiple_files=True, key="salary")
        cap_files = st.file_uploader("Capital Gains", type=["pdf"], accept_multiple_files=True, key="cap")
        ded_files = st.file_uploader("Deduction Proofs", type=["pdf"], accept_multiple_files=True, key="ded")
        
        st.divider()
        with st.expander("⚖️ Ingest New Law/Budget"):
            law_file = st.file_uploader("Upload Law/Budget (txt)", type=["txt"], key="law_upload")
            new_country = st.text_input("Country Name (if new)", "Synthetic Land")
            
            if st.button("Synthesize Tax Engine", type="secondary"):
                if law_file and new_country:
                    content = law_file.getvalue().decode("utf-8")
                    synthesizer = LawSynthesizerAgent(content)
                    schema = synthesizer.synthesize_rule_schema()
                    
                    # Save to Dynamic Rules
                    dyn_path = os.path.join(root_dir, "data", "dynamic_rules")
                    os.makedirs(dyn_path, exist_ok=True)
                    file_name = f"{new_country.lower().replace(' ', '_')}.json"
                    target_path = os.path.join(dyn_path, file_name)
                    
                    import json
                    with open(target_path, "w") as f:
                        json.dump(schema, f, indent=4)
                    
                    st.success(f"🚀 Successfully synthesized engine for {new_country}!")
                    st.info("The new engine is now available in the Country Selector.")
                    # Refresh Manager
                    manager.load_plugins()
                    st.rerun()
                else:
                    st.error("Please provide a file and a country name.")

            if st.button("Update Existing Regime (Budget)", type="secondary"):
                 if law_file and st.session_state.country:
                    content = law_file.getvalue().decode("utf-8")
                    synthesizer = LawSynthesizerAgent(content)
                    engine = manager.get_engine(st.session_state.country)
                    if hasattr(engine, 'rules'):
                        new_rules = synthesizer.calibrate_budget(engine.rules)
                        # Save back
                        rules_path = getattr(engine, 'rules_path', None)
                        if rules_path:
                            import json
                            with open(rules_path, "w") as f:
                                json.dump(new_rules, f, indent=4)
                            st.success(f"📈 Updated {st.session_state.country} regime with new budget!")
                            st.rerun()
                        else:
                            st.error("Cannot find rules path for this country.")
                    else:
                        st.error("This country engine does not support dynamic updates.")

        st.divider()
        st.header("⚙️ Execution Control")
        if st.button("Process Documents", type="primary"):
            if not (bank_files or salary_files or cap_files or ded_files):
                st.error("Upload at least one file.")
            else:
                with st.spinner("Analyzing..."):
                    all_dfs = []
                    all_dfs.extend(process_file_list(bank_files, "Bank", None))
                    all_dfs.extend(process_file_list(salary_files, "Form16", "SALARY"))
                    all_dfs.extend(process_file_list(cap_files, "CapGains", "STCG"))
                    all_dfs.extend(process_file_list(ded_files, "DedProofs", "80C_INVEST"))
                    
                    if all_dfs:
                        st.session_state.processed_data = pd.concat(all_dfs, ignore_index=True)
                        st.success(f"✅ Extracted {len(st.session_state.processed_data)} txns!")
                    else:
                        st.error("No valid data found.")

    # --- WIZARD FLOW ---
     
    # STEP 1: REVIEW DATA & BASIC INFO
    if st.session_state.step == 1:
        st.header("Step 1: Your Financial Profile")
        
        if st.session_state.processed_data is not None:
             st.info("Please review the extracted transactions below. PRO TIP: Correcting categories teaches the AI! 🧠")
             CATEGORIES = ["BUSINESS_REV", "BUSINESS_EXP", "SALARY", "80C_INVEST", "STCG", "LTCG", "PERSONAL", "SELF_TRANSFER", "UNCATEGORIZED"]
             
             # EXPLICIT UNCATEGORIZED QUESTIONING
             uncategorized = st.session_state.processed_data[st.session_state.processed_data['Tax_Category'] == 'UNCATEGORIZED']
             if not uncategorized.empty:
                 st.warning(f"⚠️ We found {len(uncategorized)} uncategorized transaction(s). Please explicitly categorize them below:")
                 
                 # Only ask for one at a time for true dynamic recategorization
                 row_to_ask = uncategorized.iloc[0]
                 idx_to_ask = uncategorized.index[0]
                 
                 with st.container(border=True):
                     desc = row_to_ask.get('Description', 'N/A')
                     amt = row_to_ask.get('Withdrawal', 0) if pd.notna(row_to_ask.get('Withdrawal')) and float(row_to_ask.get('Withdrawal', 0)) > 0 else row_to_ask.get('Deposit', 0)
                     st.markdown(f"**Description:** `{desc}` | **Amount:** {amt}")
                     
                     new_cat = st.selectbox(
                         f"What category is this?", 
                         options=["UNCATEGORIZED"] + CATEGORIES[:-1], 
                         key=f"cat_exp_dynamic"
                     )
                     
                     if new_cat != "UNCATEGORIZED":
                         with st.spinner("🧠 AI is learning and recategorizing everything..."):
                             # 1. Update EVERY transaction with this exact description
                             st.session_state.processed_data.loc[
                                 st.session_state.processed_data['Description'] == desc, 
                                 ['Tax_Category', 'Source', 'Confidence_Score']
                             ] = [new_cat, "User Verified", 1.0]
                             
                             # 2. Train the AI model
                             train_model([desc], [new_cat])
                             
                             # 3. Trigger a full recategorization of remaining UNCATEGORIZED items
                             st.session_state.processed_data = tag_transactions(st.session_state.processed_data)
                             
                             st.toast(f"✅ Learned: `{desc}` is `{new_cat}`. Other transactions updated!")
                             st.rerun()

             # Capture the edited dataframe
             edited_df = st.data_editor(
                st.session_state.processed_data,
                column_config={
                    "Tax_Category": st.column_config.SelectboxColumn("Category", options=CATEGORIES, required=True),
                    "Confidence_Score": st.column_config.NumberColumn("Conf.", format="%.2f"),
                    "Source": st.column_config.TextColumn("Inference Source")
                },
                hide_index=True, use_container_width=True, num_rows="fixed",
                key="data_editor"
            )
             # Update session state with edits
             st.session_state.processed_data = edited_df
        else:
             st.info("👈 Please verify uploaded documents in the sidebar first (if any).")

        st.subheader("Personal Details")
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            st.session_state.country = st.selectbox("Select Country Jurisdiction", supported_countries, index=supported_countries.index(st.session_state.country) if st.session_state.country in supported_countries else 0)
        
        # Determine supported tax years for selected country
        country_engine = manager.get_engine(st.session_state.country)
        supported_years = country_engine.get_supported_years() if hasattr(country_engine, "get_supported_years") else ["2024"]
        if "tax_year" not in st.session_state or st.session_state.tax_year not in supported_years:
            st.session_state.tax_year = supported_years[0] if supported_years else "2024"
            
        with col_c2:
            st.session_state.tax_year = st.selectbox("Select Tax Year", supported_years, index=supported_years.index(st.session_state.tax_year) if st.session_state.tax_year in supported_years else 0)
            if hasattr(country_engine, "set_tax_year"):
                country_engine.set_tax_year(st.session_state.tax_year)
                
        with col_c3:
            st.session_state.age = st.number_input("What is your Age?", 18, 100, st.session_state.age)
            
        st.session_state.cash_inc = st.number_input("Any Cash Income (not in bank)?", 0.0, step=1000.0, value=st.session_state.cash_inc)
        
        if st.button("Next: Tax Calculations ➡️"):
            # TRIGGER AI TRAINING HERE
            if st.session_state.processed_data is not None:
                df = st.session_state.processed_data
                # We simply retrain on ALL current data. 
                # Ideally we only train on *changes*, but training on validated data is also fine for SGD.
                # It reinforces the correct mappings.
                train_model(df['Description'].tolist(), df['Tax_Category'].tolist())
                st.toast("🧠 AI has learned from your corrections!")
            
            st.session_state.step = 2
            st.rerun()

    # STEP 2: COUNTRY SPECIFIC INTERVIEW
    elif st.session_state.step == 2:
        engine = manager.get_engine(st.session_state.country)
        if hasattr(engine, "get_ui_tabs"):
            st.header(f"Step 2: {st.session_state.country} Tax Interview (Agent Mode 🕵️)")
            st.caption("Exhaustive country-specific tax coverage.")
            
            # Render Dynamic UI using Engine's definition
            tabs_data = engine.get_ui_tabs()
            
            # Create actual Streamlit Tabs
            st_tabs = st.tabs([t["tab_name"] for t in tabs_data])
            
            # Dictionary to store the collected values
            collected_inputs = {}
            
            for tab_idx, tab in enumerate(tabs_data):
                with st_tabs[tab_idx]:
                    for comp in tab.get("components", []):
                        comp_type = comp.get("type")
                        comp_id = comp.get("id")
                        label = comp.get("label")
                        help_text = comp.get("help", "")
                        
                        # Apply condition check if needed (advanced feature)
                        # Currently just rendering everything flat
                        if comp_type == "number":
                            collected_inputs[comp_id] = st.number_input(
                                label, 
                                min_value=0.0, 
                                value=0.0,
                                step=500.0, 
                                help=help_text, 
                                key=f"dynamic_{comp_id}"
                            )
                        elif comp_type == "checkbox":
                            val = st.checkbox(label, help=help_text, key=f"dynamic_{comp_id}")
                            # The engine expects 1/0 or actual money values instead of True/False for some checkboxes
                            # So we store 1 for true, 0 for false if it's a known pattern, but bool is okay too
                            collected_inputs[comp_id] = 1 if val else 0
                        elif comp_type == "toggle":
                            # Use checkbox for 'toggle' conceptually
                            collected_inputs[comp_id] = st.checkbox(label, help=help_text, key=f"dynamic_{comp_id}")
            
            st.session_state.deductions_extra = collected_inputs
            
        else:
             # Fallback just in case a plugin isn't fully updated
             st.error("This country plugin is missing the interactive wizard UI.")
        
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Back"):
                st.session_state.step = 1
                st.rerun()
        with col2:
            if st.button("Analyze & Calculate 🚀", type="primary"):
                st.session_state.step = 3
                st.rerun()

    # STEP 3: RESULTS & AGENT INSIGHTS
    elif st.session_state.step == 3:
        st.header("📊 Digital CA Dashboard")
        
        # Fetch the selected Engine first so we can use its methods
        engine = manager.get_engine(st.session_state.country)
        
        summary = engine.get_financial_summary(st.session_state.processed_data) if st.session_state.processed_data is not None else {}
        
        with st.sidebar:
            st.header("🔮 What-If Simulator")
            # Create a clone of deductions_extra for simulation
            sim_deds = st.session_state.deductions_extra.copy() if hasattr(st.session_state.deductions_extra, 'copy') else {}
            
            if hasattr(engine, "get_simulation_sliders"):
                sliders = engine.get_simulation_sliders()
                if sliders:
                    st.write("Simulate tax savings by adjusting your investments:")
                    for s in sliders:
                        # Ensure we inject the correct currency symbol into the slider labels
                        label = s["label"].replace("₹", engine.currency_symbol).replace("$", engine.currency_symbol)
                        val = st.slider(label, s["min"], s["max"], s["default"], step=s["step"])
                        sim_deds[s["id"]] = sim_deds.get(s["id"], 0) + val
            elif st.session_state.country == "India":
                # Fallback for India if not yet explicitly implemented in engine
                st.write("Simulate tax savings by adjusting your investments:")
                sim_80c = st.slider(f"Additional 80C Investment ({engine.currency_symbol})", 0, 150000, 0, step=5000)
                sim_80d = st.slider(f"Additional 80D (Health) ({engine.currency_symbol})", 0, 50000, 0, step=1000)
                sim_nps = st.slider(f"Additional NPS (Tier 1) ({engine.currency_symbol})", 0, 50000, 0, step=5000)
                sim_deds["80C"] = sim_deds.get("80C", 0) + sim_80c
                sim_deds["80D_self"] = sim_deds.get("80D_self", 0) + sim_80d
                sim_deds["NPS"] = sim_deds.get("NPS", 0) + sim_nps

        
        
        res = engine.compute_tax_liability(
            summary,
            st.session_state.age,
            st.session_state.cash_inc,
            st.session_state.hra_exemption,
            sim_deds
        )
        
        # Initialize Hyper-Agentic Orchestrator
        orchestrator = AgentOrchestrator(res)
        agent_strategy = orchestrator.orchestrate()

        # Tabs for better organization
        tab_summary, tab_viz, tab_agent, tab_details = st.tabs(["📊 Tax Summary", "📈 Visual Analytics", "🕵️ Agent Strategy", "🔍 Compliance Details"])

        with tab_summary:
            # Comparison
            st.subheader(f"Tax Liability Comparison ({st.session_state.country})")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Strategy A Tax", f"{engine.currency_symbol} {res['old_final_tax']:,.2f}")
            with c2:
                st.metric("Strategy B Tax", f"{engine.currency_symbol} {res['new_final_tax']:,.2f}")
            with c3:
                diff = res['old_final_tax'] - res['new_final_tax']
                st.metric("Net Savings", f"{engine.currency_symbol} {abs(diff):,.2f}", delta=f"{'B' if diff > 0 else 'A'} is better")

            if diff < 0:
                st.success(f"🏆 **Recommendation**: Choose **STRATEGY A**. Total Optimized Tax: {engine.currency_symbol} {res['old_final_tax']:,.0f}")
            else:
                st.success(f"🏆 **Recommendation**: Choose **STRATEGY B**. Total Optimized Tax: {engine.currency_symbol} {res['new_final_tax']:,.0f}")
            
            st.info(f"💡 **Wealth Alert**: Reinvesting your tax savings of {engine.currency_symbol}{abs(diff):,.0f} annually could grow to **{engine.currency_symbol}{agent_strategy['wealth_impact']:,.0f}** in 10 years (at 10% CAGR)!")

        with tab_viz:
            if HAS_PLOTLY:
                col_v1, col_v2 = st.columns(2)
                
                with col_v1:
                    st.subheader("Income Composition")
                    income_data = {
                        "Category": ["Salary", "Business", "CapGains", "Other"],
                        "Amount": [res.get('salary', summary.get('salary', 0)), 
                                  res.get('business', summary.get('business_inc', 0)), 
                                  (res.get('stcg', 0) + res.get('ltcg', 0)) or (summary.get('stcg', 0) + summary.get('ltcg', 0)),
                                  res.get('other', summary.get('other_inc', 0))]
                    }
                    fig_pie = px.pie(income_data, values='Amount', names='Category', hole=.3, 
                                     color_discrete_sequence=px.colors.sequential.RdBu)
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                with col_v2:
                    st.subheader("Regime Comparison")
                    regime_df = pd.DataFrame({
                        "Regime": ["Old", "New"],
                        "Tax Payable": [res['old_final_tax'], res['new_final_tax']]
                    })
                    fig_bar = px.bar(regime_df, x="Regime", y="Tax Payable", 
                                     color="Regime", color_discrete_map={"Old": "#EF553B", "New": "#636EFA"})
                    st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.warning("Install `plotly` to view interactive charts.")

        with tab_agent:
            st.subheader("🕵️ Agent's Reasoning & Multi-Step Strategy")
            
            col_a1, col_a2 = st.columns([1, 2])
            with col_a1:
                st.markdown("### 🧠 Thought Log")
                for thought in agent_strategy["thoughts"]:
                    st.caption(f"• {thought}")
            
            with col_a2:
                st.markdown("### 🚀 Refined Wealth Strategy")
                for action in agent_strategy["actions"]:
                    with st.container(border=True):
                        st.markdown(f"**Step**: {action['step']}")
                        st.markdown(f"**Instrument**: {action['instrument']}")
                        if 'risk_alert' in action:
                            st.warning(f"🕵️ Auditor Alert: {action['risk_alert']}")
                        st.success(f"💡 {action['impact']}")

            st.divider()
            with st.expander("📝 View Adversarial Deliberation Log"):
                for entry in agent_strategy["deliberation"]:
                    st.write(f"• {entry}")

            st.divider()
            st.markdown(f"**Final Agent Verdict**: {agent_strategy['final_recommendation']}")

        with tab_details:
            st.subheader("Compliance & Detailed Deduction Breakdown")
            # Create a nice dataframe for deductions
            deds_df = pd.DataFrame(res["deductions_breakdown"].items(), columns=["Provision/Section", f"Amount ({engine.currency_symbol})"])
            st.dataframe(deds_df[deds_df[f"Amount ({engine.currency_symbol})"] > 0], hide_index=True, use_container_width=True)
        
        st.divider()
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            if st.button("📄 Download Professional AI-CA Report", type="primary"):
                p = generate_pdf_report("User", st.session_state.age, summary, res)
                with open(p, "rb") as f:
                    st.download_button("Click to Download PDF", f, file_name=os.path.basename(p))
        with col_f2:
            if st.button("🔄 Restart Wizard"):
                st.session_state.step = 1
                st.rerun()




if __name__ == "__main__":
    main()
