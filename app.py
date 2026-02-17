import streamlit as st
from audio_recorder_streamlit import audio_recorder
from supabase import create_client
import pandas as pd
import uuid

# 1. VERBINDUNG ZUERST DEFINIEREN (Wichtig!)
try:
    # Hier wird die Variable 'supabase' erstellt
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error(f"Verbindung zu Supabase fehlgeschlagen: {e}")
    st.stop()

# 2. ERST JETZT FOLGT DER LOGIN-BLOCK
if 'user' not in st.session_state:
    st.session_state.user = None

def login_mask():
    st.title("🔐 WerkOS Pro Login")
    with st.form("login_form"):
        email = st.text_input("E-Mail")
        password = st.text_input("Passwort", type="password")
        if st.form_submit_button("Anmelden", use_container_width=True):
            try:
                # Jetzt kennt das Programm 'supabase' und kann diesen Befehl ausführen
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.success("Login erfolgreich!")
                st.rerun()
            except Exception as e:
                st.error(f"Fehler: {str(e)}")

if st.session_state.user is None:
    login_mask()
    st.stop()
    # Diese Funktion sorgt dafür, dass JEDER Datensatz automatisch die user_id bekommt
def add_user(data_dict):
    if st.session_state.user:
        data_dict["user_id"] = st.session_state.user.id
    return data_dict 

# --- AB HIER DEIN BESTEHENDER v2.22 CODE ---

# --- AB HIER FOLGT DEIN BESTEHENDER v2.22 CODE UNVERÄNDERT ---

# 1. DATENBANK VERBINDUNG (Original v2.22)
try:
    supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error(f"Verbindung zu Supabase fehlgeschlagen: {e}")
    st.stop()

# 2. SEITEN-SETUP (Original v2.22)
st.set_page_config(page_title="WerkOS Pro", layout="wide")

if 'page' not in st.session_state: 
    st.session_state.page = "🏠 Home"

# 3. SIDEBAR (Exklusiv WerkOS)
with st.sidebar:
    st.title("WerkOS Pro")
    st.divider()
    if st.button("🏠 Home", use_container_width=True): st.session_state.page = "🏠 Home"
    if st.button("🏗️ Projekte", use_container_width=True): st.session_state.page = "🏗️ Projekte"
    if st.button("📋 Board", use_container_width=True): st.session_state.page = "📋 Board"
    if st.button("⏱️ Erfassung", use_container_width=True): st.session_state.page = "⏱️ Erfassung"
    if st.button("📊 Stats", use_container_width=True): st.session_state.page = "📊 Stats"
    st.divider()
    if st.button("🚪 Logout", use_container_width=True):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()
    st.caption("WerkOS v2.22 - Autarkes System")

# --- SEITE: HOME ---
if st.session_state.page == "🏠 Home":
    st.header("🏠 Home")
    st.write("Willkommen zurück im WerkOS System.")

# --- SEITE: PROJEKTE (Hinzugefügt) ---
elif st.session_state.page == "🏗️ Projekte":
    st.header("🏗️ Baustellen anlegen")
    
    with st.form("new_proj", clear_on_submit=True):
        p_name = st.text_input("Projektname")
        p_client = st.text_input("Kunde")
        
        if st.form_submit_button("Speichern"):
            if p_name:
                try:
                    # Wir senden die Daten. 
                    # Durch 'USING (true)' im SQL oben MUSS die DB das jetzt annehmen.
                    supabase.table("projects").insert({
                        "project_name": p_name, 
                        "client_name": p_client,
                        "user_id": st.session_state.user.id
                    }).execute()
                    
                    st.success(f"Baustelle '{p_name}' wurde angelegt!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Sogar mit Notregel Fehler: {e}")
    
    st.divider()
    res = supabase.table("projects").select("*").order("created_at", desc=True).execute()
    for p in (res.data if res.data else []):
        st.info(f"Projekt: {p['project_name']} (Kunde: {p['client_name']})")
