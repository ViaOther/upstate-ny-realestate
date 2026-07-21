import re
import math
import urllib.parse
import requests
from typing import Dict, Any, Tuple, Optional

# Baseline Default System Constants
DEFAULT_INTEREST_RATE = 7.5  # 7.5% default mortgage interest rate
DEFAULT_OPEX_RATIO = 30.0    # 30% default operating expense ratio
DEFAULT_CASH_RESERVES = 200000.0  # $200k max liquid capital pool
CLOSING_COST_PCT = 3.0        # 3% estimated closing costs

# Town STR Risk & Compliance Database
TOWN_REGULATIONS = {
    "12446": {
        "town": "Town of Rochester (Kerhonkson)",
        "county": "Ulster",
        "str_risk": "Medium Risk",
        "owner_occupancy_mandate": "No (Non-primary permitted)",
        "cap_status": "No Cap / No Waitlist",
        "local_manager_rule": "Mandatory within 30 miles of Town Hall",
        "guest_studio_rule": "Detached accessory studio (no kitchen) permitted under single STR permit",
        "adu_kitchen_rule": "Kitchen ADUs allowed for long-term residency, but PROHIBITED from STR",
        "min_lot_acres": 3.0,
        "pool_septic_setback": "20 ft isolation from septic tank & leach field",
        "height_limit": "35 ft (2.5 stories max)"
    },
    "12404": {
        "town": "Town of Rochester (Accord)",
        "county": "Ulster",
        "str_risk": "Medium Risk",
        "owner_occupancy_mandate": "No (Non-primary permitted)",
        "cap_status": "No Cap / No Waitlist",
        "local_manager_rule": "Mandatory within 30 miles of Town Hall",
        "guest_studio_rule": "Detached accessory studio (no kitchen) permitted under single STR permit",
        "adu_kitchen_rule": "Kitchen ADUs allowed for long-term residency, but PROHIBITED from STR",
        "min_lot_acres": 3.0,
        "pool_septic_setback": "20 ft isolation from septic tank & leach field",
        "height_limit": "35 ft (2.5 stories max)"
    },
    "12790": {
        "town": "Town of Mamakating (Wurtsboro)",
        "county": "Sullivan",
        "str_risk": "Medium Risk",
        "owner_occupancy_mandate": "No (Non-primary permitted)",
        "cap_status": "No Cap / Permit Required",
        "local_manager_rule": "Local contact required",
        "guest_studio_rule": "Permitted with standard building permit",
        "adu_kitchen_rule": "Subject to site plan review",
        "min_lot_acres": 2.0,
        "pool_septic_setback": "20 ft isolation from septic field",
        "height_limit": "35 ft max"
    },
    "12721": {
        "town": "Town of Mamakating (Bloomingburg)",
        "county": "Sullivan",
        "str_risk": "Medium Risk",
        "owner_occupancy_mandate": "No (Non-primary permitted)",
        "cap_status": "No Cap / Permit Required",
        "local_manager_rule": "Local contact required",
        "guest_studio_rule": "Permitted with standard building permit",
        "adu_kitchen_rule": "Subject to site plan review",
        "min_lot_acres": 2.0,
        "pool_septic_setback": "20 ft isolation from septic field",
        "height_limit": "35 ft max"
    },
    "12498": {
        "town": "Town of Woodstock",
        "county": "Ulster",
        "str_risk": "HIGH RISK (Capped)",
        "owner_occupancy_mandate": "Yes (Primary residence required for new permits)",
        "cap_status": "CAPPED at 285 permits / Long Waitlist",
        "local_manager_rule": "Strict local manager requirement",
        "guest_studio_rule": "Restricted",
        "adu_kitchen_rule": "Restricted",
        "min_lot_acres": 1.5,
        "pool_septic_setback": "20 ft isolation",
        "height_limit": "35 ft max"
    },
    "12764": {
        "town": "Town of Tusten (Narrowsburg)",
        "county": "Sullivan",
        "str_risk": "LOW RISK (Very Friendly)",
        "owner_occupancy_mandate": "No (Non-primary permitted)",
        "cap_status": "No Cap / No Waitlist",
        "local_manager_rule": "Standard contact requirement",
        "guest_studio_rule": "High flexibility",
        "adu_kitchen_rule": "High flexibility",
        "min_lot_acres": 2.0,
        "pool_septic_setback": "20 ft isolation",
        "height_limit": "35 ft max"
    }
}

