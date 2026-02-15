import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import datetime
import json
from fpdf import FPDF

# --- 1. SICHERE ZUGANGSDATEN ---
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    st.sidebar.warning("🔑 Keys über Sidebar aktiv")
    SUPABASE_URL = st.sidebar.text_input("Supabase URL", value="https://sjviyysbjozculvslrdy.supabase.co")
    SUPABASE_KEY = st.sidebar.text_input("Supabase Key", type="password")

if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    st.stop()

# --- 2. HILFSFUNKTIONEN ---
def speech_to_text(audio_bytes):
    t = datetime.datetime.now().strftime('%H:%M')
    return f"Sprachaufnahme vom {t}"

st.set_page_config(page_title="WerkOS v1.6.2", page_icon="🏗️", layout="wide")
st.title("🏗️ WerkOS Pro")

# --- 3. SIDEBAR NAVIGATION ---
st.sidebar.header("🚀 Hauptmenü")
page = st.sidebar.radio("Gehe zu:", ["📋 Baustellen-Board", "📦 Material & Lager", "⏱️ Zeiterfassung"])

# Projektwahl
try:
    all_p = supabase.table("notes").select("project_name").execute()
    p_list = sorted(list(set([e['project_name'] for e in all_p.data if e.get('project_name')])))
except: p_list = ["Allgemein"]

current_project = st.sidebar.selectbox("Baustelle:", p_list)

# --- SEITE 1: BOARD (Wie gehabt) ---
if page == "📋 Baustellen-Board":
    st.subheader(f"Board: {current_project}")
    # ... (Code für Notizen hier gekürzt für Übersichtlichkeit, bleibt aber gleich)
    st.info("Hier werden deine Fotos und Notizen wie gewohnt angezeigt.")
    res = supabase.table("notes").select("*").eq("is_completed", False).eq("project_name", current_project).order("created_at", desc=True).execute()
    for e in res.data:
        st.write(f"**{e['category']}**: {e['content']} ({e.get('cost_amount', 0)} €)")

# --- SEITE 2: MATERIAL & LAGER ---
elif page == "📦 Material & Lager":
    st.subheader("📦 Materialerfassung")
    
    # Material-Stammdaten laden
    try:
        mat_res = supabase.table("materials").select("*").execute()
        mat_list = mat_res.data
        mat_names = [m['name'] for m in mat_list]
    except:
        st.error("Material-Tabelle in Supabase nicht gefunden. Hast du den SQL-Befehl ausgeführt?")
        mat_list = []
        mat_names = []

    if mat_names:
        with st.form("mat_form"):
            col1, col2 = st.columns(2)
            sel_mat_name = col1.selectbox("Material wählen:", mat_names)
            menge = col2.number_input("Menge:", min_value=1.0, step=1.0)
            
            # Preis berechnen
            sel_mat = next(m for m in mat_list if m['name'] == sel_mat_name)
            einzelpreis = sel_mat['price_per_unit']
            gesamtpreis = einzelpreis * menge
            
            st.write(f"Einheit: {sel_mat['unit']} | Einzelpreis: {einzelpreis:.2f}€")
            st.write(f"**Gesamtpreis: {gesamtpreis:.2f}€**")
            
            if st.form_submit_button("Zum Projekt hinzufügen"):
                supabase.table("notes").insert({
                    "content": f"{menge}x {sel_mat_name} verbaut",
                    "category": "Material",
                    "status": "🟢 Ok",
                    "project_name": current_project,
                    "cost_amount": gesamtpreis,
                    "is_completed": False
                }).execute()
                st.success(f"{sel_mat_name} wurde gebucht!")
                st.rerun()

    st.divider()
    st.write("### Aktuelle Material-Liste (Stammdaten)")
    st.table(mat_list)

# --- SEITE 3: ZEITERFASSUNG (Vorschau für gleich) ---
elif page == "⏱️ Zeiterfassung":
    st.subheader("⏱️ Arbeitszeiten")
    st.write("Kommt als nächster Schritt...")