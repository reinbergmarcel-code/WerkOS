import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import pandas as pd
import uuid

# 1. Datenbank Verbindung
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error(f"Verbindung zu Supabase fehlgeschlagen: {e}")
    st.stop()

# 2. Seiten-Setup & State
st.set_page_config(page_title="WerkOS Pro", layout="wide")
if 'page' not in st.session_state: 
    st.session_state.page = "🏠 Home"

# Sidebar Navigation
with st.sidebar:
    st.title("WerkOS Pro")
    if st.button("🏠 Dashboard", use_container_width=True): st.session_state.page = "🏠 Home"
    if st.button("🏗️ Projekte", use_container_width=True): st.session_state.page = "🏗️ Projekte"
    if st.button("📋 Board / Doku", use_container_width=True): st.session_state.page = "📋 Board"
    if st.button("⏱️ Erfassung", use_container_width=True): st.session_state.page = "⏱️ Erfassung"
    if st.button("📊 Stats", use_container_width=True): st.session_state.page = "📊 Stats"
    
    st.divider()
    st.caption("WerkOS v2.52 Beta")
# --- SEITE: HOME ---
if st.session_state.page == "🏠 Home":
    st.header("Willkommen bei WerkOS Pro")
    st.write("Wähle ein Modul in der Sidebar aus.")
    # --- SEITE: PROJEKTE ---
elif st.session_state.page == "🏗️ Projekte":
    st.header("🏗️ Projekt-Verwaltung")
    
    # Formular zum Anlegen
    with st.expander("➕ Neue Baustelle anlegen", expanded=True):
        with st.form("new_project_form", clear_on_submit=True):
            p_name = st.text_input("Projekt Name (z.B. Neubau Meyer)")
            p_client = st.text_input("Kunde / Auftraggeber")
            p_address = st.text_input("Straße / Ort")
            if st.form_submit_button("Projekt anlegen"):
                if p_name:
                    supabase.table("projects").insert({
                        "project_name": p_name, 
                        "client_name": p_client, 
                        "address": p_address
                    }).execute()
                    st.success(f"Projekt '{p_name}' wurde erstellt!")
                    st.rerun()
                else:
                    st.error("Bitte einen Projektnamen angeben.")

    st.divider()
    
    # Liste der Baustellen
    res = supabase.table("projects").select("*").order("created_at", desc=True).execute()
    projs = res.data if res.data else []
    
    if projs:
        for p in projs:
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.subheader(f"🏗️ {p['project_name']}")
                    st.write(f"👤 Kunde: {p['client_name']} | 📍 {p['address']}")
                with col2:
                    if st.button("Löschen", key=f"del_p_{p['id']}"):
                        supabase.table("projects").delete().eq("id", p['id']).execute()
                        st.rerun()
    else:
        st.info("Noch keine Projekte angelegt.")

# --- SEITE: BOARD ---
elif st.session_state.page == "📋 Board":
    st.header("📋 Baustellen-Board")
    
    # 1. Daten laden
    res_all = supabase.table("notes").select("*").execute()
    all_notes = res_all.data if res_all.data else []
    
    # Baustellen-Liste für den Filter ziehen
    projects = sorted(list(set([n['project_name'] for n in all_notes]))) if all_notes else []
    selected_p = st.selectbox("📍 Filter nach Projekt", ["Alle"] + projects)

    # 2. Neuer Eintrag (Expander)
    with st.expander("📸 Foto & Audio Aufnahme", expanded=False):
        img_file = st.camera_input("Foto aufnehmen")
        audio_data = audio_recorder(text="Sprachnotiz", icon_size="2x")

        with st.form("media_form", clear_on_submit=True):
            m_content = st.text_input("Beschreibung zum Medium")
            m_project = st.text_input("Projekt", value="Allgemein")
            m_category = st.selectbox("Kategorie", ["Notiz", "Aufgabe", "Wichtig"])
            submit_media = st.form_submit_button("Speichern")

            if submit_media:
                file_url = None
                if img_file:
                    file_name = f"{uuid.uuid4()}.jpg"
                    supabase.storage.from_("werkos_media").upload(
                        file_name, img_file.getvalue(), {"content-type": "image/jpeg"}
                    )
                    file_url = supabase.storage.from_("werkos_media").get_public_url(file_name)

                supabase.table("notes").insert({
                    "content": m_content,
                    "project_name": m_project,
                    "category": m_category,
                    "image_url": file_url
                }).execute()
                st.success("Erfolgreich gespeichert!")
                st.rerun()

    st.divider()

    # 3. Anzeige-Logik
    filtered_notes = all_notes
    if selected_p != "Alle":
        filtered_notes = [n for n in all_notes if n['project_name'] == selected_p]

    for n in reversed(filtered_notes):
        with st.container(border=True):
            col_a, col_b = st.columns([4, 1])
            with col_a:
                emoji = "📝"
                if n['category'] == "Wichtig": emoji = "🚨"
                if n['category'] == "Aufgabe": emoji = "✅"
                if n['category'] == "Material": emoji = "📦"
                
                st.markdown(f"**{emoji} {n['category']}** | {n['project_name']}")
                st.write(n['content'])
                if n.get('image_url'):
                    st.image(n['image_url'], width=300)
                if n.get('cost_amount', 0) > 0:
                    st.caption(f"💰 Kosten: {n['cost_amount']} €")
            with col_b:
                if st.button("🗑️", key=f"del_{n['id']}"):
                    supabase.table("notes").delete().eq("id", n['id']).execute()
                    st.rerun()

