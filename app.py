import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import os
from datetime import datetime

# --- Yapılandırma ---
st.set_page_config(page_title="LexiPro Français - CECRL", page_icon="🇫🇷", layout="wide")

# API Anahtarı kontrolü
api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("Lütfen GEMINI_API_KEY ortam değişkenini veya Streamlit Secret'ı ayarlayın.")
    st.stop()

genai.configure(api_key=api_key)

# --- Sabitler ---
CEFR_LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
THEMES_BY_LEVEL = {
    'A1': ['Se présenter', 'La famille', 'La maison', 'La nourriture', 'Les vêtements', 'Le temps (météo)', 'Les loisirs', 'Le corps humain', 'Les couleurs', 'Les nombres'],
    'A2': ['Les voyages', 'Le travail', 'La santé', 'Les commerces', 'La ville', 'Les transports', "L'école", 'Les animaux', 'Le logement', 'La météo ve les saisons'],
    'B1': ["L'environnement", "L'éducation", 'Les médias', 'Le monde du travail', 'Les relations sociales', 'La culture et les arts', 'Le sport', 'Le tourisme durable', "L'histoire", 'La mode'],
    'B2': ['Le changement climatique', 'Les nouvelles technologies', 'La citoyenneté', 'La mondialisation', 'La politique', "L'éthique", 'La justice', "L'économie", 'Le travail de demain', "L'intelligence artificielle"],
    'C1': ['Les nuances linguistiques', 'La philosophie moderne', 'Les débats sociétaux complexes', "L'épistémologie", 'Le patrimoine immatériel', 'Les enjeux géopolitiques', 'La psychologie sociale', "L'urbanisme", 'Le pluralisme culturel', 'Les théories esthétiques'],
    'C2': ["L'abstraction conceptuelle", 'La critique littéraire', 'Les paradoxes de la modernité', 'Le transhumanisme', 'La sémantique cognitive', "L'herméneutique", 'La sociolinguistique critique', 'La métaphysique', 'La dialectique', 'Les subtilités stylistiques']
}

# --- Fonksiyonlar ---
def generate_vocabulary(level, theme):
    model = genai.GenerativeModel('gemini-flash-latest') # Daha hızlı ve uygun maliyetli
    prompt = f"""Génère une liste exhaustive de vocabulaire français pour le niveau {level} sur le thème "{theme}". 
    Réponds EXCLUSIVEMENT sous forme de liste JSON. Her öğe şu alanları içermeli:
    term, category (Nom, Verbe, Adjectif, Adverbe, Structure/Expression), definition (en français), english, turkish, example1 (français), example2 (français)."""
    
    try:
        response = model.generate_content(prompt)
        # JSON temizleme (bazı durumlarda model markdown blokları ekleyebilir)
        text = response.text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        return json.loads(text)
    except Exception as e:
        st.error(f"Hata oluştu: {str(e)}")
        return []

# --- Arayüz ---
st.title("🇫🇷 LexiPro Français")
st.caption("Expertise CECRL - Kelime Dağarcığı ve AI Tütör")

# Yan Panel (Sidebar)
with st.sidebar:
    st.header("⚙️ Yapılandırma")
    level = st.selectbox("CECRL Seviyesi", CEFR_LEVELS)
    theme_options = THEMES_BY_LEVEL[level]
    selected_theme = st.selectbox("Önerilen Tema", ["-- Seçin --"] + theme_options)
    custom_theme = st.text_input("Veya Özel Bir Konu")
    
    final_theme = custom_theme if custom_theme else (selected_theme if selected_theme != "-- Seçin --" else "")
    
    generate_btn = st.button("Öğrenmeye Başla", disabled=not final_theme, type="primary")

# Oturum Durumu (Session State) Başlatma
if 'vocab_list' not in st.session_state:
    st.session_state.vocab_list = []
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'chat_session' not in st.session_state:
    st.session_state.chat_session = None
if 'total_input_tokens' not in st.session_state:
    st.session_state.total_input_tokens = 0
if 'total_output_tokens' not in st.session_state:
    st.session_state.total_output_tokens = 0