def evaluate_tier_and_capital(price: float, down_payment_override: Optional[float] = None, cash_reserves_pool: float = DEFAULT_CASH_RESERVES) -> Dict[str, Any]:
    if price >= 750000:
        tier_level = "Tier A: Luxury Turnkey"
        down_payment_pct = 20.0
        tier_badge = "Tier A: Luxury Turnkey Rule. Action Required: Confirm property requires zero structural renovations, pool builds, or amenity installations."
        tier_color = "#1E88E5"
    elif price <= 600000 and price >= 350000:
        tier_level = "Tier B: Value-Add Canvas"
        down_payment_pct = down_payment_override if down_payment_override is not None else 20.0
        tier_badge = "Tier B: Value-Add Canvas. Action Required: Run full lot footprint and septic verification to support up to $200,000 in capital renovations."
        tier_color = "#2E7D32"
    else:
        tier_level = "Mid-Tier / Standard Acquisition"
        down_payment_pct = down_payment_override if down_payment_override is not None else 20.0
        tier_badge = "Standard Strategic Acquisition: Evaluate balance between turnkey condition and amenity additions."
        tier_color = "#FB8C00"

    down_payment_amt = price * (down_payment_pct / 100.0)
    closing_costs = price * (CLOSING_COST_PCT / 100.0)
    total_outlay = down_payment_amt + closing_costs
    retained_capital = max(0.0, cash_reserves_pool - total_outlay)

    renovation_target = 200000.0
    progress_ratio = min(1.0, max(0.0, retained_capital / renovation_target))

    return {
        "tier_level": tier_level,
        "tier_badge": tier_badge,
        "tier_color": tier_color,
        "down_payment_pct": down_payment_pct,
        "down_payment_amt": down_payment_amt,
        "closing_costs": closing_costs,
        "total_outlay": total_outlay,
        "retained_capital": retained_capital,
        "progress_ratio": progress_ratio,
        "renovation_target": renovation_target
    }

def calculate_dscr_underwriting(
    price: float,
    projected_adr: float,
    projected_occ_pct: float,
    interest_rate: float = DEFAULT_INTEREST_RATE,
    opex_ratio: float = DEFAULT_OPEX_RATIO,
    down_payment_pct_override: Optional[float] = None,
    cash_reserves_pool: float = DEFAULT_CASH_RESERVES,
    broker_contact: str = "Unknown Broker"
) -> Dict[str, Any]:
    tier_info = evaluate_tier_and_capital(price, down_payment_pct_override, cash_reserves_pool)

    down_pct = tier_info["down_payment_pct"]
    down_amt = tier_info["down_payment_amt"]
    loan_amount = price - down_amt

    r = (interest_rate / 100.0) / 12.0
    n = 360
    if r > 0 and loan_amount > 0:
        monthly_pi = loan_amount * (r * (1 + r)**n) / ((1 + r)**n - 1)
    else:
        monthly_pi = 0.0

    monthly_taxes = (price * 0.02) / 12.0
    monthly_insurance = (price * 0.006) / 12.0
    monthly_piti = monthly_pi + monthly_taxes + monthly_insurance

    days_in_month = 30.416
    monthly_gross_revenue = projected_adr * (projected_occ_pct / 100.0) * days_in_month
    annual_gross_revenue = monthly_gross_revenue * 12.0

    monthly_opex = monthly_gross_revenue * (opex_ratio / 100.0)
    monthly_noi = monthly_gross_revenue - monthly_opex

    dscr_ratio = monthly_gross_revenue / monthly_piti if monthly_piti > 0 else 0.0
    dscr_pass = dscr_ratio >= 1.20

    monthly_net_cash_flow = monthly_noi - monthly_piti
    annual_net_cash_flow = monthly_net_cash_flow * 12.0
    cash_on_cash_roi = (annual_net_cash_flow / tier_info["total_outlay"]) * 100.0 if tier_info["total_outlay"] > 0 else 0.0

    return {
        "price": price,
        "loan_amount": loan_amount,
        "interest_rate": interest_rate,
        "down_payment_pct": down_pct,
        "down_payment_amt": down_amt,
        "closing_costs": tier_info["closing_costs"],
        "total_outlay": tier_info["total_outlay"],
        "retained_capital": tier_info["retained_capital"],
        "progress_ratio": tier_info["progress_ratio"],
        "renovation_target": tier_info["renovation_target"],
        "tier_level": tier_info["tier_level"],
        "tier_badge": tier_info["tier_badge"],
        "tier_color": tier_info["tier_color"],
        "monthly_pi": monthly_pi,
        "monthly_taxes": monthly_taxes,
        "monthly_insurance": monthly_insurance,
        "monthly_piti": monthly_piti,
        "projected_adr": projected_adr,
        "projected_occ_pct": projected_occ_pct,
        "monthly_gross_revenue": monthly_gross_revenue,
        "annual_gross_revenue": annual_gross_revenue,
        "monthly_opex": monthly_opex,
        "monthly_noi": monthly_noi,
        "dscr_ratio": dscr_ratio,
        "dscr_pass": dscr_pass,
        "monthly_net_cash_flow": monthly_net_cash_flow,
        "annual_net_cash_flow": annual_net_cash_flow,
        "cash_on_cash_roi": cash_on_cash_roi,
        "broker_contact": broker_contact
    }

