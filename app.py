import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import datetime
import json
from fpdf import FPDF

# --- 1. ZUGANGSDATEN ---
SUPABASE_URL = "https://sjviyysbjozculvslrdy.supabase.co"
SUPABASE_KEY = "sb_publishable_Mlm0V-_soOU-G78EYcOWaw_-0we6oZw"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def speech_to_text(audio_bytes):
    t = datetime.datetime.now().strftime('%H:%M')
    return f"Sprachaufnahme vom {t}"

# --- 2. PDF EXPORT ---
def create_pdf(data, project_name, total_cost):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, f"Projekt: {project_name}", ln=True, align="C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(190, 10, f"Kosten: {total_cost:.2f} EUR", ln=True, align="C")
    pdf.ln(10)
    for entry in data:
        pdf.set_font("Arial", "B", 11)
        h = f"{entry.get('status')} | {entry.get('category')} ({entry.get('created_at', '')[:10]})"
        pdf.cell(190, 8, h.encode('latin-1', 'replace').decode('latin-1'), ln=True)
        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(190, 7, entry.get('content', '').encode('latin-1', 'replace').decode('latin-1'))
        pdf.ln(5)
    return bytes(pdf.output())

st.set_page_config(page_title="WerkOS v1.5.7", page_icon="🏗️", layout="wide")
st.title("🏗️ WerkOS")

# --- 3. SIDEBAR ---
st.sidebar.header("📁 Verwaltung")
try:
    all_p = supabase.table("notes").select("project_name").execute()
    p_list = sorted(list(set([e['project_name'] for e in all_p.data if e.get('project_name')])))
except: p_list = ["Allgemein"]

current_project = st.sidebar.selectbox("Baustelle:", p_list)
new_p = st.sidebar.text_input("✨ Neue Baustelle:")
if new_p: current_project = new_p

res_costs = supabase.table("notes").select("cost_amount").eq("project_name", current_project).execute()
total_budget = sum([float(e['cost_amount']) for e in res_costs.data if e.get('cost_amount')])
st.sidebar.metric("Ausgaben", f"{total_budget:.2f} €")

filter_kat = st.sidebar.multiselect("Filter:", ["Notiz", "Aufgabe", "Material", "Wichtig"], default=["Notiz", "Aufgabe", "Material", "Wichtig"])
show_archived = st.sidebar.checkbox("Archiv")

# --- 4. TABS ---
tab1, tab2 = st.tabs(["📋 Board", "📅 Zeitplan"])

with tab1:
    st.info(f"📍 Projekt: {current_project}")
    c_in, c_med = st.columns([2, 1])
    with c_in:
        with st.form("entry_form", clear_on_submit=True):
            txt = st.text_input("Beschreibung")
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
                with st.spinner("Upload..."):
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
    st_filt = True if show_archived else False
    res = supabase.table("notes").select("*").eq("is_completed", st_filt).eq("project_name", current_project).in_("category", filter_kat).order("created_at", desc=True).execute()
    
    for e in res.data:
        eid = e['id']
        with st.container():
            col_c, col_b = st.columns([0.8, 0.2])
            with col_c:
                st.markdown(f"**{e.get('status')} | {e.get('category')} ({e.get('cost_amount', 0)} €)**")
                st.write(e['content'])
                if e.get("image_url"): st.image(e["image_url"], use_container_width=True)
            
            b1, b2, b3, _ = st.columns([0.1, 0.1, 0.1, 0.7])
            if b1.button("✅" if not st_filt else "↩️", key=f"t_{eid}"):
                supabase.table("notes").update({"is_completed": not st_filt}).eq("id", eid).execute()
                st.rerun()
            if b2.button("📝", key=f"e_{eid}"):
                st.session_state[f"ed_{eid}"] = not st.session_state.get(f"ed_{eid}", False)
            if b3.button("🗑️", key=f"d_{eid}"):
                supabase.table("notes").delete().eq("id", eid).execute()
                st.rerun()

            if st.session_state.get(f"ed_{eid}", False):
                new_s = st.radio("Status:", ["🟢 Ok", "🟡 In Arbeit", "🔴 Dringend"], key=f"r_{eid}", horizontal=True)
                new_c = st.number_input("Kosten:", value=float(e.get('cost_amount', 0)), key=f"cost_{eid}")
                if st.button("Update", key=f"s_{eid}"):
                    supabase.table("notes").update({"status": new_s, "cost_amount": new_c}).eq("id", eid).execute()
                    st.session_state[f"ed_{eid}"] = False
                    st.rerun()
            st.divider()

with tab2:
    st.subheader("📅 Zeitplan")
    cal_res = supabase.table("notes").select("*").eq("project_name", current_project).neq("category", "Notiz").order("created_at", desc=False).execute()
    for item in cal_res.data:
        mark = "✅" if item['is_completed'] else "⏳"
        st.write(f"**{item['created_at'][:10]}** | {mark} {item['category']}: {item['content']}")

if res.data:
    pdf_b = create_pdf(res.data, current_project, total_budget)
    st.sidebar.download_button("📄 PDF Bericht", pdf_b, f"{current_project}.pdf")