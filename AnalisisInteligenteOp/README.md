# 🤖 Rappi AI Analyst - Sistema de Análisis Inteligente para Operaciones

## 📌 Resumen Ejecutivo

**Rappi AI Analyst** es un sistema basado en inteligencia artificial que democratiza el acceso a datos operacionales y automatiza la generación de insights para los equipos de Strategy, Planning & Analytics (SP&A) y Operations de Rappi.

### Problema Resuelto
- **Acceso fragmentado a insights**: Usuarios no técnicos pueden hacer preguntas en lenguaje natural sin necesidad de SQL o Python
- **Análisis manual repetitivo**: El sistema identifica automáticamente anomalías, tendencias y oportunidades

### Entregables Implementados

#### 1. Bot Conversacional de Datos (70%)
✅ Preguntas de filtrado: "¿Cuáles son las 5 zonas con mayor Lead Penetration?"  
✅ Comparaciones: "Compara Perfect Orders entre zonas Wealthy y Non Wealthy en MX"  
✅ Tendencias temporales: "Muestra la evolución de Gross Profit UE en Chapinero"  
✅ Agregaciones: "¿Cuál es el promedio de Lead Penetration por país?"  
✅ Análisis multivariable: "¿Qué zonas tienen alto Lead Penetration pero bajo Perfect Order?"  
✅ Preguntas de inferencia: "¿Qué zonas crecen más en órdenes y por qué?"  
✅ Manejo de contexto de negocio  
✅ Memoria conversacional  
✅ Visualizaciones interactivas (Plotly)  

#### 2. Sistema de Insights Automáticos (30%)
✅ Anomalías: Cambios drásticos semana a semana (>10%)  
✅ Tendencias preocupantes: Métricas en deterioro por 3+ semanas  
✅ Correlaciones: Relaciones entre métricas operacionales  
✅ Oportunidades: Zonas con bajo Lead Penetration pero alto Perfect Order  
✅ Benchmarking: Comparación por país y tipo de zona  
✅ Reporte ejecutivo en Markdown con recomendaciones accionables  

---

## 🏗️ Arquitectura Técnica

### Stack Tecnológico

| Componente | Tecnología | Justificación |
|------------|------------|---------------|
| **Frontend** | Streamlit | Rápido desarrollo, integración nativa con Python, ideal para dashboards |
| **LLM** | NVIDIA Llama 3.1 70B | Gratuito, rápido, excelente para español, sin límites restrictivos |
| **Procesamiento de datos** | Pandas, NumPy | Manipulación eficiente de datos tabulares |
| **Visualización** | Plotly | Gráficos interactivos y profesionales |
| **Almacenamiento** | Excel/CSV | Formato original de los datos proporcionados |

### Diagrama de Arquitectura

```
[Usuario] → [Streamlit UI] → [Chatbot/Insights] → [LLM (NVIDIA)]
↓
[Data Loader]
↓
[Excel/CSV → Pandas]
```

### Flujo de Datos

1. **Carga**: Los datos se leen desde Excel (hojas RAW_INPUT_METRICS y RAW_ORDERS)
2. **Transformación**: Se pivotan y normalizan a formato largo (zona, semana, métrica, valor)
3. **Consulta**: El LLM clasifica la intención y genera SQL/Pandas equivalente
4. **Respuesta**: Se ejecuta la consulta, se formatea respuesta y se genera gráfico

---

## 📊 Estructura del Proyecto
```
AnalisisInteligenteOp/
│
├── data/
│ └── Sistema de Análisis Inteligente para Operaciones Rappi - Dummy Data (2).xlsx
│
├── src/
│ ├── init.py
│ ├── chatbot.py # Lógica del bot conversacional
│ ├── insights.py # Generador de insights automáticos
│ ├── data_loader.py # Carga y preparación de datos
│ ├── llm_client.py # Cliente unificado (NVIDIA/Gemini/DeepSeek)
│ └── utils.py # Utilidades
│
├── app.py # Aplicación principal Streamlit
├── requirements.txt # Dependencias
├── .env # Variables de entorno (API keys)
├── test_data.py # Prueba de carga de datos
├── test_nvidia.py # Prueba de API key
├── check_env.py # Diagnóstico de entorno
└── README.md # Este documento
```


---

## 🔧 Configuración e Instalación

### Requisitos Previos
- Python 3.10+
- pip (gestor de paquetes)

### Pasos de Instalación

```bash
# 1. Clonar/crear el proyecto
cd AnalisisInteligenteOp

# 2. Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate  # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar API key de NVIDIA
echo "NVIDIA_API_KEY=tu_api_key_aqui" > .env

# 5. Ejecutar la aplicación
streamlit run app.py

### Dependencias principales
streamlit
pandas
numpy
plotly
scikit-learn
google-generativeai
python-dotenv
requests
chardet


