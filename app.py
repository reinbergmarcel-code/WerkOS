import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import datetime
import pandas as pd

# 1. DATENBANK-SETUP
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error(f"Datenbank-Verbindung fehlgeschlagen: {e}"); st.stop()

# 2. APP-STATE
if 'page' not in st.session_state: st.session_state.page = "🏠 Home"
if 'edit_id' not in st.session_state: st.session_state.edit_id = None

st.title("WerkOS Pro 🏗️")

# 3. DATEN ABFRAGEN (Notes & Projekte)
try:
    res_notes = supabase.table("notes").select("*").execute()
    all_data = res_notes.data if res_notes.data else []
except:
    all_data = []

all_p = sorted(list(set([e['project_name'] for e in all_data if e.get('project_name')])))
arch_p = list(set([e['project_name'] for e in all_data if e['content'] == "PROJECT_ARCHIVED"]))

# 4. PROJEKT-STEUERUNG
c1, c2 = st.columns([3, 1])
with c1:
    show_arch = st.checkbox("Archiv anzeigen")
    curr_p = st.selectbox("📍 Baustelle", [p for p in all_p if p not in arch_p] if not show_arch else all_p)
with c2:
    with st.popover("➕ Neu"):
        np = st.text_input("Name:")
        if st.button("Anlegen"):
            if np: 
                supabase.table("notes").insert({"content": "Start", "project_name": np, "category": "Notiz", "is_completed": False}).execute()
                st.rerun()

is_archived = curr_p in arch_p

# ARCHIVIEREN / REAKTIVIEREN
if curr_p and curr_p != "Allgemein":
    if not is_archived:
        if st.button(f"📁 '{curr_p}' ARCHIVIEREN", use_container_width=True):
            supabase.table("notes").insert({"content": "PROJECT_ARCHIVED", "project_name": curr_p, "category": "System", "is_completed": True}).execute(); st.rerun()
    else:
        if st.button(f"🔓 '{curr_p}' REAKTIVIEREN", use_container_width=True):
            supabase.table("notes").delete().eq("project_name", curr_p).eq("content", "PROJECT_ARCHIVED").execute(); st.rerun()

st.divider()

# 5. NAVIGATION
if st.session_state.page == "🏠 Home":
    col1, col2 = st.columns(2)
    if col1.button("📋 BOARD", use_container_width=True): st.session_state.page = "📋 Board"; st.rerun()
    if col1.button("📦 LAGER", use_container_width=True): st.session_state.page = "📦 Lager"; st.rerun()
    if col2.button("⏱️ ZEITEN", use_container_width=True): st.session_state.page = "⏱️ Zeiten"; st.rerun()
    if col2.button("📊 STATS", use_container_width=True): st.session_state.page = "📊 Dashboard"; st.rerun()

elif st.session_state.page == "📋 Board":
    if st.button("⬅️ MENÜ"): st.session_state.page = "🏠 Home"; st.rerun()
    if not is_archived:
        with st.expander("➕ EINTRAG"):
            audio_recorder(text="Sprachaufnahme")
            st.camera_input("Foto")
            with st.form("nb"):
                t = st.text_input("Inhalt")
                k = st.selectbox("Kategorie", ["Notiz", "Aufgabe", "Wichtig"])
                c = st.number_input("Kosten €", value=0.0)
                if st.form_submit_button("Speichern"):
                    supabase.table("notes").insert({"content":t, "category":k, "project_name":curr_p, "cost_amount":c, "is_completed":False}).execute(); st.rerun()

    items = [e for e in all_data if e['project_name'] == curr_p and not e['is_completed'] and e['content'] != "PROJECT_ARCHIVED"]
    colors = {"Notiz": "blue", "Aufgabe": "orange", "Wichtig": "red", "Material": "gray"}

    for e in items:
        if st.session_state.edit_id == e['id']:
            with st.form(f"ed_{e['id']}"):
                nt = st.text_input("Ändern", value=e['content'])
                if st.form_submit_button("OK"):
                    supabase.table("notes").update({"content": nt}).eq("id", e['id']).execute(); st.session_state.edit_id = None; st.rerun()
        else:
            with st.container(border=True):
                st.markdown(f":{colors.get(e['category'], 'blue')}[**{e['category']}**]")
                st.write(f"{e['content']}")
                st.caption(f"💰 {e.get('cost_amount',0)}€")
                if not is_archived:
                    b1, b2, b3 = st.columns(3)
                    if b1.button("✅", key=f"d_{e['id']}"): supabase.table("notes").update({"is_completed":True}).eq("id", e['id']).execute(); st.rerun()
                    if b2.button("✏️", key=f"e_{e['id']}"): st.session_state.edit_id = e['id']; st.rerun()
                    if b3.button("🗑️", key=f"x_{e['id']}"): supabase.table("notes").delete().eq("id", e['id']).execute(); st.rerun()

elif st.session_state.page == "📦 Lager":
    if st.button("⬅️ MENÜ"): st.session_state.page = "🏠 Home"; st.rerun()
    
    # --- REPARIERTE MATERIAL-ABFRAGE ---
    mat_query = supabase.table("materials").select("*").execute()
    materials = mat_query.data if mat_query.data else []
    
    if not materials:
        st.error("Keine Materialien in der Datenbank 'materials' gefunden. Bitte Tabellenstruktur prüfen.")
    else:
        t1, t2 = st.tabs(["📥 Inventur (Bestand setzen)", "📤 Verbrauch buchen"])
        
        with t1:
            with st.form("inv_update"):
                sel_mat = st.selectbox("Material wählen", [m['name'] for m in materials])
                new_q = st.number_input("Aktueller Bestand (Ist-Wert)", value=0.0)
                if st.form_submit_button("BESTAND ÜBERSCHREIBEN"):
                    m_id = next(m for m in materials if m['name'] == sel_mat)['id']
                    supabase.table("materials").update({"stock_quantity": new_q}).eq("id", m_id).execute(); st.rerun()
        
        with t2:
            if not is_archived:
                with st.form("cons_update"):
                    sel_mat = st.selectbox("Verbrauchtes Material", [m['name'] for m in materials])
                    used_q = st.number_input("Menge entnommen", value=0.0)
                    if st.form_submit_button("BUCHUNG ABSCHICKEN"):
                        m_data = next(m for m in materials if m['name'] == sel_mat)
                        # In Notes eintragen
                        supabase.table("notes").insert({"content":f"{used_q}x {sel_mat}", "category":"Material", "project_name":curr_p, "cost_amount":m_data['price_per_unit']*used_q, "is_completed":False}).execute()
                        # Bestand im Lager abziehen
                        new_stock = float(m_data['stock_quantity']) - used_q
                        supabase.table("materials").update({"stock_quantity": new_stock}).eq("id", m_data['id']).execute(); st.rerun()

        st.write("### Aktuelle Lagerliste")
        for m in materials:
            st.write(f"📦 **{m['name']}**: {m['stock_quantity']} Einheiten (Einzelpreis: {m.get('price_per_unit', 0)}€)")
