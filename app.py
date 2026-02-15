import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import datetime
from fpdf import FPDF
import pandas as pd
import os

# --- 1. APP CONFIG ---
st.set_page_config(page_title="WerkOS Pro", page_icon="🏗️", layout="wide", initial_sidebar_state="collapsed")

# --- 2. PROFESSINAL APP STYLING (CSS) ---
st.markdown("""
    <style>
    /* Hintergrund und Schrift */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #F8F9FB; }
    
    /* Header ausblenden für App-Look */
    header {visibility: hidden;}
    .main .block-container {padding-top: 2rem; padding-bottom: 2rem;}

    # 

    /* Card-Design für Einträge */
    .stMetric, .stExpander, div[data-testid="stForm"] {
        background: white;
        border-radius: 15px !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important;
        padding: 20px !important;
    }
    
    /* Buttons professionell */
    .stButton>button {
        width: 100%;
        border-radius: 12px !important;
        background-color: #1E3A8A !important; /* Dunkelblau */
        color: white !important;
        font-weight: 600 !important;
        height: 3.5rem !important;
        border: none !important;
        transition: 0.3s;
    }
    .stButton>button:hover { background-color: #2563EB !important; transform: translateY(-2px); }

    /* Eingabefelder */
    .stTextInput>div>div>input, .stSelectbox>div>div>div {
        border-radius: 10px !important;
        background-color: #F1F5F9 !important;
        border: 1px solid #E2E8F0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ZUGANG ---
try:
    S_URL, S_KEY = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
except:
    S_URL = st.sidebar.text_input("URL", value="https://sjviyysbjozculvslrdy.supabase.co")
    S_KEY = st.sidebar.text_input("Key", type="password")

if S_URL and S_KEY:
    supabase = create_client(S_URL, S_KEY)
else:
    st.stop()

# --- 4. FUNKTIONEN ---
def create_pdf(data, p_name, total):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"Projektbericht: {p_name}", ln=True)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Gesamtkosten: {total:.2f} EUR", ln=True)
    pdf.ln(10)
    for e in data:
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, f"{e.get('category')} - {e.get('created_at','')[:10]}", ln=True)
        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(0, 7, f"{e.get('content')} | {e.get('cost_amount',0)} EUR")
        pdf.ln(4)
    return bytes(pdf.output())

# --- 5. NAVIGATION ---
st.sidebar.markdown("### 🏗️ WerkOS Navigation")
page = st.sidebar.radio("Gehe zu:", ["📊 Dashboard", "📋 Board", "📦 Lager", "⏱️ Zeiten"])

p_res = supabase.table("notes").select("project_name").execute()
p_list = sorted(list(set([e['project_name'] for e in p_res.data if e.get('project_name')])))
curr_p = st.sidebar.selectbox("Projekt wählen:", p_list if p_list else ["Allgemein"])

# --- SEITE 1: DASHBOARD ---
if page == "📊 Dashboard":
    st.markdown(f"## 📊 {curr_p}")
    m_check = supabase.table("materials").select("*").execute()
    if m_check.data:
        low = [m for m in m_check.data if float(m.get('stock_quantity',0)) <= float(m.get('min_stock',5))]
        if low: st.error(f"⚠️ Achtung: {len(low)} Artikel im Lager fast leer!")
    
    res = supabase.table("notes").select("*").eq("project_name", curr_p).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        col1, col2 = st.columns(2)
        col1.metric("Projektkosten", f"{df['cost_amount'].sum():.2f} €")
        col2.metric("Einträge", len(df))
        st.divider()
        st.subheader("Kostenanalyse")
        st.bar_chart(df.groupby('category')['cost_amount'].sum())

# --- SEITE 2: BOARD ---
elif page == "📋 Board":
    st.markdown(f"## 📋 Board: {curr_p}")
    
    # Eingabe-Bereich als Card
    with st.container():
        with st.form("main_input", clear_on_submit=True):
            t = st.text_input("Was ist zu tun / passiert?")
            c1, c2 = st.columns(2)
            kat = c1.selectbox("Kategorie", ["Notiz", "Aufgabe", "Material", "Wichtig"])
            cost = c2.number_input("Kosten in €", min_value=0.0)
            if st.form_submit_button("Eintrag Speichern") and t:
                supabase.table("notes").insert({"content":t, "category":kat, "project_name":curr_p, "cost_amount":cost, "is_completed":False}).execute()
                st.rerun()

    # Media-Bereich
    col_a, col_b = st.columns(2)
    with col_a:
        img = st.camera_input("Foto aufnehmen")
        if img:
            fn = f"{datetime.datetime.now().strftime('%H%M%S')}.jpg"
            supabase.storage.from_("werkos_fotos").upload(fn, img.getvalue())
            url = supabase.storage.from_("werkos_fotos").get_public_url(fn)
            supabase.table("notes").insert({"content":"Foto-Notiz", "category":"Notiz", "project_name":curr_p, "image_url":url, "is_completed":False}).execute()
            st.rerun()
    with col_b:
        st.write("🎤 Sprachnotiz")
        aud = audio_recorder(text="", icon_size="2x")
        if aud:
            supabase.table("notes").insert({"content":f"Sprachaufnahme {datetime.datetime.now().strftime('%H:%M')}", "category":"Notiz", "project_name":curr_p, "is_completed":False}).execute()
            st.rerun()

    st.divider()
    # Board-Elemente als saubere Karten
    res = supabase.table("notes").select("*").eq("is_completed", False).eq("project_name", curr_p).order("created_at", desc=True).execute()
    for e in res.data:
        with st.container():
            st.markdown(f"""
                <div style="background:white; border-radius:15px; padding:15px; margin-bottom:10px; border-left: 5px solid #1E3A8A;">
                    <small style="color:gray;">{e['category']} | {e.get('cost_amount', 0)}€</small><br>
                    <strong>{e['content']}</strong>
                </div>
            """, unsafe_allow_html=True)
            if e.get("image_url"): st.image(e["image_url"], use_container_width=True)
            if st.button("Erledigt ✅", key=e['id']):
                supabase.table("notes").update({"is_completed":True}).eq("id", e['id']).execute()
                st.rerun()

# --- SEITE 3: LAGER ---
elif page == "📦 Lager":
    st.markdown("## 📦 Lagerverwaltung")
    with st.expander("➕ Neues Material anlegen"):
        with st.form("lager_add"):
            n = st.text_input("Name")
            p = st.number_input("Preis pro Stück/Einheit")
            s = st.number_input("Aktueller Bestand")
            if st.form_submit_button("Speichern"):
                supabase.table("materials").insert({"name":n, "price_per_unit":p, "stock_quantity":s, "min_stock":5}).execute()
                st.rerun()
    
    m_res = supabase.table("materials").select("*").execute()
    if m_res.data:
        df_m = pd.DataFrame(m_res.data)
        st.table(df_m[['name', 'stock_quantity']])
        
        with st.form("lager_use"):
            sel = st.selectbox("Für Baustelle entnehmen:", df_m['name'].tolist())
            q = st.number_input("Menge", min_value=1.0)
            if st.form_submit_button("Bestand abbuchen"):
                info = next(i for i in m_res.data if i['name'] == sel)
                supabase.table("notes").insert({"content":f"{q}x {sel}", "category":"Material", "project_name":curr_p, "cost_amount":info['price_per_unit']*q, "is_completed":False}).execute()
                supabase.table("materials").update({"stock_quantity": float(info['stock_quantity'])-q}).eq("id", info['id']).execute()
                st.rerun()

# --- SEITE 4: ZEIT ---
elif page == "⏱️ Zeiten":
    st.markdown("## ⏱️ Zeiterfassung")
    # Hier der gewohnte Zeit-Code, jetzt im Card-Design
    s_res = supabase.table("staff").select("*").execute()
    if s_res.data:
        with st.form("time_add"):
            sel_s = st.selectbox("Mitarbeiter", [i['name'] for i in s_res.data])
            h = st.number_input("Stunden", min_value=0.5, step=0.5)
            if st.form_submit_button("Stunden buchen"):
                s = next(i for i in s_res.data if i['name'] == sel_s)
                supabase.table("notes").insert({"content":f"{sel_s}: {h}h", "category":"Aufgabe", "project_name":curr_p, "cost_amount":s['hourly_rate']*h, "is_completed":False}).execute()
                st.rerun()

# PDF Button in Sidebar
if st.sidebar.button("📄 Bericht (PDF)"):
    r = supabase.table("notes").select("*").eq("project_name", curr_p).execute()
    pdf_b = create_pdf(r.data, curr_p, sum([float(x['cost_amount']) for x in r.data]))
    st.sidebar.download_button("Download PDF", pdf_b, f"Report_{curr_p}.pdf")
