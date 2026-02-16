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
    if st.button("🏠 Home", use_container_width=True): st.session_state.page = "🏠 Home"
    if st.button("📋 Board", use_container_width=True): st.session_state.page = "📋 Board"
    if st.button("📦 Lager", use_container_width=True): st.session_state.page = "📦 Lager"
    if st.button("📊 Stats", use_container_width=True): st.session_state.page = "📊 Stats"

# --- SEITE: HOME ---
if st.session_state.page == "🏠 Home":
    st.header("Willkommen bei WerkOS Pro")
    st.write("Wähle ein Modul in der Sidebar aus.")

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

# --- SEITE: LAGER ---
elif st.session_state.page == "📦 Lager":
    st.header("📦 Lagerverwaltung & Buchung")
    
    res = supabase.table("materials").select("*").execute()
    mats = res.data if res.data else []
    
    if not mats:
        st.info("Keine Materialien gefunden.")
    else:
        df = pd.DataFrame(mats)
        st.dataframe(df[["name", "stock_quantity", "unit", "price_per_unit"]], use_container_width=True)
        
        st.divider()
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📤 Verbrauch buchen")
            with st.form("usage_form", clear_on_submit=True):
                m_choice = st.selectbox("Material wählen", [m['name'] for m in mats])
                m_qty = st.number_input("Menge entnommen", min_value=0.0, step=1.0)
                m_project = st.text_input("Für Projekt/Baustelle", value="Allgemein")
                
                if st.form_submit_button("Verbrauch Speichern"):
                    selected_mat = next(m for m in mats if m['name'] == m_choice)
                    new_qty = float(selected_mat['stock_quantity']) - m_qty
                    cost = m_qty * float(selected_mat['price_per_unit'])
                    
                    supabase.table("materials").update({"stock_quantity": new_qty}).eq("id", selected_mat['id']).execute()
                    supabase.table("notes").insert({
                        "content": f"Verbrauch: {m_qty}x {m_choice}",
                        "category": "Material",
                        "project_name": m_project,
                        "cost_amount": cost
                    }).execute()
                    
                    st.success(f"Gebucht! Neuer Restbestand: {new_qty}")
                    st.rerun()

        with col2:
            st.subheader("📥 Inventur")
            with st.form("inv_form", clear_on_submit=True):
                m_choice_inv = st.selectbox("Material korrigieren", [m['name'] for m in mats])
                m_new_total = st.number_input("Tatsächlicher Bestand", min_value=0.0)
                if st.form_submit_button("Bestand Aktualisieren"):
                    sel_inv = next(m for m in mats if m['name'] == m_choice_inv)
                    supabase.table("materials").update({"stock_quantity": m_new_total}).eq("id", sel_inv['id']).execute()
                    st.success("Lagerbestand angepasst!")
                    st.rerun()

# --- SEITE: STATISTIK ---
elif st.session_state.page == "📊 Stats":
    st.header("📊 Kosten-Übersicht")
    res = supabase.table("notes").select("project_name, cost_amount, category").execute()
    data = res.data if res.data else []
    
    if not data:
        st.info("Noch keine Kostendaten vorhanden.")
    else:
        df = pd.DataFrame(data)
        total_costs = df['cost_amount'].sum()
        st.metric("Gesamtausgaben (Material)", f"{total_costs:,.2f} €")
        
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("💰 Kosten pro Projekt")
            project_costs = df.groupby('project_name')['cost_amount'].sum().sort_values(ascending=False)
            st.bar_chart(project_costs)
        with col2:
            st.subheader("📋 Einträge pro Projekt")
            project_counts = df['project_name'].value_counts()
            st.area_chart(project_counts)