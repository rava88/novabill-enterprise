import streamlit as st
from supabase import create_client, Client
import pdfplumber
import pandas as pd
import re
import traceback
from datetime import datetime
import plotly.graph_objects as go

# --- INIZIALIZZAZIONE CLOUD ---
try:
    supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error("Errore di connessione al database. Verifica i Secrets.")

# --- LOGICA DI BUSINESS ---
class NovaIntelligence:
    @staticmethod
    def check_market_convenience(utenza, prezzo_utente, consumo_utente):
        """Confronta automaticamente i dati utente con i benchmark ARERA nel DB."""
        try:
            res = supabase.table("market_benchmarks").select("*").eq("utenza", utenza).execute()
            if res.data:
                bench = res.data[0]
                costo_unitario = prezzo_utente / consumo_utente if consumo_utente > 0 else 0
                prezzo_arera = bench['prezzo_riferimento']
                
                st.subheader("🤖 Nova Advisor - Analisi Convenienza")
                if costo_unitario > (prezzo_arera + 0.05):
                    st.error(f"⚠️ Attenzione: Stai pagando {costo_unitario:.3f}€/unità. La media ARERA è {prezzo_arera:.3f}€.")
                    st.info("Consiglio: Valuta il passaggio a un'offerta indicizzata o contatta un consulente.")
                    st.link_button("Vai al Portale Offerte ARERA", "https://www.ilportaleofferte.it/")
                else:
                    st.success("✅ Ottimo! La tua tariffa è in linea con i prezzi di mercato ARERA.")
        except:
            pass

# --- INTERFACCIA AUTH ---
def login_page():
    st.title("💎 NovaBill AI - Enterprise")
    tab1, tab2 = st.tabs(["Accedi", "Registrati"])
    
    with tab1:
        email = st.text_input("Email", key="l_email")
        pwd = st.text_input("Password", type="password", key="l_pwd")
        if st.button("Entra nel Vault"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": pwd})
                st.session_state.user = res.user
                st.rerun()
            except: st.error("Email o Password errati (o email non confermata).")
            
    with tab2:
        r_email = st.text_input("Email", key="r_email")
        r_pwd = st.text_input("Password", type="password", key="r_pwd")
        if st.button("Crea Account"):
            try:
                supabase.auth.sign_up({"email": r_email, "password": r_pwd})
                st.success("✅ Registrazione completata! Controlla l'email per confermare.")
            except Exception as e: st.error(e)

# --- MAIN APP ---
if 'user' not in st.session_state or st.session_state.user is None:
    login_page()
else:
    user = st.session_state.user
    
    # Sidebar
    st.sidebar.title("NovaBill AI")
    st.sidebar.write(f"Logged: {user.email}")
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()

    # Admin Check
    if user.email == st.secrets["ADMIN_EMAIL"]:
        if st.sidebar.checkbox("👑 Admin Panel"):
            st.title("Control Center Amministratore")
            logs = supabase.table("error_logs").select("*").execute()
            st.dataframe(logs.data)
            st.stop()

    # Dashboard Utente
    st.title("📊 La tua Dashboard Energetica")
    
    # Inserimento
    with st.expander("📝 Inserisci Bolletta (Manuale o Analisi)", expanded=True):
        col1, col2, col3 = st.columns(3)
        u_sel = col1.selectbox("Utenza", ["Luce", "Gas", "Acqua", "Tari"])
        p_val = col2.number_input("Prezzo Totale (€)", min_value=0.0, step=0.01)
        c_val = col3.number_input("Consumo Reale", min_value=0.0, step=0.1)
        
        if st.button("🚀 Salva ed Analizza"):
            try:
                # Salvataggio Cloud
                dati = {
                    "user_id": user.id,
                    "mese": datetime.now().strftime("%b"),
                    "anno": datetime.now().year,
                    "utenza": u_sel,
                    "prezzo": p_val,
                    "consumo": c_val
                }
                supabase.table("bollette").insert(dati).execute()
                st.toast("Dati salvati nel Cloud!")
                
                # Advisor Automatico
                if u_sel in ["Luce", "Gas"]:
                    NovaIntelligence.check_market_convenience(u_sel, p_val, c_val)
            except Exception as e:
                trace = traceback.format_exc()
                supabase.table("error_logs").insert({"user_email": user.email, "error_message": str(e), "stack_trace": trace}).execute()
                st.error("Errore durante il salvataggio. Segnalazione inviata all'admin.")

    # Storico Cloud
    st.divider()
    st.subheader("📚 Il tuo storico bollette")
    res_data = supabase.table("bollette").select("*").eq("user_id", user.id).execute()
    if res_data.data:
        df = pd.DataFrame(res_data.data)
        st.dataframe(df[["mese", "anno", "utenza", "prezzo", "consumo"]], use_container_width=True)
    else:
        st.info("Nessun dato presente. Carica la tua prima bolletta!")