def lookup_town_compliance(zip_code: str) -> Dict[str, Any]:
    zip_clean = str(zip_code).strip()
    if zip_clean in TOWN_REGULATIONS:
        return TOWN_REGULATIONS[zip_clean]
    else:
        return {
            "town": f"Unmapped Town (ZIP {zip_clean})",
            "county": "Ulster/Sullivan",
            "str_risk": "Requires Verification",
            "owner_occupancy_mandate": "Check local town code",
            "cap_status": "Unknown",
            "local_manager_rule": "Verify local agent mandate",
            "guest_studio_rule": "Subject to standard building permit & zoning setbacks",
            "adu_kitchen_rule": "Verify ADU short-term rental laws",
            "min_lot_acres": 2.0,
            "pool_septic_setback": "20 ft isolation setback from septic tank/field",
            "height_limit": "35 ft max height"
        }

def parse_listing_input(user_input: str) -> Dict[str, Any]:
    result = {
        "address": "",
        "zip_code": "12446",
        "price": 550000.0,
        "beds": 3,
        "baths": 2.0,
        "lot_size_acres": 3.4,
        "broker_contact": "Listing Broker (Click-to-Call: 845-555-0199)",
        "raw_url": user_input if user_input.startswith("http") else ""
    }

    price_match = re.search(r'\$(\d{1,3}(?:,\d{3})+|\d+)', user_input)
    if price_match:
        try:
            result["price"] = float(price_match.group(1).replace(",", ""))
        except:
            pass

    zip_match = re.search(r'\b(1\d{4})\b', user_input)
    if zip_match:
        result["zip_code"] = zip_match.group(1)

    beds_match = re.search(r'(\d+)\s*(?:bed|bd|br)', user_input, re.IGNORECASE)
    if beds_match:
        result["beds"] = int(beds_match.group(1))

    baths_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:bath|ba)', user_input, re.IGNORECASE)
    if baths_match:
        result["baths"] = float(baths_match.group(1))

    acres_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:acre|ac)', user_input, re.IGNORECASE)
    if acres_match:
        result["lot_size_acres"] = float(acres_match.group(1))

    # Parse Address & Price from URL or OpenGraph metadata
    if "zillow.com" in user_input or "redfin.com" in user_input:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            resp = requests.get(user_input, headers=headers, timeout=3)
            if resp.status_code == 200:
                html = resp.text
                meta_price = re.search(r'\$(\d{1,3}(?:,\d{3})+|\d+)', html)
                if meta_price:
                    result["price"] = float(meta_price.group(1).replace(",", ""))
        except:
            pass

        parsed_url = urllib.parse.urlparse(user_input)
        path_parts = [p for p in parsed_url.path.split('/') if p and p != '']
        address_found = False

        for part in path_parts:
            if re.search(r'\d+', part) and not part.endswith('_zpid') and part != 'home':
                cleaned = part.replace("-", " ").strip()
                if len(cleaned) > 5:
                    result["address"] = cleaned.title()
                    address_found = True
                    break

        if not address_found and len(path_parts) > 1:
            for part in reversed(path_parts):
                if not part.endswith('_zpid') and part != 'home' and len(part) > 3:
                    result["address"] = part.replace("-", " ").title()
                    break

    if not result["address"] or result["address"].endswith("Zpid"):
        result["address"] = f"Property near ZIP {result['zip_code']}"

    return result