# --- SEITE: PROJEKTE (Neu!) ---
elif st.session_state.page == "🏗️ Projekte":
    st.header("🏗️ Projekt-Verwaltung")
    
    with st.expander("➕ Neue Baustelle anlegen"):
        with st.form("new_project"):
            p_name = st.text_input("Projekt Name (z.B. Objekt Müller)")
            p_client = st.text_input("Kunde")
            p_address = st.text_input("Adresse")
            if st.form_submit_button("Projekt erstellen"):
                supabase.table("projects").insert({
                    "project_name": p_name, 
                    "client_name": p_client, 
                    "address": p_address
                }).execute()
                st.success("Projekt angelegt!")
                st.rerun()

    # Liste der Projekte anzeigen
    res = supabase.table("projects").select("*").execute()
    projs = res.data if res.data else []
    if projs:
        st.subheader("Aktuelle Baustellen")
        for p in projs:
            with st.container(border=True):
                st.write(f"**{p['project_name']}** - {p['client_name']}")
                st.caption(f"📍 {p['address']}")

# --- SEITE: ERFASSUNG ---
elif st.session_state.page == "⏱️ Erfassung":
    st.header("⏱️ Zeit & Material erfassen")
    
    # Projekte für Dropdown laden
    res_p = supabase.table("projects").select("id, project_name").execute()
    projs = res_p.data if res_p.data else []
    
    if not projs:
        st.warning("Bitte lege zuerst ein Projekt unter '🏗️ Projekte' an!")
    else:
        proj_options = {p['project_name']: p['id'] for p in projs}
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🕒 Arbeitszeit")
            with st.form("time_entry", clear_on_submit=True):
                p_choice = st.selectbox("Projekt", options=list(proj_options.keys()))
                worker = st.text_input("Mitarbeiter")
                h_val = st.number_input("Stunden", min_value=0.25, step=0.25)
                work_desc = st.text_area("Tätigkeit")
                if st.form_submit_button("Zeit buchen"):
                    supabase.table("work_hours").insert({
                        "project_id": proj_options[p_choice],
                        "worker_name": worker,
                        "hours": h_val,
                        "description": work_desc
                    }).execute()
                    # Automatisch Eintrag ins Board für die Historie
                    supabase.table("notes").insert({
                        "content": f"Arbeitszeit: {worker} ({h_val}h) - {work_desc}",
                        "project_name": p_choice,
                        "category": "Aufgabe"
                    }).execute()
                    st.success("Zeit erfolgreich gebucht!")

        with col2:
            st.subheader("🧱 Material")
            with st.form("mat_entry", clear_on_submit=True):
                p_choice_m = st.selectbox("Projekt", options=list(proj_options.keys()))
                m_name = st.text_input("Was wurde verbraucht?")
                m_cost = st.number_input("Kosten in €", min_value=0.0)
                if st.form_submit_button("Material buchen"):
                    supabase.table("notes").insert({
                        "content": f"Material: {m_name}",
                        "project_name": p_choice_m,
                        "category": "Material",
                        "cost_amount": m_cost
                    }).execute()
                    st.success("Material erfasst!")
    
    # Projekte für das Dropdown laden
    res_p = supabase.table("projects").select("id, project_name").execute()
    projs = res_p.data if res_p.data else []
    proj_options = {p['project_name']: p['id'] for p in projs}

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🕒 Arbeitszeit buchen")
        with st.form("time_form"):
            selected_p = st.selectbox("Projekt", options=list(proj_options.keys()))
            worker = st.text_input("Mitarbeiter Name")
            h_qty = st.number_input("Stunden", min_value=0.5, step=0.5)
            desc = st.text_input("Was wurde gemacht?")
            if st.form_submit_button("Zeit speichern"):
                supabase.table("work_hours").insert({
                    "project_id": proj_options[selected_p],
                    "worker_name": worker,
                    "hours": h_qty,
                    "description": desc
                }).execute()
                st.success("Zeit gebucht!")

    with col2:
        st.subheader("🧱 Materialverbrauch")
        with st.form("mat_form"):
            selected_p_mat = st.selectbox("Projekt", options=list(proj_options.keys()))
            mat_name = st.text_input("Material (z.B. 5x OSB Platten)")
            mat_cost = st.number_input("Kosten (optional)", min_value=0.0)
            if st.form_submit_button("Material speichern"):
                # Das landet wie gewohnt im Board für die Übersicht
                supabase.table("notes").insert({
                    "content": f"Material: {mat_name}",
                    "project_name": selected_p_mat,
                    "category": "Material",
                    "cost_amount": mat_cost
                }).execute()
                st.success("Material erfasst!")

