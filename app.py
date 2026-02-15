import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import datetime
from fpdf import FPDF
import pandas as pd

# --- 1. ZUGANGSDATEN ---
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    SUPABASE_URL = st.sidebar.text_input("Supabase URL", value="https://sjviyysbjozculvslrdy.supabase.co")
    SUPABASE_KEY = st.sidebar.text_input("Supabase Key", type="password")

if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    st.stop()

# --- 2. VERBESSERTER PDF EXPORT (Punkt 3) ---
class WerkOS_PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'WerkOS - Professioneller Projektbericht', 0, 1, 'L')
        self.set_font('Arial', 'I', 8)
        self.cell(0, 5, f'Erstellt am: {datetime.datetime.now().strftime("%d.%m.%Y %H:%M")}', 0, 1, 'L')
        self.ln(10)

def create_pdf(data, project_name, total_cost):
    pdf = WerkOS_PDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"Projekt: {project_name}", ln=True)
    pdf.cell(0, 10, f"Gesamtkosten: {total_cost:.2f} EUR", ln=True)
    pdf.ln(5)
    
    for e in data:
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 8, f"{e.get('category')} - {e.get('created_at')[:10]}", ln=True, fill=True)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 7, f"{e.get('content')} | Kosten: {e.get('cost_amount', 0):.2f} EUR")
        pdf.ln(3)
    return bytes(pdf.output())

st.set_page_config(page_title="WerkOS Pro", layout="wide")

# --- 3. NAVIGATION ---
page = st.sidebar.radio("Navigation", ["📊 Dashboard", "📋 Board", "📦 Material & Lager", "⏱️ Zeiterfassung"])

# Projektwahl
p_res = supabase.table("notes").select("project_name").execute()
p_list = sorted(list(set([e['project_name'] for e in p_res.data if e.get('project_name')])))
current_project = st.sidebar.selectbox("Aktive Baustelle:", p_list if p_list else ["Allgemein"])

# --- SEITE 1: DASHBOARD (Punkt 1) ---
if page == "📊 Dashboard":
    st.title(f"Statistik: {current_project}")
    res = supabase.table("notes").select("*").eq("project_name", current_project).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        
        c1, c2, c3 = st.columns(3)
        total = df['cost_amount'].sum()
        c1.metric("Gesamtkosten", f"{total:.2f} €")
        c2.metric("Einträge", len(df))
        c3.metric("Offene Aufgaben", len(df[df['is_completed'] == False]))

        st.divider()
        st.subheader("Kostenverteilung (Material vs. Arbeit)")
        # Gruppierung nach Kategorie
        chart_data = df.groupby('category')['cost_amount'].sum()
        st.bar_chart(chart_data)
        


# --- SEITE 2: BOARD ---
elif page == "📋 Board":
    st.subheader(f"Baustellen-Board: {current_project}")
    # (Hier bleibt dein bisheriger Code für Kamera, Audio und Notizen gleich)
    st.info("Kamera und Notizen sind hier aktiv.")
    # ... [Hier den Board-Code von v1.6.8 einfügen] ...

# --- SEITE 3: MATERIAL & LAGER (Punkt 2) ---
elif page == "📦 Material & Lager":
    st.subheader("📦 Lager & Material")
    
    # Neues Material mit Anfangsbestand
    with st.expander("➕ Neues Material / Bestand hinzufügen"):
        with st.form("new_mat"):
            n = st.text_input("Name")
            p = st.number_input("Preis/Einh.", min_value=0.0)
            stock = st.number_input("Aktueller Lagerbestand", min_value=0.0)
            if st.form_submit_button("Speichern"):
                supabase.table("materials").insert({"name": n, "price_per_unit": p, "stock_quantity": stock}).execute()
                st.rerun()

    # Lagerübersicht
    st.write("### Aktueller Lagerbestand")
    m_res = supabase.table("materials").select("*").execute()
    if m_res.data:
        m_df = pd.DataFrame(m_res.data)[['name', 'stock_quantity', 'price_per_unit']]
        st.dataframe(m_df, use_container_width=True)

        st.divider()
        # Buchen mit Bestandsabzug
        with st.form("book_mat"):
            sel = st.selectbox("Material für Baustelle entnehmen:", m_df['name'].tolist())
            qty = st.number_input("Menge entnommen:", min_value=1.0)
            if st.form_submit_button("Buchen & Bestand reduzieren"):
                m_info = next(item for item in m_res.data if item['name'] == sel)
                # 1. In Projekt buchen
                supabase.table("notes").insert({"content": f"{qty}x {sel} verbaut", "category": "Material", "project_name": current_project, "cost_amount": m_info['price_per_unit']*qty, "is_completed": False}).execute()
                # 2. Lagerbestand aktualisieren
                new_stock = m_info['stock_quantity'] - qty
                supabase.table("materials").update({"stock_quantity": new_stock}).eq("id", m_info['id']).execute()
                st.success(f"Bestand von {sel} aktualisiert!")
                st.rerun()

# --- SEITE 4: ZEIT ---
elif page == "⏱️ Zeiterfassung":
    st.subheader("⏱️ Zeiterfassung")
    # ... [Hier den Zeit-Code von v1.6.8 einfügen] ...

# PDF Export in Sidebar
if st.sidebar.button("📄 Profi-Bericht (PDF)"):
    pdf_res = supabase.table("notes").select("*").eq("project_name", current_project).execute()
    total_val = sum([float(x['cost_amount']) for x in pdf_res.data if x.get('cost_amount')])
    pdf_b = create_pdf(pdf_res.data, current_project, total_val)
    st.sidebar.download_button("PDF Speichern", pdf_b, f"Bericht_{current_project}.pdf")