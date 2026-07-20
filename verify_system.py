import sys
import os
import time

from underwriter import calculate_dscr_underwriting, lookup_town_compliance, parse_listing_input
from supabase_db import DatabaseManager, generate_notebooklm_markdown

def run_system_verification():
    print("=" * 70)
    print("      RUNNING TIERED CAPITAL SHIELDING SYSTEM VERIFICATION")
    print("=" * 70)

    db = DatabaseManager()

    # -------------------------------------------------------------
    # SCENARIO 1: $950,000 Tier A Luxury Turnkey Property
    # -------------------------------------------------------------
    print("\n[TEST 1] Testing $950,000 Luxury Turnkey Scenario (Tier A)...")
    uw_tier_a = calculate_dscr_underwriting(
        price=950000.0,
        projected_adr=650.0,
        projected_occ_pct=62.0,
        interest_rate=7.5,
        opex_ratio=30.0,
        cash_reserves_pool=200000.0,
        broker_contact="Luxury Broker (845-555-9999)"
    )
    comp_a = lookup_town_compliance("12446")

    print(f"  - Tier Level: {uw_tier_a['tier_level']}")
    print(f"  - Down Payment: ${uw_tier_a['down_payment_amt']:,.2f} ({uw_tier_a['down_payment_pct']:.0f}%)")
    print(f"  - Closing Costs (3%): ${uw_tier_a['closing_costs']:,.2f}")
    print(f"  - Total Outlay: ${uw_tier_a['total_outlay']:,.2f}")
    print(f"  - Retained Capital Runway: ${uw_tier_a['retained_capital']:,.2f}")
    print(f"  - Monthly PITI: ${uw_tier_a['monthly_piti']:,.2f}")
    print(f"  - Monthly Gross STR Revenue: ${uw_tier_a['monthly_gross_revenue']:,.2f}")
    print(f"  - DSCR Ratio: {uw_tier_a['dscr_ratio']:.2f}x ({'PASS' if uw_tier_a['dscr_pass'] else 'FAIL'})")
    print(f"  - Tier Badge Text: {uw_tier_a['tier_badge']}")

    assert uw_tier_a['tier_level'] == "Tier A: Luxury Turnkey", "Failed: Tier A level mismatch"
    assert uw_tier_a['down_payment_pct'] == 20.0, "Failed: Tier A down payment pct must be capped at 20%"
    assert uw_tier_a['down_payment_amt'] == 190000.0, "Failed: Tier A down payment calculation incorrect"

    prop_a = {
        "address": "100 Mountain View Rd, Kerhonkson, NY 12446",
        "zip_code": "12446",
        "town": comp_a["town"],
        "price": 950000.0,
        "down_payment_pct": uw_tier_a["down_payment_pct"],
        "down_payment_amt": uw_tier_a["down_payment_amt"],
        "closing_costs": uw_tier_a["closing_costs"],
        "total_outlay": uw_tier_a["total_outlay"],
        "retained_capital": uw_tier_a["retained_capital"],
        "monthly_piti": uw_tier_a["monthly_piti"],
        "projected_adr": 650.0,
        "projected_occ": 62.0,
        "monthly_revenue": uw_tier_a["monthly_gross_revenue"],
        "dscr_ratio": uw_tier_a["dscr_ratio"],
        "tier_level": uw_tier_a["tier_level"],
        "tier_badge": uw_tier_a["tier_badge"],
        "lot_size_acres": 4.5,
        "str_risk": comp_a["str_risk"],
        "broker_contact": uw_tier_a["broker_contact"],
        "rating": 5,
        "user_notes": "Turnkey chalet with existing hot tub and panoramic views. Requires zero structural renovations.",
        "added_by": "Husband",
        "status": "Interested",
        "url": "https://www.redfin.com/NY/Kerhonkson/100-Mountain-View-Rd-12446/home/test950k"
    }
    db.save_property(prop_a)
    print("  [OK] $950k Tier A Scenario Passed & Saved to Database.")

    # -------------------------------------------------------------
    # SCENARIO 2: $450,000 Tier B Value-Add Canvas Property
    # -------------------------------------------------------------
    print("\n[TEST 2] Testing $450,000 Value-Add Canvas Scenario (Tier B)...")
    uw_tier_b = calculate_dscr_underwriting(
        price=450000.0,
        projected_adr=380.0,
        projected_occ_pct=58.0,
        interest_rate=7.5,
        opex_ratio=30.0,
        cash_reserves_pool=200000.0,
        broker_contact="Value Broker (845-555-4444)"
    )
    comp_b = lookup_town_compliance("12790")

    print(f"  - Tier Level: {uw_tier_b['tier_level']}")
    print(f"  - Down Payment: ${uw_tier_b['down_payment_amt']:,.2f} ({uw_tier_b['down_payment_pct']:.0f}%)")
    print(f"  - Closing Costs (3%): ${uw_tier_b['closing_costs']:,.2f}")
    print(f"  - Total Outlay: ${uw_tier_b['total_outlay']:,.2f}")
    print(f"  - Retained Capital Runway: ${uw_tier_b['retained_capital']:,.2f}")
    print(f"  - Renovation Target Progress: {uw_tier_b['progress_ratio']*100:.1f}% of ${uw_tier_b['renovation_target']:,.0f}")
    print(f"  - Monthly PITI: ${uw_tier_b['monthly_piti']:,.2f}")
    print(f"  - Monthly Gross STR Revenue: ${uw_tier_b['monthly_gross_revenue']:,.2f}")
    print(f"  - DSCR Ratio: {uw_tier_b['dscr_ratio']:.2f}x ({'PASS' if uw_tier_b['dscr_pass'] else 'FAIL'})")
    print(f"  - Tier Badge Text: {uw_tier_b['tier_badge']}")

    assert uw_tier_b['tier_level'] == "Tier B: Value-Add Canvas", "Failed: Tier B level mismatch"
    assert uw_tier_b['down_payment_amt'] == 90000.0, "Failed: Tier B down payment calculation incorrect"
    assert uw_tier_b['retained_capital'] == 96500.0, "Failed: Tier B retained capital calculation incorrect"

    prop_b = {
        "address": "45 Wurtsboro Hills Rd, Wurtsboro, NY 12790",
        "zip_code": "12790",
        "town": comp_b["town"],
        "price": 450000.0,
        "down_payment_pct": uw_tier_b["down_payment_pct"],
        "down_payment_amt": uw_tier_b["down_payment_amt"],
        "closing_costs": uw_tier_b["closing_costs"],
        "total_outlay": uw_tier_b["total_outlay"],
        "retained_capital": uw_tier_b["retained_capital"],
        "monthly_piti": uw_tier_b["monthly_piti"],
        "projected_adr": 380.0,
        "projected_occ": 58.0,
        "monthly_revenue": uw_tier_b["monthly_gross_revenue"],
        "dscr_ratio": uw_tier_b["dscr_ratio"],
        "tier_level": uw_tier_b["tier_level"],
        "tier_badge": uw_tier_b["tier_badge"],
        "lot_size_acres": 3.8,
        "str_risk": comp_b["str_risk"],
        "broker_contact": uw_tier_b["broker_contact"],
        "rating": 4,
        "user_notes": "Great value-add candidate. Retains $96.5k in capital to build a detached guest studio and inground pool.",
        "added_by": "Wife",
        "status": "Interested",
        "url": "https://www.redfin.com/NY/Wurtsboro/45-Wurtsboro-Hills-Rd-12790/home/test450k"
    }
    db.save_property(prop_b)
    print("  [OK] $450k Tier B Scenario Passed & Saved to Database.")

    # -------------------------------------------------------------
    # SCENARIO 3: NotebookLM Exporter Verification
    # -------------------------------------------------------------
    print("\n[TEST 3] Testing NotebookLM Exporter Markdown Generator...")
    props = db.get_all_properties()
    md_output = generate_notebooklm_markdown(props)
    print(f"  - Successfully generated Markdown output ({len(md_output)} characters).")
    assert "100 Mountain View Rd" in md_output, "Failed: Tier A property missing from NotebookLM Markdown"
    assert "45 Wurtsboro Hills Rd" in md_output, "Failed: Tier B property missing from NotebookLM Markdown"
    print("  [OK] NotebookLM Markdown Generation Passed.")

    print("\n" + "=" * 70)
    print("  ALL SYSTEM VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    run_system_verification()
