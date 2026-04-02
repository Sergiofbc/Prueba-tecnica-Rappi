import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Any
from src.llm_client import LLMClient
from src.data_loader import get_zone_summary, load_metrics_data


class RappiChatbot:
    def __init__(self, llm_provider: str = "nvidia", api_key: str = None):
        """
        llm_provider: "nvidia", "gemini", o "deepseek"
        api_key: API key opcional (si no se pasa, busca en entorno)
        """
        # Si no se pasa API key, buscar del entorno
        if not api_key:
            if llm_provider == "nvidia":
                api_key = os.getenv("NVIDIA_API_KEY")
            elif llm_provider == "gemini":
                api_key = os.getenv("GEMINI_API_KEY")
            elif llm_provider == "deepseek":
                api_key = os.getenv("DEEPSEEK_API_KEY")
        
        self.llm = LLMClient(provider=llm_provider, api_key=api_key)
        self.df_summary = get_zone_summary()
        self.df_metrics = load_metrics_data()
        self.conversation_history = []
        
        # Diccionario de métricas para contexto
        self.metrics_context = {
            "Lead Penetration": "Cobertura de tiendas habilitadas vs prospectos",
            "Perfect Orders": "Órdenes sin cancelaciones o demoras",
            "Gross Profit UE": "Margen bruto por orden",
            "Pro Adoption": "% de usuarios suscritos a Pro",
            "Turbo Adoption": "% de usuarios que usan Turbo"
        }
        
        print(f"✅ Chatbot inicializado con {llm_provider}")

    def execute_query(self, user_query: str) -> Dict[str, Any]:
        """
        Ejecuta una consulta y retorna respuesta + visualización opcional
        """
        self.conversation_history.append({"role": "user", "content": user_query})

        # Clasificar la consulta usando Gemini
        query_type = self._classify_query(user_query)

        # Ejecutar según tipo
        if query_type == "filter":
            result = self._handle_filter(user_query)
        elif query_type == "comparison":
            result = self._handle_comparison(user_query)
        elif query_type == "trend":
            result = self._handle_trend(user_query)
        elif query_type == "aggregation":
            result = self._handle_aggregation(user_query)
        elif query_type == "multivariable":
            result = self._handle_multivariable(user_query)
        elif query_type == "inference":
            result = self._handle_inference(user_query)
        else:
            result = self._handle_general(user_query)

        # Guardar en historial
        self.conversation_history.append({"role": "assistant", "content": result["text"]})

        return result

    def _classify_query(self, query: str) -> str:
        """Usa Gemini para clasificar la intención de la consulta"""
        prompt = f"""
        Clasifica la siguiente pregunta en UNA de estas categorías:
        - filter: preguntas de filtrado (ej: "zonas con mayor X")
        - comparison: comparaciones entre grupos (ej: "Wealthy vs Non Wealthy")
        - trend: tendencias temporales (ej: "evolución de X en las últimas semanas")
        - aggregation: agregaciones por país o zona (ej: "promedio por país")
        - multivariable: análisis de dos métricas (ej: "zonas con alto X pero bajo Y")
        - inference: inferencia de causas de crecimiento o deterioro
        - general: cualquier otra pregunta

        Responde SOLO con el nombre de la categoría.

        Pregunta: {query}
        Categoría:
        """

        response = self.llm.chat([{"role": "user", "content": prompt}], temperature=0.1)
        return response.strip().lower()

    def _handle_filter(self, query: str) -> Dict[str, Any]:
        """Maneja consultas de filtrado (top zonas)"""
        # Extraer métrica y top n usando Gemini
        extract_prompt = f"""
        De la pregunta: "{query}"
        Extrae:
        1. La métrica mencionada (puede ser: Lead Penetration, Perfect Orders, Gross Profit UE, etc.)
        2. El número de zonas a mostrar (ej: "5 zonas" -> 5)

        Responde en formato: METRICA|NUMERO
        Ejemplo: Lead Penetration|5
        """

        try:
            extraction = self.llm.chat([{"role": "user", "content": extract_prompt}], temperature=0.1)
            metric, top_n = extraction.strip().split("|")
            top_n = int(top_n)
        except:
            metric = "Lead Penetration"
            top_n = 5

        # Obtener datos de última semana
        latest_week = self.df_summary['WEEK_NUM'].max()
        df_latest = self.df_summary[self.df_summary['WEEK_NUM'] == latest_week]

        # Filtrar por métrica
        if metric in df_latest.columns:
            df_sorted = df_latest.nlargest(top_n, metric)[['ZONE', 'COUNTRY', metric]]
            result_text = f"🏆 Top {top_n} zonas con mayor {metric} (semana actual):\n\n"
            for i, row in df_sorted.iterrows():
                result_text += f"{i + 1}. {row['ZONE']} ({row['COUNTRY']}): {row[metric]:.2f}\n"

            # Generar gráfico
            fig = px.bar(df_sorted, x='ZONE', y=metric, title=f"Top {top_n} zonas - {metric}")
            return {"text": result_text, "figure": fig}

        return {"text": f"No se encontraron datos para la métrica '{metric}'", "figure": None}

    def _handle_comparison(self, query: str) -> Dict[str, Any]:
        """Compara zonas Wealthy vs Non Wealthy"""
        latest_week = self.df_summary['WEEK_NUM'].max()
        df_latest = self.df_summary[self.df_summary['WEEK_NUM'] == latest_week]

        # Extraer métrica a comparar
        extract_prompt = f"""
        De la pregunta: "{query}"
        Extrae la métrica a comparar entre Wealthy y Non Wealthy.
        Responde SOLO con el nombre de la métrica.
        """

        try:
            metric = self.llm.chat([{"role": "user", "content": extract_prompt}], temperature=0.1).strip()
        except:
            metric = "Perfect Orders"

        # Calcular promedios
        wealthy_avg = df_latest[df_latest['ZONE_TYPE'] == 'Wealthy'][metric].mean()
        non_wealthy_avg = df_latest[df_latest['ZONE_TYPE'] == 'Non Wealthy'][metric].mean()

        result_text = f"""
        📊 Comparación de **{metric}** entre zonas Wealthy y Non Wealthy:

        - **Wealthy**: {wealthy_avg:.2f}
        - **Non Wealthy**: {non_wealthy_avg:.2f}
        - **Diferencia**: {wealthy_avg - non_wealthy_avg:.2f} ({((wealthy_avg - non_wealthy_avg) / non_wealthy_avg * 100):.1f}% {'mayor' if wealthy_avg > non_wealthy_avg else 'menor'} en zonas Wealthy)
        """

        # Gráfico de comparación
        comparison_df = pd.DataFrame({
            'ZONE_TYPE': ['Wealthy', 'Non Wealthy'],
            metric: [wealthy_avg, non_wealthy_avg]
        })
        fig = px.bar(comparison_df, x='ZONE_TYPE', y=metric, title=f"Comparación de {metric}")

        return {"text": result_text, "figure": fig}

    def _handle_trend(self, query: str) -> Dict[str, Any]:
        """Muestra tendencia temporal de una métrica en una zona"""
        # Extraer zona y métrica
        extract_prompt = f"""
        De la pregunta: "{query}"
        Extrae:
        1. La zona geográfica mencionada
        2. La métrica mencionada

        Responde en formato: ZONA|METRICA
        Ejemplo: Chapinero|Gross Profit UE
        """

        try:
            extraction = self.llm.chat([{"role": "user", "content": extract_prompt}], temperature=0.1)
            zone, metric = extraction.strip().split("|")
        except:
            zone = "Chapinero"
            metric = "Gross Profit UE"

        # Filtrar datos
        zone_data = self.df_metrics[
            (self.df_metrics['ZONE'].str.contains(zone, case=False)) &
            (self.df_metrics['METRIC'] == metric)
            ].sort_values('WEEK_NUM')

        if len(zone_data) > 0:
            fig = px.line(zone_data, x='WEEK_NUM', y='VALUE',
                          title=f"Evolución de {metric} en {zone}",
                          labels={'WEEK_NUM': 'Semana (0=actual)', 'VALUE': metric})

            # Análisis de tendencia con Gemini
            values = zone_data['VALUE'].tolist()
            analysis_prompt = f"""
            Analiza esta tendencia de {metric} en {zone}:
            Valores: {values[-5:]} (últimas 5 semanas)

            ¿Qué observas? ¿Hay crecimiento, decrecimiento o estabilidad?
            Responde en 2-3 líneas.
            """

            analysis = self.llm.chat([{"role": "user", "content": analysis_prompt}])
            result_text = f"📈 **Tendencia de {metric} en {zone}**\n\n{analysis}"

            return {"text": result_text, "figure": fig}

        return {"text": f"No se encontraron datos para {zone} - {metric}", "figure": None}

    def _handle_aggregation(self, query: str) -> Dict[str, Any]:
        """Agregaciones por país"""
        latest_week = self.df_summary['WEEK_NUM'].max()
        df_latest = self.df_summary[self.df_summary['WEEK_NUM'] == latest_week]

        # Extraer métrica
        extract_prompt = f"""
        De la pregunta: "{query}"
        Extrae la métrica para calcular el promedio por país.
        Responde SOLO con el nombre de la métrica.
        """

        try:
            metric = self.llm.chat([{"role": "user", "content": extract_prompt}], temperature=0.1).strip()
        except:
            metric = "Lead Penetration"

        # Calcular promedio por país
        country_avg = df_latest.groupby('COUNTRY')[metric].mean().reset_index()
        country_avg = country_avg.sort_values(metric, ascending=False)

        result_text = f"🌍 **Promedio de {metric} por país** (semana actual):\n\n"
        for _, row in country_avg.iterrows():
            result_text += f"- {row['COUNTRY']}: {row[metric]:.2f}\n"

        fig = px.bar(country_avg, x='COUNTRY', y=metric, title=f"{metric} por país")

        return {"text": result_text, "figure": fig}

    def _handle_multivariable(self, query: str) -> Dict[str, Any]:
        """Análisis multivariable (ej: alto Lead Penetration pero bajo Perfect Order)"""
        latest_week = self.df_summary[self.df_summary['WEEK_NUM'] == self.df_summary['WEEK_NUM'].max()]

        # Identificar zonas con alta Lead Penetration y bajo Perfect Order
        lead_median = latest_week['Lead Penetration'].median()
        perfect_median = latest_week['Perfect Orders'].median()

        high_low = latest_week[
            (latest_week['Lead Penetration'] > lead_median) &
            (latest_week['Perfect Orders'] < perfect_median)
            ]

        if len(high_low) > 0:
            result_text = f"🎯 **Zonas con alto Lead Penetration pero bajo Perfect Order** (oportunidad de mejora):\n\n"
            for _, row in high_low.iterrows():
                result_text += f"- {row['ZONE']} ({row['COUNTRY']}): Lead={row['Lead Penetration']:.2f}, Perfect={row['Perfect Orders']:.2f}\n"

            # Scatter plot
            fig = px.scatter(latest_week, x='Lead Penetration', y='Perfect Orders',
                             text='ZONE', title="Lead Penetration vs Perfect Orders",
                             color='ZONE_TYPE')
            fig.add_hline(y=perfect_median, line_dash="dash", line_color="red")
            fig.add_vline(x=lead_median, line_dash="dash", line_color="red")

            return {"text": result_text, "figure": fig}

        return {"text": "No se encontraron zonas con alto Lead Penetration y bajo Perfect Order", "figure": None}

        
    def _handle_inference(self, query: str) -> Dict[str, Any]:
        """Inferencia sobre causas de crecimiento"""
        from src.data_loader import load_orders_data
        
        # Usar la misma función que carga órdenes correctamente
        df_orders_long = load_orders_data()
        
        if df_orders_long is None or len(df_orders_long) == 0:
            return {"text": "No se encontraron datos de órdenes para analizar.", "figure": None}
        
        # Calcular crecimiento últimas 5 semanas
        latest_orders = df_orders_long[df_orders_long['WEEK_NUM'] == 0].groupby('ZONE')['ORDERS'].sum()
        earliest_orders = df_orders_long[df_orders_long['WEEK_NUM'] == 4].groupby('ZONE')['ORDERS'].sum()
        
        # Evitar división por cero
        growth = pd.Series(index=latest_orders.index, dtype=float)
        for zone in latest_orders.index:
            if zone in earliest_orders.index and earliest_orders[zone] > 0:
                growth[zone] = ((latest_orders[zone] - earliest_orders[zone]) / earliest_orders[zone] * 100)
            else:
                growth[zone] = 0
        
        growth = growth.sort_values(ascending=False)
        top_growth = growth.head(5)
        top_growth = top_growth[top_growth > 0]  # Solo crecimiento positivo
        
        if len(top_growth) == 0:
            return {"text": "No se encontraron zonas con crecimiento positivo en órdenes en las últimas 5 semanas.", "figure": None}
        
        # Usar Gemini/NVIDIA para análisis
        zones_list = "\n".join([f"- {zone}: +{growth_pct:.1f}%" for zone, growth_pct in top_growth.items()])
        
        analysis_prompt = f"""
        Las siguientes zonas han tenido el mayor crecimiento en órdenes en las últimas 5 semanas:
        {zones_list}
        
        Basado en métricas operacionales típicas de Rappi (Lead Penetration, Perfect Orders, Pro Adoption, Gross Profit UE, etc.),
        ¿qué podrían estar haciendo bien estas zonas? ¿Qué factores podrían explicar su crecimiento?
        Proporciona un análisis breve (3-4 líneas) con hipótesis accionables para el equipo de Operations.
        """
        
        analysis = self.llm.chat([{"role": "user", "content": analysis_prompt}])
        
        result_text = f"🚀 **Zonas con mayor crecimiento en órdenes (últimas 5 semanas):**\n\n"
        for zone, growth_pct in top_growth.items():
            result_text += f"- **{zone}**: +{growth_pct:.1f}%\n"
        result_text += f"\n💡 **Análisis de causas potenciales:**\n{analysis}"
        
        # Gráfico de crecimiento
        growth_df = pd.DataFrame({'Zona': top_growth.index, 'Crecimiento %': top_growth.values})
        fig = px.bar(growth_df, x='Zona', y='Crecimiento %', 
                    title="Top 5 zonas con mayor crecimiento en órdenes",
                    color='Crecimiento %',
                    color_continuous_scale='Greens')
        
        return {"text": result_text, "figure": fig}


    def _handle_general(self, query: str) -> Dict[str, Any]:
        """Consulta general usando Gemini"""
        # Crear contexto de datos
        latest_week = self.df_summary[self.df_summary['WEEK_NUM'] == self.df_summary['WEEK_NUM'].max()]
        summary_stats = latest_week.describe().to_string()

        prompt = f"""
        Eres un asistente de análisis de datos para Rappi. Tienes acceso a las siguientes métricas operacionales por zona:
        - Lead Penetration: cobertura de tiendas
        - Perfect Orders: calidad de órdenes
        - Gross Profit UE: rentabilidad
        - Pro Adoption: suscripciones
        - Turbo Adoption: adopción de servicio express

        Estadísticas resumidas de la última semana:
        {summary_stats}

        El usuario pregunta: {query}

        Responde de manera clara, concisa y útil. Si no tienes suficiente información, sugiere qué métricas revisar.
        """

        response = self.llm.chat([{"role": "user", "content": prompt}])
        return {"text": response, "figure": None}

    def suggest_questions(self) -> List[str]:
        """Sugiere preguntas relevantes basadas en los datos"""
        return [
            "¿Cuáles son las 5 zonas con mayor Lead Penetration?",
            "Compara Perfect Orders entre zonas Wealthy y Non Wealthy en México",
            "¿Cuál es el promedio de Gross Profit UE por país?",
            "Muestra la evolución de Pro Adoption en Chapinero",
            "¿Qué zonas tienen alto Lead Penetration pero bajo Perfect Order?",
            "¿Qué zonas están creciendo más en órdenes?"
        ]