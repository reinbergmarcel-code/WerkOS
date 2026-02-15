import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import datetime
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
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except:
        st.error("Verbindung zu Supabase fehlgeschlagen.")
        st.stop()
else:
    st.info("Bitte Zugangsdaten eingeben.")
    st.stop()

# --- 2. HILFSFUNKTIONEN ---
def speech_to_text(audio_bytes):
    t = datetime.datetime.now().strftime('%H:%M')
    return f"Sprachaufnahme vom {t}"

def create_pdf(data, project_name, total_cost):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, f"Projektbericht: {project_name}", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(190, 10, f"Gesamtkosten: {total_cost:.2f} EUR", ln=True, align="C")
    pdf.ln(10)
    for entry in data:
        pdf.set_font("Arial", "B", 11)
        h = f"{entry.get('category')} | {entry.get('status')} ({entry.get('created_at', '')[:10]})"
        pdf.cell(190, 8, h.encode('latin-1', 'replace').decode('latin-1'), ln=True)
        pdf.set_font("Arial", "", 11)
        c = f"{entry.get('content')} - Kosten: {entry.get('cost_amount', 0)} EUR"
        pdf.multi_cell(190, 7, c.encode('latin-1', 'replace').decode('latin-1'))
        pdf.ln(5)
    return bytes(pdf.output())

st.set_page_config(page_title="WerkOS Pro", page_icon="🏗️", layout="wide")
st.title("🏗️ WerkOS Pro")

# --- 3. SIDEBAR NAVIGATION ---
st.sidebar.header("🚀 Hauptmenü")
page = st.sidebar.radio("Gehe zu:", ["📋 Board", "📦 Material", "⏱️ Zeit"])

# Projektwahl
try:
    p_res = supabase.table("notes").select("project_name").execute()
    p_list = sorted(list(set([e['project_name'] for e in p_res.data if e.get('project_name')])))
except: p_list = ["Allgemein"]
if not p_list: p_list = ["Allgemein"]

current_project = st.sidebar.selectbox("Baustelle:", p_list)
new_p = st.sidebar.text_input("✨ Neue Baustelle:")
if new_p: current_project = new_p

# Kosten-Metrik
res_costs = supabase.table("notes").select("cost_amount").eq("project_name", current_project).execute()
total_budget = sum([float(e['cost_amount']) for e in res_costs.data if e.get('cost_amount')])
st.sidebar.metric("Projekt-Ausgaben", f"{total_budget:.2f} €")

# --- SEITE 1: BOARD ---
if page == "📋 Board":
    st.subheader(f"Dashboard: {current_project}")
    tab1, tab2 = st.tabs(["📋 Notizen & Media", "📅 Verlauf"])
    with tab1:
        c_in, c_med = st.columns([2, 1])
        with c_in:
            with st.form("entry_form", clear_on_submit=True):
                txt = st.text_input("Was gibt's Neues?")
                c1, c2, c3 = st.columns(3)
                kat = c1.selectbox("Kat:", ["Notiz", "Aufgabe", "Material", "Wichtig"])
                prio = c2.selectbox("Status:", ["🟢 Ok", "🟡 In Arbeit", "🔴 Dringend"], index=1)
                cost = c3.number_input("Kosten €:", min_value=0.0)
                if st.form_submit_button("Speichern") and txt:
                    supabase.table("notes").insert({"content": txt, "category": kat, "status": prio, "project_name": current_project, "cost_amount": cost, "is_completed": False}).execute()
                    st.rerun()
        with c_med:
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

# --- SEITE 2: MATERIAL ---
elif page == "📦 Material":
    st.subheader("📦 Materialverwaltung")
    with st.expander("➕ Neues Material anlegen"):
        with st.form("new_mat"):
            n = st.text_input("Materialname")
            u = st.selectbox("Einheit", ["Stück", "Sack", "Meter", "m²", "m³"])
            p = st.number_input("Preis pro Einheit (€)", min_value=0.0)
            if st.form_submit_button("Speichern"):
                supabase.table("materials").insert({"name": n, "unit": u, "price_per_unit": p}).execute()
                st.success("Gespeichert!")
                st.rerun()
    st.divider()
    try:
        mat_res = supabase.table("materials").select("*").execute()
        if mat_res.data:
            mat_dict = {m['name']: m for m in mat_res.data}
            with st.form("book_mat"):
                sel = st.selectbox("Material wählen:", list(mat_dict.keys()))
                qty = st.number_input("Menge:", min_value=1.0)
                if st.form_submit_button("Auf Baustelle buchen"):
                    m = mat_dict[sel]
                    supabase.table("notes").insert({"content": f"{qty} {m['unit']} {sel}", "category": "Material", "status": "🟢 Ok", "project_name": current_project, "cost_amount": m['price_per_unit']*qty, "is_completed": False}).execute()
                    st.success("Gebucht!")
                    st.rerun()
        else: st.info("Noch kein Material im Katalog.")
    except: st.error("Tabelle 'materials' fehlt.")

# --- SEITE 3: ZEIT ---
elif page == "⏱️ Zeit":
    st.subheader("⏱️ Zeiterfassung")
    with st.expander("👤 Mitarbeiter anlegen", expanded=True):
        with st.form("new_staff"):
            sn = st.text_input("Name des Mitarbeiters")
            sr = st.number_input("Stundensatz (€)", min_value=0.0, value=45.0)
            if st.form_submit_button("Mitarbeiter Speichern"):
                if sn:
                    supabase.table("staff").insert({"name": sn, "hourly_rate": sr}).execute()
                    st.success("Mitarbeiter angelegt!")
                    st.rerun()
    st.divider()
    try:
        st_res = supabase.table("staff").select("*").execute()
        if st_res.data:
            st_dict = {s['name']: s for s in st_res.data}
            with st.form("book_time"):
                sel_s = st.selectbox("Wer hat gearbeitet?", list(st_dict.keys()))
                hrs = st.number_input("Stunden:", min_value=0.5, step=0.5)
                if st.form_submit_button("Zeit buchen"):
                    s = st_dict[sel_s]
                    supabase.table("notes").insert({"content": f"{sel_s}: {hrs} Std.", "category": "Aufgabe", "status": "🟢 Ok", "project_name": current_project, "cost_amount": s['hourly_rate']*hrs, "is_completed": False}).execute()
                    st.success("Zeit gebucht!")
                    st.rerun()
        else: st.info("Noch keine Mitarbeiter im System.")
    except Exception as e: st.error(f"Fehler: {e}")

# PDF Export
if st.sidebar.button("📄 PDF Export"):
    pdf_res = supabase.table("notes").select("*").eq("project_name", current_project).execute()
    pdf_b = create_pdf(pdf_res.data, current_project, total_budget)
    st.sidebar.download_button("Download", pdf_b, f"Bericht_{current_project}.pdf")