if 'last_input_tokens' not in st.session_state:
    st.session_state.last_input_tokens = 0
if 'last_output_tokens' not in st.session_state:
    st.session_state.last_output_tokens = 0

# Kelime Üretimi
if generate_btn:
    with st.spinner("Kelimeler hazırlanıyor..."):
        try:
            vocab_data = generate_vocabulary(level, final_theme)
            if vocab_data and hasattr(vocab_data, 'usage_metadata'):
                st.session_state.last_input_tokens = vocab_data.usage_metadata.prompt_token_count
                st.session_state.last_output_tokens = vocab_data.usage_metadata.candidates_token_count
                st.session_state.total_input_tokens += st.session_state.last_input_tokens
                st.session_state.total_output_tokens += st.session_state.last_output_tokens
            st.session_state.vocab_list = vocab_data
        except Exception as e:
            st.error(f"Kelime üretilirken bir hata oluştu: {str(e)}")
            st.session_state.vocab_list = []
            
        st.session_state.chat_history = [] # Yeni tema ile sohbeti sıfırla
        st.session_state.chat_session = None

# Ana İçerik
if st.session_state.vocab_list:
    tab1, tab2 = st.tabs(["📚 Kelime Tablosu", "💬 AI Tütör ile Pratik"])
    
    with tab1:
        df = pd.DataFrame(st.session_state.vocab_list)
        st.dataframe(df, use_container_width=True)
        
        # CSV İndirme
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "Listeyi CSV Olarak İndir",
            csv,
            f"vocabulaire_{level}_{final_theme}.csv",
            "text/csv",
            key='download-csv'
        )
        
    with tab2:
        st.subheader(f"Sohbet: {final_theme} ({level})")
        
        # Sohbet oturumunu başlat
        if st.session_state.chat_session is None:
            vocab_summary = ", ".join([item['term'] for item in st.session_state.vocab_list[:10]])
            system_instruction = f"""Tu es un enseignant de français expert. L'utilisateur a un niveau {level}.
            Le thème est "{final_theme}". Vocabulaire : {vocab_summary}.
            1. Sohbet et. 2. Kelimeleri kullandır. 3. Kibarca düzelt. 4. Gerektiğinde Türkçe kısa açıklama yap."""
            
            model = genai.GenerativeModel('gemini-flash-latest', system_instruction=system_instruction)
            st.session_state.chat_session = model.start_chat(history=[])
            
            # İlk karşılama mesajı
            welcome_text = f"Bonjour ! Je suis ravi de vous aider à pratiquer votre français au niveau {level} sur le thème '{final_theme}'. Prêt ?"
            st.session_state.chat_history.append({"role": "assistant", "content": welcome_text})

        # Mesajları Görüntüle
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Kullanıcı Girdisi
        if prompt := st.chat_input("Fransızca bir şeyler yazın..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                response = st.session_state.chat_session.send_message(prompt)
                
                # Token kullanımını güncelle
                if hasattr(response, 'usage_metadata'):
                    st.session_state.last_input_tokens = response.usage_metadata.prompt_token_count
                    st.session_state.last_output_tokens = response.usage_metadata.candidates_token_count
                    st.session_state.total_input_tokens += st.session_state.last_input_tokens
                    st.session_state.total_output_tokens += st.session_state.last_output_tokens
                
                st.markdown(response.text)
                st.session_state.chat_history.append({"role": "assistant", "content": response.text})
else:
    st.info("Sol taraftan bir seviye ve tema seçerek başlayın.")

# --- Token Kullanım Bilgileri (Sol Alt Köşe) ---
with st.sidebar:
    st.markdown("---")
    st.subheader("📊 Token Kullanımı")
    st.metric("Son Giriş Tokenları", st.session_state.last_input_tokens)
    st.metric("Son Çıkış Tokenları", st.session_state.last_output_tokens)
    st.metric("Toplam Giriş Tokenları", st.session_state.total_input_tokens)
    st.metric("Toplam Çıkış Tokenları", st.session_state.total_output_tokens)
