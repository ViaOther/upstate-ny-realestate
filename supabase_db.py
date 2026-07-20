import os
import sqlite3
import time
import pandas as pd
from typing import List, Dict, Any, Optional

# Try importing supabase-py
try:
    from supabase import create_client, Client
    HAS_SUPABASE_LIB = True
except ImportError:
    HAS_SUPABASE_LIB = False

DB_FILE = r"c:\Users\viaan\Desktop\New York Real Estate Project\properties.db"

class DatabaseManager:
    def __init__(self, supabase_url: str = "", supabase_key: str = ""):
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.client: Optional[Any] = None
        self.use_supabase = False

        if HAS_SUPABASE_LIB and supabase_url and supabase_key and "your-supabase" not in supabase_url:
            try:
                self.client = create_client(supabase_url, supabase_key)
                self.use_supabase = True
                print("[INFO] Connected to Supabase Cloud Database.")
            except Exception as e:
                print(f"[WARNING] Supabase connection failed: {e}. Falling back to SQLite.")
                self.use_supabase = False
        else:
            print("[INFO] Using local SQLite database (properties.db).")

        self.init_db()

    def _get_sqlite_conn(self):
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Creates table in SQLite if it does not exist."""
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS properties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT UNIQUE,
                zip_code TEXT,
                town TEXT,
                price REAL,
                down_payment_pct REAL,
                down_payment_amt REAL,
                closing_costs REAL,
                total_outlay REAL,
                retained_capital REAL,
                monthly_piti REAL,
                projected_adr REAL,
                projected_occ REAL,
                monthly_revenue REAL,
                dscr_ratio REAL,
                tier_level TEXT,
                tier_badge TEXT,
                lot_size_acres REAL,
                str_risk TEXT,
                broker_contact TEXT,
                rating INTEGER,
                user_notes TEXT,
                added_by TEXT,
                status TEXT,
                url TEXT,
                created_at TEXT
            )
        """)
        conn.commit()
        conn.close()

    def save_property(self, data: Dict[str, Any]) -> bool:
        """Saves a property record to Supabase or SQLite."""
        data["created_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

        if self.use_supabase and self.client:
            try:
                # Upsert into Supabase table 'properties'
                response = self.client.table("properties").upsert(data, on_conflict="address").execute()
                return True
            except Exception as e:
                print(f"[WARNING] Supabase save failed: {e}. Saving to SQLite fallback...")

        # SQLite fallback
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO properties (
                    address, zip_code, town, price, down_payment_pct, down_payment_amt,
                    closing_costs, total_outlay, retained_capital, monthly_piti,
                    projected_adr, projected_occ, monthly_revenue, dscr_ratio,
                    tier_level, tier_badge, lot_size_acres, str_risk, broker_contact,
                    rating, user_notes, added_by, status, url, created_at
                ) VALUES (
                    :address, :zip_code, :town, :price, :down_payment_pct, :down_payment_amt,
                    :closing_costs, :total_outlay, :retained_capital, :monthly_piti,
                    :projected_adr, :projected_occ, :monthly_revenue, :dscr_ratio,
                    :tier_level, :tier_badge, :lot_size_acres, :str_risk, :broker_contact,
                    :rating, :user_notes, :added_by, :status, :url, :created_at
                ) ON CONFLICT(address) DO UPDATE SET
                    price=excluded.price,
                    down_payment_pct=excluded.down_payment_pct,
                    down_payment_amt=excluded.down_payment_amt,
                    closing_costs=excluded.closing_costs,
                    total_outlay=excluded.total_outlay,
                    retained_capital=excluded.retained_capital,
                    monthly_piti=excluded.monthly_piti,
                    projected_adr=excluded.projected_adr,
                    projected_occ=excluded.projected_occ,
                    monthly_revenue=excluded.monthly_revenue,
                    dscr_ratio=excluded.dscr_ratio,
                    tier_level=excluded.tier_level,
                    tier_badge=excluded.tier_badge,
                    lot_size_acres=excluded.lot_size_acres,
                    str_risk=excluded.str_risk,
                    broker_contact=excluded.broker_contact,
                    rating=excluded.rating,
                    user_notes=excluded.user_notes,
                    added_by=excluded.added_by,
                    status=excluded.status,
                    url=excluded.url,
                    created_at=excluded.created_at
            """, data)
            conn.commit()
            return True
        except Exception as e:
            print(f"[ERROR] SQLite save failed: {e}")
            return False
        finally:
            conn.close()

    def get_all_properties(self) -> List[Dict[str, Any]]:
        """Retrieves all archived properties."""
        if self.use_supabase and self.client:
            try:
                res = self.client.table("properties").select("*").order("created_at", desc=True).execute()
                if res.data:
                    return res.data
            except Exception as e:
                print(f"[WARNING] Supabase fetch failed: {e}. Reading from SQLite...")

        # SQLite fallback
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM properties ORDER BY created_at DESC")
        rows = cursor.fetchall()
        result = [dict(r) for r in rows]
        conn.close()
        return result

    def delete_property(self, address: str) -> bool:
        """Deletes a property by address."""
        if self.use_supabase and self.client:
            try:
                self.client.table("properties").delete().eq("address", address).execute()
            except Exception as e:
                print(f"[WARNING] Supabase delete failed: {e}")

        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM properties WHERE address = ?", (address,))
        conn.commit()
        conn.close()
        return True

def generate_notebooklm_markdown(properties: List[Dict[str, Any]]) -> str:
    """Formats archived properties into NotebookLM-compliant Markdown."""
    md = "## MLS Daily Listings & Underwriting Vault\n"
    md += "### Filtered DSCR & Zoning Evaluated Properties\n\n"

    if not properties:
        md += "No properties currently archived in the vault.\n"
        return md

    for p in properties:
        md += f"## {p.get('address', 'Unknown Address')}\n"
        md += "### DSCR Financial & Tier Evaluation\n\n"
        md += "| Metric | Underwritten Value |\n"
        md += "| :--- | :--- |\n"
        md += f"| **Purchase Price** | ${p.get('price', 0):,.2f} |\n"
        md += f"| **Tier Category** | {p.get('tier_level', 'N/A')} |\n"
        md += f"| **Down Payment ({p.get('down_payment_pct', 20):.0f}%)** | ${p.get('down_payment_amt', 0):,.2f} |\n"
        md += f"| **Estimated Closing Costs (3%)** | ${p.get('closing_costs', 0):,.2f} |\n"
        md += f"| **Total Outlay (Cash Required)** | ${p.get('total_outlay', 0):,.2f} |\n"
        md += f"| **Retained Renovation Runway** | ${p.get('retained_capital', 0):,.2f} |\n"
        md += f"| **Monthly PITI Debt Service** | ${p.get('monthly_piti', 0):,.2f} |\n"
        md += f"| **Projected Monthly STR Revenue** | ${p.get('monthly_revenue', 0):,.2f} (ADR: ${p.get('projected_adr', 0):.0f} @ {p.get('projected_occ', 0):.0f}% Occ) |\n"
        md += f"| **DSCR Ratio** | **{p.get('dscr_ratio', 0):.2f}x** ({'PASS' if p.get('dscr_ratio', 0) >= 1.2 else 'FAIL'}) |\n"
        md += f"| **Lot Size** | {p.get('lot_size_acres', 0):.2f} Acres |\n"
        md += f"| **Town & STR Risk** | {p.get('town', 'N/A')} ({p.get('str_risk', 'N/A')}) |\n"
        md += f"| **Broker Contact** | {p.get('broker_contact', 'N/A')} |\n"
        md += f"| **Rating / Status** | {'★' * int(p.get('rating', 3))} ({p.get('status', 'Interested')}) |\n"
        md += f"| **Listing URL** | [{p.get('url', '')}]({p.get('url', '')}) |\n\n"

        md += "### Investment & Renovation Notes\n"
        md += f"**Tier Badge:** {p.get('tier_badge', '')}\n\n"
        md += f"{p.get('user_notes', 'No notes added.')}\n\n"
        md += "---\n\n"

    md += "## Sources & Statutory Citations\n"
    md += "*   **Underwriting Engine:** 7.5% Default Mortgage Interest Rate, 30% Default Opex Ratio, 20%-25% Tiered Down Payment.\n"
    md += "*   **Zoning Framework:** Town of Rochester Chapter 140 (Local Law 3 of 2021) & Ulster County Sanitary Code.\n"
    md += f"*   **Export Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n"

    return md
