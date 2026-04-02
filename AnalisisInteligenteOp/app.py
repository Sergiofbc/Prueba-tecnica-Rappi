# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import os
import sys

# Configurar página primero
st.set_page_config(
    page_title="Rappi AI Analyst",
    page_icon="🤖",
    layout="wide"
)

# Agregar src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ .env cargado correctamente")
except:
    print("⚠️ python-dotenv no instalado")

# Obtener API key
nvidia_key = os.getenv("NVIDIA_API_KEY")
gemini_key = os.getenv("GEMINI_API_KEY")
deepseek_key = os.getenv("DEEPSEEK_API_KEY")

# Título
st.title("🤖 Rappi AI Analyst")
st.markdown("Asistente inteligente para análisis operacional | Powered by NVIDIA Llama 3.1 70B")

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Configuración")

    llm_provider = st.selectbox(
        "Modelo LLM",
        ["nvidia", "gemini", "deepseek"],
        index=0,
        help="NVIDIA (recomendado, gratis), Gemini o DeepSeek"
    )

    if llm_provider == "nvidia":
        if nvidia_key:
            st.success("✅ NVIDIA API key configurada")
        else:
            st.warning("⚠️ NVIDIA API key no encontrada")
            st.markdown("""
            **Para obtener una API key gratis:**
            1. Ve a: https://build.nvidia.com/
            2. Regístrate
            3. Crea una API key
            4. Agrega al archivo `.env`: NVIDIA_API_KEY=tu_key
            """)

st.markdown("---")
st.markdown("### 📌 Preguntas sugeridas")

preguntas = [
    "🏆 ¿Cuáles son las 5 zonas con mayor Lead Penetration?",
    "📊 Compara Perfect Orders entre Wealthy y Non Wealthy",
    "🌍 ¿Cuál es el promedio de Gross Profit UE por país?",
    "📈 Muestra la evolución de Pro Adoption en Chapinero",
    "🎯 ¿Qué zonas tienen alto Lead Penetration pero bajo Perfect Order?",
    "🚀 ¿Qué zonas están creciendo más en órdenes?"
]

for q in preguntas:
    if st.button(q, use_container_width=True):
        st.session_state["pregunta"] = q
        st.rerun()

# Inicializar estado
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

# Mostrar mensajes existentes
for msg in st.session_state.mensajes:
    with st.chat_message(msg["rol"]):
        st.markdown(msg["contenido"])
        if "figura" in msg and msg["figura"]:
            st.plotly_chart(msg["figura"], use_container_width=True)

# Input del usuario
pregunta = st.chat_input("Haz una pregunta sobre las métricas operacionales...")

if pregunta or "pregunta" in st.session_state:
    if "pregunta" in st.session_state:
        pregunta = st.session_state["pregunta"]
        del st.session_state["pregunta"]

    with st.chat_message("user"):
        st.markdown(pregunta)

    st.session_state.mensajes.append({
        "rol": "user",
        "contenido": pregunta
    })

    with st.chat_message("assistant"):
        with st.spinner(f"🔍 Analizando datos con {llm_provider.upper()}..."):

            api_key = None
            if llm_provider == "nvidia":
                api_key = nvidia_key
            elif llm_provider == "gemini":
                api_key = gemini_key
            elif llm_provider == "deepseek":
                api_key = deepseek_key

            if not api_key:
                st.error(f"❌ No se encontró API key para {llm_provider.upper()}")
                st.markdown("Configura tu API key en el archivo `.env` y reinicia.")
            else:
                try:
                    from src.chatbot import RappiChatbot

                    chatbot = RappiChatbot(
                        llm_provider=llm_provider,
                        api_key=api_key
                    )

                    result = chatbot.execute_query(pregunta)

                    st.markdown(result["text"])

                    if result.get("figure"):
                        st.plotly_chart(result["figure"], use_container_width=True)

                    st.session_state.mensajes.append({
                        "rol": "assistant",
                        "contenido": result["text"],
                        "figura": result.get("figure")
                    })

                except Exception as e:
                    st.error(f"❌ Error: {e}")
                    import traceback
                    st.code(traceback.format_exc())

# Botón para generar reporte
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    if st.button(
        "📊 Generar Reporte Automático de Insights",
        use_container_width=True,
        type="primary"
    ):
        with st.spinner(f"🤖 Generando insights con {llm_provider.upper()}..."):

            api_key = None
            if llm_provider == "nvidia":
                api_key = nvidia_key
            elif llm_provider == "gemini":
                api_key = gemini_key
            elif llm_provider == "deepseek":
                api_key = deepseek_key

            if not api_key:
                st.error(f"❌ No se encontró API key para {llm_provider.upper()}")
            else:
                try:
                    from src.insights import InsightGenerator

                    insight_gen = InsightGenerator(
                        llm_provider=llm_provider,
                        api_key=api_key
                    )

                    report = insight_gen.generate_full_report()
                    st.session_state["reporte"] = report
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Error: {e}")

# Mostrar reporte si existe
if "reporte" in st.session_state:
    st.markdown("---")
    st.markdown("## 📈 Reporte de Insights Automáticos")
    st.markdown(st.session_state["reporte"])

    report_bytes = st.session_state["reporte"].encode('utf-8')

    st.download_button(
        label="📥 Descargar Reporte (Markdown)",
        data=report_bytes,
        file_name=f"rappi_insights_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.md",
        mime="text/markdown"
    )

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.8rem;">
Sistema de Análisis Inteligente para Operaciones Rappi<br>
Powered by NVIDIA Llama 3.1 70B
</div>
""", unsafe_allow_html=True)