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
        pdf.cell(0, 8, f"{e.get('category')} - {e.get('created_at', '')[:10]}", ln=True, fill=True)
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 7, f"{e.get('content')} | Kosten: {e.get('cost_amount', 0):.2f} EUR")
        pdf.ln(3)
    return bytes(pdf.output())

st.set_page_config(page_title="WerkOS Pro", page_icon="🏗️", layout="wide")

# --- 3. SIDEBAR & PROJEKTWAHL ---
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
    
    # NEU: Lagerwarnung im Dashboard
    m_check = supabase.table("materials").select("*").execute()
    if m_check.data:
        low_stock_items = [m for m in m_check.data if m.get('stock_quantity', 0) <= m.get('min_stock', 5)]
        if low_stock_items:
            st.warning(f"⚠️ **Lager-Warnung:** {len(low_stock_items)} Materialien sind fast leer!")
            with st.expander("Details anzeigen"):
                for l in low_stock_items:
                    st.write(f"- {l['name']}: Nur noch {l['stock_quantity']} im Lager (Limit: {l['min_stock']})")

    res = supabase.table("notes").select("*").eq("project_name", current_project).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        c1, c2, c3 = st.columns(3)
        total = df['cost_amount'].sum()
        c1.metric("Gesamtkosten", f"{total:.2f} €")
        c2.metric("Einträge", len(df))
        c3.metric("Offene Aufgaben", len(df[df['is_completed'] == False]))
        st.divider()
        st.subheader("Kostenverteilung")
        chart_data = df.groupby('category')['cost_amount'].sum()
        st.bar_chart(chart_data)
    else:
        st.info("Noch keine Daten für dieses Projekt vorhanden.")

# --- SEITE 2: BOARD ---
elif page == "📋 Board":
    st.subheader(f"Board: {current_project}")
    tab1, tab2 = st.tabs(["📋 Notizen & Media", "📅 Verlauf"])
    with tab1:
        col_in, col_med = st.columns([2, 1])
        with col_in:
            with st.form("entry_form", clear_on_submit=True):
                txt = st.text_input("Titel / Aufgabe")
                c1, c2, c3 = st.columns(3)
                kat = c1.selectbox("Kat:", ["Notiz", "Aufgabe", "Material", "Wichtig"])
                prio = c2.selectbox("Status:", ["🟢 Ok", "🟡 In Arbeit", "🔴 Dringend"], index=1)
                cost = c3.number_input("Kosten €:", min_value=0.0)
                if st.form_submit_button("Speichern") and txt:
                    supabase.table("notes").insert({"content": txt, "category": kat, "status": prio, "project_name": current_project, "cost_amount": cost, "is_completed": False}).execute()
                    st.rerun()
        with col_med:
            st.write("📸 Foto / 🎤 Audio")
            img = st.camera_input("Foto", key="cam")
            if img:
                if st.session_state.get("last_img") != img.size:
                    fn = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    supabase.storage.from_("werkos_fotos").upload(fn, img.getvalue())
                    url = supabase.storage.from_("werkos_fotos").get_public_url(fn)
                    supabase.table("notes").insert({"content": "Foto-Notiz", "category": "Notiz", "status": "🟡 In Arbeit", "project_name": current_project, "image_url": url, "is_completed": False}).execute()
                    st.session_state["last_img"] = img.size
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
        for item in cal_res.data:
            st.write(f"✅ **{item['created_at'][:10]}** | {item['category']}: {item['content']}")

# --- SEITE 3: MATERIAL & LAGER ---
elif page == "📦 Material & Lager":
    st.subheader("📦 Lagerverwaltung")
    with st.expander("➕ Neues Material / Bestand hinzufügen"):
        with st.form("new_mat"):
            n = st.text_input("Name")
            p = st.number_input("Preis pro Einheit (€)", min_value=0.0)
            stock = st.number_input("Lagerbestand (Anfang)", min_value=0.0)
            m_limit = st.number_input("Warnen bei Bestand unter...", min_value=0.0, value=5.0)
            if st.form_submit_button("Im Katalog speichern"):
                supabase.table("materials").insert({"name": n, "price_per_unit": p, "stock_quantity": stock, "min_stock": m_limit}).execute()
                st.rerun()
    st.divider()
    m_res = supabase.table("materials").select("*").execute()
    if m_res.data:
        # Bestandsliste mit Warn-Emojis
        m_df = pd.DataFrame(m_res.data)
        m_df['Status'] = m_df.apply(lambda x: "⚠️ KNAPP" if x['stock_quantity'] <= x['min_stock'] else "✅ OK", axis=1)
        st.write("### Aktueller Bestand")
        st.table(m_df[['name', 'stock_quantity', 'min_stock', 'Status', 'price_per_unit']])
        
        with st.form("book_mat"):
            sel = st.selectbox("Material entnehmen:", m_df['name'].tolist())
            qty = st.number_input("Menge:", min_value=1.0)
            if st.form_submit_button("Buchen & Bestand abziehen"):
                m_info = next(item for item in m_res.data if item['name'] == sel)
                supabase.table("notes").insert({"content": f"{qty}x {sel}", "category": "Material", "project_name": current_project, "cost_amount": m_info['price_per_unit']*qty, "is_completed": False}).execute()
                new_q = m_info['stock_quantity'] - qty
                supabase.table("materials").update({"stock