# --- SEITE: BOARD (RESTAURIERT & ERGÄNZT) ---
elif st.session_state.page == "📋 Board":
    st.header("📋 Dokumentation")
    
    st.subheader("🎤 Audio-Notiz")
    audio_data = audio_recorder(text="Aufnahme starten", icon_size="2x")
    if audio_data:
        st.audio(audio_data)
        if st.button("Audio hochladen"):
            f_name = f"audio_{uuid.uuid4()}.wav"
            supabase.storage.from_("werkos_media").upload(f_name, audio_data)
            url = supabase.storage.from_("werkos_media").get_public_url(f_name)
            
            # KORREKTUR: add_user bekommt runde Klammern um das Dictionary
            supabase.table("notes").insert(add_user({
                "content": "Sprachnotiz", 
                "image_url": url, 
                "category": "Audio"
            })).execute()
            
            st.rerun()

    st.divider()
    
    # Neue Funktion: Manuelle Textnotiz & Foto
    st.subheader("✍️ Text / 📸 Foto")
    with st.form("board_entry"):
        text_input = st.text_area("Manuelle Notiz eintippen")
        img_input = st.camera_input("Foto hinzufügen")
        res_p = supabase.table("projects").select("project_name").execute()
        p_list = [p['project_name'] for p in res_p.data] if res_p.data else ["Allgemein"]
        selected_p = st.selectbox("Projekt zuordnen", p_list)
        
        if st.form_submit_button("Eintrag speichern"):
            f_url = None
            if img_input:
                f_name = f"{uuid.uuid4()}.jpg"
                supabase.storage.from_("werkos_media").upload(f_name, img_input.getvalue())
                f_url = supabase.storage.from_("werkos_media").get_public_url(f_name)
            
            # WICHTIG: Prüfe die Klammern hier am Ende:
            supabase.table("notes").insert(add_user({
                "content": text_input if text_input else "Foto-Doku",
                "project_name": selected_p,
                "image_url": f_url,
                "category": "Notiz" if text_input else "Foto"
            })).execute()
            st.rerun()

    st.divider()
    # Hier muss die Anzeige-Logik der Notizen korrekt eingerückt sein
    res_n = supabase.table("notes").select("*").order("created_at", desc=True).execute()
    for n in (res_n.data if res_n.data else []):
        with st.container(border=True):
            st.write(f"**{n.get('project_name', 'Allgemein')}** | {n['created_at'][:10]}")
            st.write(n['content'])
            if n.get('image_url'):
                if ".wav" in n['image_url']: st.audio(n['image_url'])
                else: st.image(n['image_url'], width=300)

# --- ZEILE 163: Das elif muss GANZ LINKS stehen (gleiche Ebene wie das if davor) ---
elif st.session_state.page == "⏱️ Erfassung":
    st.header("⏱️ Erfassung")
    res_p = supabase.table("projects").select("id, project_name").execute()
    p_map = {p['project_name']: p['id'] for p in res_p.data} if res_p.data else {}
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Stunden")
        with st.form("h_form"):
            p_sel = st.selectbox("Projekt", list(p_map.keys()))
            worker = st.text_input("Wer?")
            h_val = st.number_input("Stunden", step=0.5)
            if st.form_submit_button("Zeit buchen"):
                # Auch hier: add_user( { ... } )
                supabase.table("work_hours").insert(add_user({
                    "project_id": p_map[p_sel], 
                    "worker_name": worker, 
                    "hours": h_val
                })).execute()
                st.success("Zeit gebucht")
    with col2:
        st.subheader("Material")
        with st.form("m_form"):
            p_sel_m = st.selectbox("Projekt", list(p_map.keys()), key="m_p")
            item = st.text_input("Was?")
            price = st.number_input("Kosten (€)")
            if st.form_submit_button("Material speichern"):
                # Hier ebenfalls add_user() hinzugefügt für das Material
                supabase.table("notes").insert(add_user({
                    "content": f"Material: {item}", 
                    "project_name": p_sel_m, 
                    "cost_amount": price, 
                    "category": "Material"
                })).execute()
                st.success("Material gebucht")
# --- SEITE: STATS ---
elif st.session_state.page == "📊 Stats":
    st.header("📊 Statistik")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Materialkosten (bestehend)
        res = supabase.table("notes").select("cost_amount").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            # Falls cost_amount None-Werte hat, werden diese zu 0 gesetzt für die Summe
            total_cost = df['cost_amount'].fillna(0).sum()
            st.metric("Gesamt Materialkosten", f"{total_cost:,.2f} €")
        else:
            st.info("Noch keine Materialdaten vorhanden.")

    with col2:
        # Arbeitsstunden (Erweiterung)
        res_h = supabase.table("work_hours").select("hours").execute()
        if res_h.data:
            df_h = pd.DataFrame(res_h.data)
            total_hours = df_h['hours'].fillna(0).sum()
            st.metric("Gesamt Arbeitsstunden", f"{total_hours:,.1f} h")
        else:
            st.info("Noch keine Stunden gebucht.")