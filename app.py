import os
import time
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from underwriter import (
    calculate_dscr_underwriting,
    lookup_town_compliance,
    parse_listing_input,
    DEFAULT_INTEREST_RATE,
    DEFAULT_OPEX_RATIO,
    DEFAULT_CASH_RESERVES
)
from supabase_db import DatabaseManager, generate_notebooklm_markdown

# Page Config (Mobile-Optimized Title and Wide Layout)
st.set_page_config(
    page_title="Upstate NY DSCR Underwriter & Vault",
    page_icon="🏡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom Mobile CSS Styling
st.markdown("""
<style>
    .main { padding: 1rem; }
    .stButton button { width: 100%; border-radius: 8px; height: 3rem; font-weight: bold; }
    .tier-a-badge {
        background-color: #E3F2FD; color: #0D47A1; padding: 14px; border-radius: 8px;
        border-left: 6px solid #1976D2; font-weight: bold; margin-bottom: 15px;
    }
    .tier-b-badge {
        background-color: #E8F5E9; color: #1B5E20; padding: 14px; border-radius: 8px;
        border-left: 6px solid #388E3C; font-weight: bold; margin-bottom: 15px;
    }
    .tier-mid-badge {
        background-color: #FFF3E0; color: #E65100; padding: 14px; border-radius: 8px;
        border-left: 6px solid #F57C00; font-weight: bold; margin-bottom: 15px;
    }
    .metric-card {
        background-color: #F8F9FA; padding: 12px; border-radius: 8px; border: 1px solid #E0E0E0; text-align: center;
    }
    .tel-link {
        display: inline-block; background-color: #0288D1; color: white !important;
        padding: 10px 18px; border-radius: 6px; text-decoration: none; font-weight: bold; margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Password Authentication Check
def check_password():
    if "APP_PASSWORD" in st.secrets:
        target_pw = st.secrets["APP_PASSWORD"]
    else:
        target_pw = "upstate-investor"

    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.title("🔒 Security Access Check")
        pw_input = st.text_input("Enter Access Password:", type="password")
        if st.button("Unlock Dashboard"):
            if pw_input == target_pw:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Incorrect password.")
        st.stop()

check_password()

# Initialize Supabase Database Manager
@st.cache_resource
def get_db():
    supabase_url = st.secrets.get("supabase", {}).get("SUPABASE_URL", "")
    supabase_key = st.secrets.get("supabase", {}).get("SUPABASE_KEY", "")
    return DatabaseManager(supabase_url, supabase_key)

db = get_db()

# Main Header
st.title("🏡 Upstate NY DSCR Underwriter & Shared Vault")
st.caption("24/7 Multi-Device Real Estate Underwriting, Zoning Compliance & Capital Shielding Platform")

# Tabs
tab1, tab2, tab3 = st.tabs(["🔎 Analyze Property", "📁 Shared Property Vault", "📥 NotebookLM Exporter"])

# ==========================================
# TAB 1: ANALYZE PROPERTY
# ==========================================
with tab1:
    st.subheader("1. Property Ingestion & Underwriting Parameters")

    user_input = st.text_input(
        "Drop Zillow/Redfin Listing URL or paste listing text:",
        placeholder="https://www.redfin.com/NY/Kerhonkson/142-Samsonville-Rd-12446/home/...",
        help="Paste any real estate URL or raw listing text containing price, zip code, and beds/baths."
    )

    parsed = parse_listing_input(user_input)

    col_a, col_b, col_c = st.columns([2, 1, 1])
    with col_a:
        address = st.text_input("Property Address:", value=parsed["address"])
    with col_b:
        zip_code = st.text_input("ZIP Code:", value=parsed["zip_code"])
    with col_c:
        price = st.number_input("Purchase Price ($):", min_value=100000.0, max_value=2000000.0, value=float(parsed["price"]), step=10000.0)

    col_d, col_e, col_f, col_g = st.columns(4)
    with col_d:
        beds = st.number_input("Bedrooms:", min_value=1, max_value=10, value=parsed["beds"])
    with col_e:
        baths = st.number_input("Bathrooms:", min_value=1.0, max_value=10.0, value=float(parsed["baths"]), step=0.5)
    with col_f:
        lot_acres = st.number_input("Lot Size (Acres):", min_value=0.1, max_value=100.0, value=float(parsed["lot_size_acres"]), step=0.1)
    with col_g:
        cash_reserves = st.number_input("Liquid Capital Pool ($):", min_value=50000.0, max_value=500000.0, value=DEFAULT_CASH_RESERVES, step=10000.0)

    st.markdown("---")
    st.subheader("2. Financial Underwriting Controls")

    col_h, col_i, col_j, col_k = st.columns(4)
    with col_h:
        interest_rate = st.number_input("DSCR Interest Rate (%):", min_value=4.0, max_value=12.0, value=DEFAULT_INTEREST_RATE, step=0.25)
    with col_i:
        projected_adr = st.number_input("Projected ADR ($):", min_value=150.0, max_value=1500.0, value=380.0, step=10.0)
    with col_j:
        projected_occ = st.number_input("Projected Occupancy (%):", min_value=10.0, max_value=95.0, value=58.0, step=1.0)
    with col_k:
        opex_ratio = st.number_input("Opex Ratio (%):", min_value=10.0, max_value=50.0, value=DEFAULT_OPEX_RATIO, step=1.0)

    # Execute Underwriting
    uw = calculate_dscr_underwriting(
        price=price,
        projected_adr=projected_adr,
        projected_occ_pct=projected_occ,
        interest_rate=interest_rate,
        opex_ratio=opex_ratio,
        cash_reserves_pool=cash_reserves,
        broker_contact=parsed["broker_contact"]
    )

    compliance = lookup_town_compliance(zip_code)

    st.markdown("---")
    st.subheader("3. Tiered Capital Shielding & Underwriting Output")

    # Render Tier Indicator Badge
    if "Tier A" in uw["tier_level"]:
        st.markdown(f'<div class="tier-a-badge"><strong>🔵 {uw["tier_level"]}</strong><br>{uw["tier_badge"]}</div>', unsafe_allow_html=True)
    elif "Tier B" in uw["tier_level"]:
        st.markdown(f'<div class="tier-b-badge"><strong>🟢 {uw["tier_level"]}</strong><br>{uw["tier_badge"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="tier-mid-badge"><strong>🟠 {uw["tier_level"]}</strong><br>{uw["tier_badge"]}</div>', unsafe_allow_html=True)

    # Live Renovation Capital Runway Panel
    st.markdown("#### 💳 Capital Outlay & Renovation Runway Panel")
    panel_col1, panel_col2, panel_col3, panel_col4 = st.columns(4)
    with panel_col1:
        st.metric("Down Payment", f"${uw['down_payment_amt']:,.0f}", f"{uw['down_payment_pct']:.0f}% Metric")
    with panel_col2:
        st.metric("Closing Costs (3%)", f"${uw['closing_costs']:,.0f}")
    with panel_col3:
        st.metric("Total Cash Outlay", f"${uw['total_outlay']:,.0f}")
    with panel_col4:
        st.metric("Retained Renovation Runway", f"${uw['retained_capital']:,.0f}")

    if "Tier B" in uw["tier_level"]:
        st.write(f"**Tier B Renovation Runway Progress:** ${uw['retained_capital']:,.0f} retained of $200,000 target for guest studio/landscaping.")
        st.progress(uw["progress_ratio"])

    # Executive Investment Summary Note-Card
    st.markdown("---")
    st.markdown("### 📝 Executive Investment Summary Note-Card")

    if uw["dscr_pass"] and "Tier B" in uw["tier_level"]:
        verdict_title = "🟢 HIGH-POTENTIAL VALUE-ADD CANVAS"
        verdict_color = "#2E7D32"
        verdict_bg = "#E8F5E9"
        verdict_border = "#81C784"
    elif uw["dscr_pass"] and "Tier A" in uw["tier_level"]:
        verdict_title = "🔵 LUXURY TURNKEY INVESTMENT ESTATE"
        verdict_color = "#1565C0"
        verdict_bg = "#E3F2FD"
        verdict_border = "#64B5F6"
    elif not uw["dscr_pass"]:
        verdict_title = "🔴 UNDERWRITING CAUTION: DSCR BELOW 1.20x"
        verdict_color = "#C62828"
        verdict_bg = "#FFEBEE"
        verdict_border = "#EF9A9A"
    else:
        verdict_title = "🟠 STANDARD STRATEGIC ACQUISITION"
        verdict_color = "#EF6C00"
        verdict_bg = "#FFF3E0"
        verdict_border = "#FFB74D"

    note_card_html = f"""
    <div style="background-color: {verdict_bg}; border: 2px solid {verdict_border}; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 25px; color: #1A1A1A;">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid {verdict_border}; padding-bottom: 10px; margin-bottom: 15px;">
            <h3 style="margin: 0; color: {verdict_color}; font-size: 1.3rem;">{verdict_title}</h3>
            <span style="font-weight: bold; background: white; padding: 4px 12px; border-radius: 20px; border: 1px solid {verdict_border}; color: #333;">{address}</span>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; margin-bottom: 15px;">
            <div style="background: white; padding: 12px; border-radius: 8px; border: 1px solid #E0E0E0;">
                <strong style="color: #555;">💰 Capital Required:</strong><br>
                <span style="font-size: 1.2rem; font-weight: bold; color: #1A1A1A;">${uw['total_outlay']:,.0f}</span>
                <span style="font-size: 0.85rem; color: #666;"><br>({uw['down_payment_pct']:.0f}% Down + 3% Closing)</span>
            </div>
            <div style="background: white; padding: 12px; border-radius: 8px; border: 1px solid #E0E0E0;">
                <strong style="color: #555;">🛡️ Retained Capital Runway:</strong><br>
                <span style="font-size: 1.2rem; font-weight: bold; color: {verdict_color};">${uw['retained_capital']:,.0f}</span>
                <span style="font-size: 0.85rem; color: #666;"><br>(Available for Studio & Pool)</span>
            </div>
            <div style="background: white; padding: 12px; border-radius: 8px; border: 1px solid #E0E0E0;">
                <strong style="color: #555;">📈 Debt Coverage (DSCR):</strong><br>
                <span style="font-size: 1.2rem; font-weight: bold; color: {'#2E7D32' if uw['dscr_pass'] else '#C62828'};">{uw['dscr_ratio']:.2f}x</span>
                <span style="font-size: 0.85rem; color: #666;"><br>({'PASSES >= 1.20x' if uw['dscr_pass'] else 'NEEDS HIGHER ADR/OCC'})</span>
            </div>
            <div style="background: white; padding: 12px; border-radius: 8px; border: 1px solid #E0E0E0;">
                <strong style="color: #555;">🌙 Target STR Performance:</strong><br>
                <span style="font-size: 1.2rem; font-weight: bold; color: #1A1A1A;">${projected_adr:.0f}/night</span>
                <span style="font-size: 0.85rem; color: #666;"><br>at {projected_occ:.0f}% Occupancy (${uw['monthly_gross_revenue']:,.0f}/mo)</span>
            </div>
        </div>
        <div style="background: white; padding: 15px; border-radius: 8px; border-left: 4px solid {verdict_color};">
            <h4 style="margin: 0 0 8px 0; color: #333;">💡 Strategic Takeaways & Action Plan:</h4>
            <ul style="margin: 0; padding-left: 20px; font-size: 0.95rem; line-height: 1.5; color: #333;">
                <li><strong>Development Strategy:</strong> {'Retains $' + f"{uw['retained_capital']:,.0f}" + ' capital runway. Target a detached guest studio (no kitchen) under a single STR permit.' if 'Tier B' in uw['tier_level'] else 'Turnkey property requiring zero major capital outlays.'}</li>
                <li><strong>Zoning & Septic Audit:</strong> Property sits in <strong>{compliance['town']}</strong> ({compliance['str_risk']}). Lot size is <strong>{lot_acres:.2f} Acres</strong> ({'Meets 2.0+ Acre Rule' if lot_acres >= compliance['min_lot_acres'] else 'Below District Min'}). Maintain 20-ft septic isolation for any pool/hot tub build.</li>
                <li><strong>Operating Requirement:</strong> Must assign a local contact/property manager within {compliance['local_manager_rule']}.</li>
            </ul>
        </div>
    </div>
    """
    st.markdown(note_card_html, unsafe_allow_html=True)

    # Town & Zoning Compliance Output
    st.markdown("---")
    st.subheader("4. Municipal Zoning & STR Compliance Audit")

    z_col1, z_col2 = st.columns(2)
    with z_col1:
        st.write(f"**Town/Municipality:** {compliance['town']} ({compliance['county']} County)")
        st.write(f"**STR Regulatory Risk:** **{compliance['str_risk']}**")
        st.write(f"**Permit Cap Status:** {compliance['cap_status']}")
        st.write(f"**Local Manager Rule:** {compliance['local_manager_rule']}")
        lot_status = "✅ Meets 2.0+ Acre Rule" if lot_acres >= compliance["min_lot_acres"] else f"⚠️ Below District Min ({compliance['min_lot_acres']} Acres)"
        st.write(f"**Lot Size Check:** {lot_acres:.2f} Acres ({lot_status})")

    with z_col2:
        st.write(f"**Detached Guest Studio Rule:** {compliance['guest_studio_rule']}")
        st.write(f"**Kitchen ADU STR Mandate:** {compliance['adu_kitchen_rule']}")
        st.write(f"**Pool & Septic Isolation:** {compliance['pool_septic_setback']}")
        st.write(f"**Building Height Limit:** {compliance['height_limit']}")

    # Click to Call Broker Field
    st.markdown(f'<a href="tel:8455550199" class="tel-link">📞 {parsed["broker_contact"]}</a>', unsafe_allow_html=True)

    # Save Property to Vault Form
    st.markdown("---")
    st.subheader("5. Archive Property to Shared Vault")
    save_col1, save_col2, save_col3 = st.columns([1, 1, 1])
    with save_col1:
        added_by = st.selectbox("Property Evaluated By:", ["Andrew", "Gab"])
    with save_col2:
        rating = st.slider("Property Rating (1 to 5 Stars):", 1, 5, 4)
    with save_col3:
        prop_status = st.selectbox("Acquisition Status:", ["Interested", "Offer Made", "Passed", "Under Contract"])

    user_notes = st.text_area("Investment & Renovation Notes:", placeholder="Add notes on layout, pool location, or septic condition...")

    if st.button("💾 Save Property to Shared Vault"):
        prop_record = {
            "address": address,
            "zip_code": zip_code,
            "town": compliance["town"],
            "price": price,
            "down_payment_pct": uw["down_payment_pct"],
            "down_payment_amt": uw["down_payment_amt"],
            "closing_costs": uw["closing_costs"],
            "total_outlay": uw["total_outlay"],
            "retained_capital": uw["retained_capital"],
            "monthly_piti": uw["monthly_piti"],
            "projected_adr": projected_adr,
            "projected_occ": projected_occ,
            "monthly_revenue": uw["monthly_gross_revenue"],
            "dscr_ratio": uw["dscr_ratio"],
            "tier_level": uw["tier_level"],
            "tier_badge": uw["tier_badge"],
            "lot_size_acres": lot_acres,
            "str_risk": compliance["str_risk"],
            "broker_contact": parsed["broker_contact"],
            "rating": rating,
            "user_notes": user_notes,
            "added_by": added_by,
            "status": prop_status,
            "url": parsed["raw_url"]
        }
        if db.save_property(prop_record):
            st.success(f"Successfully archived '{address}' to shared vault!")
            time.sleep(1)
            st.rerun()

# ==========================================
# TAB 2: SHARED PROPERTY VAULT
# ==========================================
with tab2:
    st.subheader("📁 Shared Property Vault & Comparison Workspace")
    properties = db.get_all_properties()

    if not properties:
        st.info("No properties currently saved in the vault. Analyze and save properties in Tab 1!")
    else:
        df_vault = pd.DataFrame(properties)

        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            status_filter = st.multiselect("Filter by Status:", options=list(df_vault["status"].unique()), default=list(df_vault["status"].unique()))
        with f_col2:
            min_dscr = st.slider("Filter Min DSCR Ratio:", 0.0, 3.0, 1.0, 0.1)
        with f_col3:
            rating_filter = st.slider("Filter Min Rating (Stars):", 1, 5, 1)

        filtered_df = df_vault[
            (df_vault["status"].isin(status_filter)) &
            (df_vault["dscr_ratio"] >= min_dscr) &
            (df_vault["rating"] >= rating_filter)
        ]

        st.markdown(f"**Showing {len(filtered_df)} of {len(df_vault)} Archived Properties**")

        display_cols = ["address", "price", "tier_level", "dscr_ratio", "retained_capital", "town", "rating", "status", "added_by"]
        st.dataframe(filtered_df[display_cols], use_container_width=True)

        st.markdown("---")
        st.subheader("Manage Saved Properties")
        selected_addr = st.selectbox("Select Property to Manage:", options=filtered_df["address"].tolist())
        if selected_addr:
            selected_prop = filtered_df[filtered_df["address"] == selected_addr].iloc[0]
            st.write(f"**Address:** {selected_prop['address']}")
            st.write(f"**Tier:** {selected_prop['tier_level']} | **DSCR:** {selected_prop['dscr_ratio']:.2f}x")
            st.write(f"**Notes:** {selected_prop['user_notes']}")

            if st.button("🗑️ Delete Property from Vault"):
                if db.delete_property(selected_addr):
                    st.success(f"Deleted {selected_addr}")
                    time.sleep(1)
                    st.rerun()

# ==========================================
# TAB 3: NOTEBOOKLM EXPORTER
# ==========================================
with tab3:
    st.subheader("📥 NotebookLM Markdown Exporter")
    st.write("Generate and download a clean, table-heavy Markdown file formatted for direct ingestion into your Google NotebookLM project vault.")

    properties_for_export = db.get_all_properties()
    markdown_content = generate_notebooklm_markdown(properties_for_export)

    st.download_button(
        label="📥 Download daily_listings_scan.md for NotebookLM",
        data=markdown_content,
        file_name="daily_listings_scan.md",
        mime="text/markdown"
    )

    st.markdown("---")
    st.subheader("Live Markdown Preview")
    st.code(markdown_content, language="markdown")
