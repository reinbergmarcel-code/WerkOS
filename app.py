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
page = st.sidebar.radio("Gehe zu:", ["📋 Baustellen-Board", "📦 Material & Lager", "⏱️ Zeiterfassung"])

# Projektwahl
try:
    p_res = supabase.table("notes").select("project_name").execute()
    p_list = sorted(list(set([e['project_name'] for e in p_res.data if e.get('project_name')])))
except: p_list = ["Allgemein"]
if not p_list: p_list = ["Allgemein"]

current_project = st.sidebar.selectbox("Baustelle:", p_list)
new_p = st.sidebar.text_input("✨ Neue Baustelle:")
if new_p: current_project = new_p

res_costs = supabase.table("notes").select("cost_amount").eq("project_name", current_project).execute()
total_budget = sum([float(e['cost_amount']) for e in res_costs.data if e.get('cost_amount')])
st.sidebar.metric("Projekt-Ausgaben", f"{total_budget:.2f} €")

# --- SEITE 1: BOARD ---
if page == "📋 Baustellen-Board":
    st.subheader(f"Board: {current_project}")
    tab1, tab2 = st.tabs(["📋 Notizen", "📅 Verlauf"])
    with tab1:
        with st.form("entry_form", clear_on_submit=True):
            txt = st.text_input("Titel")
            c1, c2, c3 = st.columns(3)
            kat = c1.selectbox("Kat:", ["Notiz", "Aufgabe", "Material", "Wichtig"])
            prio = c2.selectbox("Status:", ["🟢 Ok", "🟡 In Arbeit", "🔴 Dringend"], index=1)
            cost = c3.number_input("Kosten €:", min_value=0.0)
            if st.form_submit_button("Speichern") and txt:
                supabase.table("notes").insert({"content": txt, "category": kat, "status": prio, "project_name": current_project, "cost_amount": cost, "is_completed": False}).execute()
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

# --- SEITE 2: MATERIAL ---
elif page == "📦 Material & Lager":
    st.subheader("📦 Materialverwaltung")
    
    # Teil A: Immer sichtbar - Neues Material anlegen
    with st.expander("➕ Neues Material zum Katalog hinzufügen", expanded=True):
        with st.form("new_mat_form"):
            n_name = st.text_input("Materialname")
            n_unit = st.selectbox("Einheit", ["Stück", "Sack", "Meter", "m²", "m³", "Paket"])
            n_price = st.number_input("Preis pro Einheit (€)", min_value=0.0)
            if st.form_submit_button("Speichern"):
                supabase.table("materials").insert({"name": n_name, "unit": n_unit, "price_per_unit": n_price}).execute()
                st.success(f"{n_name} im Katalog!")
                st.rerun()

    st.divider()
    
    # Teil B: Auswahl aus Katalog
    st.write("### Auf Baustelle buchen")
    try:
        mat_res = supabase.table("materials").select("*").execute()
        if mat_res.data and len(mat_res.data) > 0:
            mat_options = {m['name']: m for m in mat_res.data}
            with st.form("book_mat"):
                sel_name = st.selectbox("Material wählen:", list(mat_options.keys()))
                menge = st.number_input("Menge:", min_value=1.0)
                if st.form_submit_button("Jetzt buchen"):
                    m = mat_options[sel_name]
                    supabase.table("notes").insert({
                        "content": f"{menge} {m['unit']} {sel_name}",
                        "category": "Material", "status": "🟢 Ok",
                        "project_name": current_project, "cost_amount": m['price_per_unit'] * menge,
                        "is_completed": False
                    }).execute()
                    st.success("Erfolgreich auf Baustelle gebucht!")
                    st.rerun()
        else:
            st.info("Dein Katalog ist leer. Leg oben Materialien an.")
    except Exception as e:
        st.error(f"Datenbank-Fehler: {e}. Prüfe, ob die Tabelle 'materials' in Supabase existiert.")

# --- SEITE 3: ZEITERFASSUNG ---
elif page == "⏱️ Zeiterfassung":
    st.subheader("⏱️ Zeiterfassung")
    
    with st.expander("👤 Neuen Mitarbeiter anlegen", expanded=True):
        with st.form("new_staff"):
            s_name = st.text_input("Name")
            s_rate = st.number_input("Stundensatz (€)", min_value=0.0, value=45.0)
            if st.form_submit_button("Speichern"):
                supabase.table("staff").insert({"name": s_name, "hourly_rate": s_rate}).execute()
                st.success(f"{s_name} angelegt!")
                st.rerun()

    st.divider()

    st.write("### Stunden buchen")
    try:
        staff_res = supabase.table("staff").select("*").execute()
        if staff_res.data and len(staff_res.data) > 0:
            staff_options = {s['name']: s for s in staff_res.data}
            with st.form("book_time"):
                sel_staff = st.selectbox("Mitarbeiter:", list(staff_options.keys()))
                stunden = st.number_input("Stunden:", min_value=0.5, step=0.5)
                if st.form_submit_button("Zeit buchen"):
                    s = staff_options[sel_staff]
                    supabase.table("notes").insert({
                        "content": f"{sel_staff}: {stunden} Std.",
                        "category": "Aufgabe", "status": "🟢 Ok",
                        "project_name": current_project, "cost_amount": s['hourly_rate'] * stunden,
                        "is_completed": False
                    }).execute()
                    st.success("Zeit gebucht!")
                    st.rerun()
        else:
            st.info("Keine Mitarbeiter gefunden. Leg oben jemanden an.")
    except Exception as e:
        st.error(f"Datenbank-Fehler: {e}. Prüfe, ob die Tabelle 'staff' in Supabase existiert.")

# PDF Bericht
if st.sidebar.button("📄 Bericht erstellen"):
    pdf_res = supabase.table("notes").select("*").eq("project_name", current_project).execute()
    pdf_b = create_pdf(pdf_res.data, current_project, total_budget)
    st.sidebar.download_button("Download PDF", pdf_b, f"Bericht_{current_project}.pdf")