# --- SEITE: STATISTIK ---
# --- SEITE: STATISTIK (Update v3.0) ---
elif st.session_state.page == "📊 Stats":
    st.header("📊 Projekt-Controlling")
    
    # 1. Daten laden
    res_notes = supabase.table("notes").select("project_name, cost_amount, category").execute()
    res_hours = supabase.table("work_hours").select("project_id, hours").execute()
    res_projs = supabase.table("projects").select("id, project_name").execute()
    
    notes_df = pd.DataFrame(res_notes.data) if res_notes.data else pd.DataFrame()
    hours_df = pd.DataFrame(res_hours.data) if res_hours.data else pd.DataFrame()
    projs_df = pd.DataFrame(res_projs.data) if res_projs.data else pd.DataFrame()

    if projs_df.empty:
        st.info("Noch keine Daten für die Auswertung vorhanden.")
    else:
        # Stundensatz definieren (später über Einstellungen anpassbar)
        HOURLY_RATE = 55.0  

        # 2. Kennzahlen berechnen
        total_mat = notes_df['cost_amount'].sum() if not notes_df.empty else 0
        total_hours = hours_df['hours'].sum() if not hours_df.empty else 0
        total_labor = total_hours * HOURLY_RATE
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Gesamt Material", f"{total_mat:,.2f} €")
        c2.metric("Gesamt Arbeitsstunden", f"{total_hours} h")
        c3.metric("Kalk. Lohnkosten", f"{total_labor:,.2f} €", delta=f"{HOURLY_RATE}€/h")

        st.divider()

        # 3. Grafik: Kosten pro Projekt
        st.subheader("💰 Kostenverteilung nach Baustelle")
        
        # Daten für Grafik zusammenführen
        # A) Materialkosten pro Projekt
        if not notes_df.empty:
            mat_per_proj = notes_df.groupby('project_name')['cost_amount'].sum().reset_index()
        else:
            mat_per_proj = pd.DataFrame(columns=['project_name', 'cost_amount'])

        # B) Lohnkosten pro Projekt (Mapping ID zu Name)
        if not hours_df.empty:
            id_to_name = dict(zip(projs_df['id'], projs_df['project_name']))
            hours_df['project_name'] = hours_df['project_id'].map(id_to_name)
            labor_per_proj = hours_df.groupby('project_name')['hours'].sum().reset_index()
            labor_per_proj['labor_costs'] = labor_per_proj['hours'] * HOURLY_RATE
        else:
            labor_per_proj = pd.DataFrame(columns=['project_name', 'labor_costs'])

        # Zusammenführen für ein Balkendiagramm
        chart_data = pd.merge(mat_per_proj, labor_per_proj, on='project_name', how='outer').fillna(0)
        chart_data = chart_data.rename(columns={'cost_amount': 'Material', 'labor_costs': 'Lohn'})
        
        if not chart_data.empty:
            st.bar_chart(chart_data.set_index('project_name')[['Material', 'Lohn']])
        else:
            st.write("Noch keine Buchungen vorhanden.")

        # 4. Detail-Liste
        st.subheader("📋 Projekt-Details")
        st.table(chart_data)