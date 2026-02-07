import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import plotly.express as px
import traceback

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="NovaBill AI Enterprise", layout="wide", page_icon="💎")

# --- STILE CSS CUSTOM ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    .stMetric { background-color: #1e2130; padding: 20px; border-radius: 15px; border-bottom: 4px solid #007BFF; }
    .stExpander { border: 1px solid #30363d; border-radius: 10px; background-color: #161b22; }
    div.stButton > button:first-child {
        background: linear-gradient(90deg, #007BFF, #00C6FF); color: white;
        border: none; border-radius: 8px; font-weight: bold; width: 100%;
    }
    </style>
    """, unsafe_allow_index=True)

# --- CONNESSIONE CLOUD ---
try:
    supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error("Errore di configurazione: controlla i Secrets di Streamlit.")

# --- LOGICA DI AUTOMAZIONE ---
def auto_update_benchmarks():
    """Simulazione aggiornamento automatico (può essere esteso con Web Scraping)"""
    try:
        # Qui potresti inserire una chiamata API a un servizio di prezzi energia
        supabase.table("market_benchmarks").upsert([
            {"utenza": "Luce", "prezzo_monorario": 0.128, "prezzo_f1": 0.145, "prezzo_f2": 0.138, "prezzo_f3": 0.115},
            {"utenza": "Gas", "prezzo_monorario": 0.450}
        ], on_conflict="utenza").execute()
        return True
    except: return False

# --- UI DI AUTENTICAZIONE ---
def auth_ui():
    st.title("💎 NovaBill AI")
    st.markdown("### Il tuo consulente energetico digitale.")
    col1, col2 = st.columns([1, 1.2])
    
    with col1:
        tab = st.radio("Seleziona azione", ["Login", "Registrazione"], horizontal=True)
        email = st.text_input("Email")
        pwd = st.text_input("Password", type="password")
        
        if st.button("Procedi"):
            try:
                if tab == "Login":
                    res = supabase.auth.sign_in_with_password({"email": email, "password": pwd})
                    st.session_state.user = res.user
                else:
                    supabase.auth.sign_up({"email": email, "password": pwd})
                    st.success("✅ Mail inviata! Controlla la tua posta.")
                st.rerun()
            except Exception as e: st.error("Errore: Credenziali errate o email non confermata.")
    
    with col2:
        st.info("💡 **NovaBill Enterprise** analizza le tue bollette e le confronta con i prezzi ARERA in tempo reale per garantirti sempre il risparmio massimo.")

# --- APP PRINCIPALE ---
if 'user' not in st.session_state or st.session_state.user is None:
    auth_ui()
else:
    user = st.session_state.user
    
    # Sidebar
    with st.sidebar:
        st.title("NovaBill Pro")
        st.write(f"Logged as: **{user.email}**")
        if st.button("Esci"):
            st.session_state.user = None
            st.rerun()
        
        st.divider()
        if user.email == st.secrets["ADMIN_EMAIL"]:
            if st.checkbox("👑 Pannello Admin"):
                st.subheader("Gestione Sistema")
                if st.button("🔄 Forza Aggiornamento Benchmark"):
                    if auto_update_benchmarks(): st.success("Dati ARERA Aggiornati!")
                st.stop()

    # DASHBOARD
    st.title("📊 Dashboard Analitica")
    
    # Recupero Dati
    res = supabase.table("bollette").select("*").eq("user_id", user.id).order("created_at", desc=True).execute()
    df = pd.DataFrame(res.data) if res.data else pd.DataFrame()

    # Metriche
    if not df.empty:
        m1, m2, m3 = st.columns(3)
        m1.metric("Totale Spesa 2026", f"€ {df['prezzo'].sum():.2f}")
        m2.metric("Ultimo Consumo", f"{df.iloc[0]['consumo']} Unità")
        m3.metric("Stato Tariffa", "Sotto Controllo" if len(df) > 1 else "Analisi...")

    # Sezione Inserimento ed Analisi
    st.divider()
    c_in, c_ch = st.columns([1, 2])
    
    with c_in:
        st.subheader("➕ Nuova Bolletta")
        with st.form("bill_form", clear_on_submit=True):
            utenza = st.selectbox("Utenza", ["Luce", "Gas", "Acqua"])
            prezzo = st.number_input("Prezzo Totale (€)", step=0.01)
            consumo = st.number_input("Consumo Reale", step=0.1)
            submitted = st.form_submit_button("Salva ed Analizza")
            
            if submitted:
                d = {"user_id": user.id, "mese": datetime.now().strftime("%b"), "anno": 2026, "utenza": utenza, "prezzo": prezzo, "consumo": consumo}
                supabase.table("bollette").insert(d).execute()
                st.balloons()
                
                # Advisor Logic
                bench = supabase.table("market_benchmarks").select("*").eq("utenza", utenza).execute()
                if bench.data:
                    b = bench.data[0]
                    costo_u = prezzo/consumo if consumo > 0 else 0
                    if costo_u > b['prezzo_monorario']:
                        st.warning(f"Sei sopra la media ARERA di {(costo_u - b['prezzo_monorario']):.3f}€")

    with c_ch:
        st.subheader("📈 Analisi Trend")
        if not df.empty:
            fig = px.bar(df, x="mese", y="prezzo", color="utenza", barmode="group", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("Inserisci dati per visualizzare il grafico.")

    # STORICO CON ELIMINAZIONE
    st.divider()
    st.subheader("📂 Storico e Gestione")
    if not df.empty:
        for i, row in df.iterrows():
            with st.expander(f"📦 {row['utenza']} - {row['mese']} {row['anno']} - € {row['prezzo']}"):
                col_a, col_b = st.columns([4, 1])
                col_a.write(f"Dettaglio: {row['consumo']} unità registrate il {row['created_at'][:10]}")
                if col_b.button("🗑️ Elimina", key=f"del_{row['id']}"):
                    supabase.table("bollette").delete().eq("id", row['id']).execute()
                    st.rerun()
