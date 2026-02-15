import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import datetime
from fpdf import FPDF
import pandas as pd

# --- 1. SICHERE ZUGANGSDATEN ---
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    st.sidebar.warning("🔑 Keys über Sidebar aktiv")
    SUPABASE_URL = st.sidebar.text_input("Supabase URL", value="https://sjviyysbjozculvslrdy.supabase.co")
    SUPABASE_KEY = st.sidebar.text_input("Supabase Key", type="password")

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except:
        st.error("Verbindung zu Supabase fehlgeschlagen.")
        st.stop()
else:
    st.stop()

# --- 2. HILFSFUNKTIONEN ---
def speech_to_text(audio_bytes):
    t = datetime.datetime.now().strftime('%H:%M')
    return f"Sprachaufnahme vom {t}"

class WerkOS_PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'WerkOS - Professioneller Projektbericht', 0, 1, 'L')
        self.ln(10)

def create_pdf(data, project_name, total_cost):
    pdf = WerkOS_PDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"Projekt: {project_name} | Gesamt: {total_cost:.2f} EUR", ln=True)
    pdf.ln(5)
    for e in data:
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 8, f"{e.get('category')} - {e.get('created_at', '')[:10]}", ln=True, fill=True)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 7, f"{e.get('content')} | {e.get('cost_amount', 0):.2f} EUR")
        pdf.ln(3)
    return bytes(pdf.output())

st.set_page_config(page_title="WerkOS Pro", page_icon="🏗️", layout="wide")

# --- 3. NAVIGATION ---
st.sidebar.header("🚀 Hauptmenü")
page = st.sidebar.radio("Navigation", ["📊 Dashboard", "📋 Board", "📦 Material & Lager", "⏱️ Zeit"])

try:
    p_res = supabase.table("notes").select("project_name").execute()
    p_list = sorted(list(set([e['project_name'] for e in p_res.data if e.get('project_name')])))
except: p_list = ["Allgemein"]
current_project = st.sidebar.selectbox("Baustelle:", p_list if p_list else ["Allgemein"])
new_p = st.sidebar.text_input("✨ Neue Baustelle:")
if new_p: current_project = new_p

# --- SEITE 1: DASHBOARD ---
if page == "📊 Dashboard":
    st.title(f"📊 Dashboard: {current_project}")
    m_check = supabase.table("materials").select("*").execute()
    if m_check.data:
        low_stock = [m for m in m_check.data if float(m.get('stock_quantity', 0)) <= float(m.get('min_stock', 5))]
        if low_stock:
            st.warning(f"⚠️ **Bestands-Warnung:** {len(low_stock)} Artikel fast leer!")
            with st.expander("Details"):
                for l in low_stock: st.write(f"- {l['name']}: Nur noch {l['stock_quantity']} vorhanden.")

    res = supabase.table("notes").select("*").eq("project_name", current_project).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        c1, c2, c3 = st.columns(3)
        c1.metric("Kosten", f"{df['cost_amount'].sum():.2f} €")
        c2.metric("Einträge", len(df))
        c3.metric("Offen", len(df[df['is_completed'] == False]))
        st.divider()
        st.bar_chart(df.groupby('category')['cost_amount'].sum())
    else: st.info("Keine Daten.")

# --- SEITE 2: BOARD ---
elif page == "📋 Board":
    st.subheader(f"Board: {current_project}")
    tab1, tab2 = st.tabs(["📋 Notizen & Media", "📅 Verlauf"])
    with tab1:
        col_in, col_med = st.columns([2, 1])
        with col_in:
            with st.form("entry_form", clear_on_submit=True):
                txt = st.text_input("Titel")
                c1, c2, c3 = st.columns(3)
                kat = c1.selectbox("Kat:", ["Notiz", "Aufgabe", "Material", "Wichtig"])
                prio = c2.selectbox("Status:", ["🟢 Ok", "🟡 In Arbeit", "🔴 Dringend"], index=1)
                cost = c3.number_input("Kosten €:", min_value=0.0)
                if st.form_submit_button("Speichern") and txt:
                    supabase.table("notes").insert({"content": txt, "category": kat, "status": prio, "project_name": current_project, "cost_amount": cost, "is_completed": False}).execute()
                    st.rerun()
        with col_med:
            img = st.camera_input("Foto", key="cam")
            if img:
                fn = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                supabase.storage.from_("werkos_fotos").upload(fn, img.getvalue())
                url = supabase.storage.from_("werkos_fotos").get_public_url(fn)
                supabase.table("notes").insert({"content": "Foto-Notiz", "category": "Notiz", "status": "🟡 In Arbeit", "project_name": current_project, "image_url": url, "is_completed": False}).execute()
                st.rerun()
            aud = audio_recorder(text="", icon_size="2x", key="aud")
            if aud:
                supabase.table("notes").insert({"content": speech_to_text(aud), "category": "Notiz", "status": "🟡 In Arbeit", "project_name": current_project, "is_completed": False}).execute()
                st.rerun()
        st.divider()
        res = supabase.table("notes").select("*").eq("is_completed", False).eq("project_name", current_project).order("created_at", desc=True).execute()
        for e in res.data:
            with st.container():
                st.markdown(f"**{e['status']} | {e['category']} ({e.get('cost_amount', 0)} €)**")
                st.write(e['content'])
                if e.get("image_url"): st.image(e["image_url"], use_container_width=True)
                if st.button("Erledigt ✅", key=f"d_{e['id']}"):
                    supabase.table("notes").update({"is_completed": True}).eq("id", e['id']).execute()
                    st.rerun()
                st.divider()
    with tab2:
        cal_res = supabase.table("notes").select("*").eq("project_name", current_project).eq("is_completed", True).order("created_at", desc=True).execute()
        for item in cal_res.data: st.write(f"✅ **{item['created_at'][:10]}** | {item['content']}")

# --- SEITE 3: MATERIAL & LAGER ---
elif page == "📦 Material & Lager":
    st.subheader("📦 Lagerverwaltung")
    with st.expander("➕ Neues Material anlegen"):
        with st.form("new_mat"):
            n = st.text_input("Name")
            p = st.number_input("Preis/Einh.", min_value=0.0)
            stock = st.number_input("Bestand", min_value=0.0)
            lim = st.number_input("Warnlimit", min_value=0.0, value=5.0)
            if st.form_submit_button("Speichern"):
                supabase.table("materials").insert({"name": n, "price_per_unit": p, "stock_quantity": stock, "min_stock": lim}).execute()
                st.rerun()
    st.divider()
    m_res = supabase.table("materials").select("*").execute()
    if m_res.data:
        m_df = pd.DataFrame(m_res.data)
        m_df['Status'] = m_df.apply(lambda x: "⚠️ KNAPP" if float(x['stock
