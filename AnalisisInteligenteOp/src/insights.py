import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import os
from src.llm_client import LLMClient

class InsightGenerator:
    def __init__(self, llm_provider: str = "nvidia", api_key: str = None):
        # Si no se pasa API key, buscar del entorno
        if not api_key:
            if llm_provider == "nvidia":
                api_key = os.getenv("NVIDIA_API_KEY")
            elif llm_provider == "gemini":
                api_key = os.getenv("GEMINI_API_KEY")
            elif llm_provider == "deepseek":
                api_key = os.getenv("DEEPSEEK_API_KEY")
        
        self.llm = LLMClient(provider=llm_provider, api_key=api_key)
        self.df_metrics = self._load_metrics_data()
        self.df_orders = self._load_orders_data()
        print(f"✅ InsightGenerator inicializado con {llm_provider}")
        
    def _load_metrics_data(self):
        """Carga métricas usando el archivo Excel o CSV"""
        # Buscar archivo Excel
        excel_files = [f for f in os.listdir('data/') if f.endswith(('.xlsx', '.xls'))]
        
        for file in excel_files:
            try:
                xl = pd.ExcelFile(f'data/{file}')
                if 'RAW_INPUT_METRICS' in xl.sheet_names:
                    df = pd.read_excel(f'data/{file}', sheet_name='RAW_INPUT_METRICS')
                    print(f"✅ Métricas cargadas desde Excel: {file}")
                    return df
            except:
                continue
        
        # Buscar CSV
        csv_files = [f for f in os.listdir('data/') if f.endswith('.csv') and 'METRIC' in f.upper()]
        for file in csv_files:
            try:
                df = pd.read_csv(f'data/{file}', encoding='latin-1')
                print(f"✅ Métricas cargadas desde CSV: {file}")
                return df
            except:
                continue
        
        # Si no encuentra, usar el archivo RAW_INPUT_METRICS.csv
        if os.path.exists('data/RAW_INPUT_METRICS.csv'):
            df = pd.read_csv('data/RAW_INPUT_METRICS.csv', encoding='latin-1')
            print(f"✅ Métricas cargadas desde RAW_INPUT_METRICS.csv")
            return df
        
        raise Exception("No se encontró archivo de métricas")
    
    def _load_orders_data(self):
        """Carga órdenes usando el archivo Excel o CSV"""
        # Buscar archivo Excel
        excel_files = [f for f in os.listdir('data/') if f.endswith(('.xlsx', '.xls'))]
        
        for file in excel_files:
            try:
                xl = pd.ExcelFile(f'data/{file}')
                if 'RAW_ORDERS' in xl.sheet_names:
                    df = pd.read_excel(f'data/{file}', sheet_name='RAW_ORDERS')
                    print(f"✅ Órdenes cargadas desde Excel: {file}")
                    return df
            except:
                continue
        
        # Buscar CSV
        csv_files = [f for f in os.listdir('data/') if f.endswith('.csv') and 'ORDER' in f.upper()]
        for file in csv_files:
            try:
                df = pd.read_csv(f'data/{file}', encoding='latin-1')
                print(f"✅ Órdenes cargadas desde CSV: {file}")
                return df
            except:
                continue
        
        # Si no encuentra, usar el archivo RAW_ORDERS.csv
        if os.path.exists('data/RAW_ORDERS.csv'):
            df = pd.read_csv('data/RAW_ORDERS.csv', encoding='latin-1')
            print(f"✅ Órdenes cargadas desde RAW_ORDERS.csv")
            return df
        
        print("⚠️ No se encontró archivo de órdenes, creando datos dummy...")
        # Crear datos dummy
        df = self.df_metrics[['COUNTRY', 'CITY', 'ZONE']].drop_duplicates().copy()
        df['METRIC'] = 'Orders'
        for w in range(9):
            df[f'L{w}W'] = np.random.randint(100, 1000, len(df))
        return df
    
    def generate_full_report(self) -> str:
        """Genera reporte completo de insights"""
        
        insights = []
        
        # 1. Anomalías semanales
        anomalies = self._find_anomalies()
        if anomalies:
            insights.append({"category": "⚠️ Anomalías", "insights": anomalies[:5]})
        
        # 2. Tendencias preocupantes
        trends = self._find_trends()
        if trends:
            insights.append({"category": "📉 Tendencias Negativas", "insights": trends[:5]})
        
        # 3. Correlaciones importantes
        correlations = self._find_correlations()
        if correlations:
            insights.append({"category": "🔗 Correlaciones Clave", "insights": correlations[:5]})
        
        # 4. Oportunidades
        opportunities = self._find_opportunities()
        if opportunities:
            insights.append({"category": "💡 Oportunidades", "insights": opportunities[:5]})
        
        # 5. Benchmarks
        benchmarks = self._find_benchmarks()
        if benchmarks:
            insights.append({"category": "📊 Benchmarking", "insights": benchmarks[:5]})
        
        # Generar resumen ejecutivo con Gemini
        executive_summary = self._generate_executive_summary(insights)
        
        # Construir reporte final
        report = self._build_report(executive_summary, insights)
        
        return report
    
    def _find_anomalies(self) -> list:
        """Encuentra cambios drásticos (>10%) semana a semana"""
        # Identificar columnas de semanas
        week_cols = [col for col in self.df_metrics.columns if 'L' in col and 'W' in col]
        
        if not week_cols:
            return []
        
        anomalies = []
        
        # Para cada zona y métrica
        for (zone, metric), group in self.df_metrics.groupby(['ZONE', 'METRIC']):
            try:
                # Obtener valores de las últimas 2 semanas
                latest_weeks = [col for col in week_cols if col not in ['L8W', 'L7W']]
                if len(latest_weeks) >= 2:
                    last_week_val = group[latest_weeks[0]].iloc[0] if len(latest_weeks) > 0 else 0
                    prev_week_val = group[latest_weeks[1]].iloc[0] if len(latest_weeks) > 1 else 0
                    
                    if prev_week_val != 0:
                        pct_change = (last_week_val - prev_week_val) / prev_week_val * 100
                        
                        if abs(pct_change) > 10:
                            anomalies.append({
                                "zone": zone,
                                "metric": metric,
                                "change": pct_change,
                                "description": f"{zone} tuvo un cambio del {pct_change:.1f}% en {metric}",
                                "recommendation": f"Revisar causas del {'aumento' if pct_change > 0 else 'deterioro'} en {zone} para {metric}"
                            })
            except:
                continue
        
        return anomalies
    
    def _find_trends(self) -> list:
        """Encuentra métricas en deterioro"""
        week_cols = sorted([col for col in self.df_metrics.columns if 'L' in col and 'W' in col])
        
        if len(week_cols) < 4:
            return []
        
        trends = []
        
        for (zone, metric), group in self.df_metrics.groupby(['ZONE', 'METRIC']):
            try:
                values = []
                for col in week_cols[-4:]:  # Últimas 4 semanas
                    val = group[col].iloc[0] if not pd.isna(group[col].iloc[0]) else 0
                    values.append(val)
                
                if len(values) == 4 and all(values[i] > values[i+1] for i in range(3)):
                    pct_decline = (values[-1] - values[0]) / values[0] * 100 if values[0] != 0 else 0
                    trends.append({
                        "zone": zone,
                        "metric": metric,
                        "decline": pct_decline,
                        "description": f"{zone} muestra deterioro en {metric} por 3+ semanas",
                        "recommendation": f"Analizar estrategias para revertir tendencia en {zone}"
                    })
            except:
                continue
        
        return trends
    
    def _find_correlations(self) -> list:
        """Encuentra correlaciones entre métricas"""
        # Seleccionar solo métricas numéricas
        numeric_cols = self.df_metrics.select_dtypes(include=[np.number]).columns
        metric_cols = [col for col in numeric_cols if 'L' not in col and col not in ['COUNTRY', 'CITY', 'ZONE', 'WEEK_NUM']]
        
        if len(metric_cols) < 2:
            return []
        
        correlations = []
        
        for i in range(len(metric_cols)):
            for j in range(i+1, len(metric_cols)):
                try:
                    corr = self.df_metrics[metric_cols[i]].corr(self.df_metrics[metric_cols[j]])
                    if abs(corr) > 0.7:
                        correlations.append({
                            "metrics": f"{metric_cols[i]} y {metric_cols[j]}",
                            "correlation": corr,
                            "description": f"Alta correlación ({corr:.2f}) entre {metric_cols[i]} y {metric_cols[j]}",
                            "recommendation": f"Monitorear ambas métricas juntas; acciones en una pueden afectar la otra"
                        })
                except:
                    continue
        
        return correlations
    
    def _find_opportunities(self) -> list:
        """Encuentra oportunidades de mejora"""
        opportunities = []
        
        # Buscar columnas de Lead Penetration y Perfect Orders
        lead_col = None
        perfect_col = None
        
        for col in self.df_metrics.columns:
            if 'LEAD' in col.upper() or 'PENETRATION' in col.upper():
                lead_col = col
            if 'PERFECT' in col.upper() or 'ORDER' in col.upper():
                perfect_col = col
        
        if lead_col and perfect_col:
            # Calcular medianas
            lead_median = self.df_metrics[lead_col].median()
            perfect_median = self.df_metrics[perfect_col].median()
            
            # Encontrar zonas con bajo lead pero alto perfect
            opportunities_zones = self.df_metrics[
                (self.df_metrics[lead_col] < lead_median) &
                (self.df_metrics[perfect_col] > perfect_median)
            ]
            
            for _, row in opportunities_zones.head(5).iterrows():
                opportunities.append({
                    "zone": row['ZONE'],
                    "country": row.get('COUNTRY', 'N/A'),
                    "type": "Low Lead, High Perfect",
                    "description": f"{row['ZONE']} tiene bajo Lead Penetration pero alto Perfect Order",
                    "recommendation": f"Explorar por qué estos usuarios no adoptan nuevos comercios. Potencial de crecimiento."
                })
        
        return opportunities
    
    def _find_benchmarks(self) -> list:
        """Benchmarking entre países"""
        benchmarks = []
        
        # Seleccionar métricas numéricas
        numeric_cols = self.df_metrics.select_dtypes(include=[np.number]).columns
        metric_cols = [col for col in numeric_cols if 'L' not in col and col not in ['WEEK_NUM']]
        
        if 'COUNTRY' in self.df_metrics.columns:
            for metric in metric_cols[:5]:  # Top 5 métricas
                country_avg = self.df_metrics.groupby('COUNTRY')[metric].mean()
                for country, avg in country_avg.items():
                    benchmarks.append({
                        "country": country,
                        "metric": metric,
                        "avg_value": avg,
                        "description": f"En {country}, {metric} promedio es {avg:.2f}",
                        "recommendation": f"Comparar estrategias para mejorar {metric}"
                    })
        
        return benchmarks
    
    def _generate_executive_summary(self, insights: list) -> str:
        """Genera resumen ejecutivo usando Gemini"""
        all_insights_text = ""
        for category in insights:
            all_insights_text += f"\n{category['category']}:\n"
            for insight in category['insights'][:3]:
                all_insights_text += f"- {insight['description']}\n"
        
        prompt = f"""
        Basado en los siguientes insights generados automáticamente:
        {all_insights_text}
        
        Genera un resumen ejecutivo (máximo 5 líneas) con los 3-5 hallazgos más críticos y accionables para el equipo de Operations de Rappi.
        """
        
        try:
            return self.llm.chat([{"role": "user", "content": prompt}])
        except:
            return "Resumen ejecutivo: Los datos muestran oportunidades de mejora en zonas con bajo Lead Penetration y tendencias negativas en algunas métricas. Se recomienda priorizar las zonas identificadas."
    
    def _build_report(self, executive_summary: str, insights: list) -> str:
        """Construye reporte en formato Markdown"""
        report = "# 📊 Rappi Insights - Reporte Automático\n\n"
        report += f"*Fecha de generación: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}*\n\n"
        report += "## 📌 Resumen Ejecutivo\n\n"
        report += executive_summary + "\n\n"
        report += "---\n\n"
        
        for category in insights:
            report += f"## {category['category']}\n\n"
            for insight in category['insights']:
                report += f"### {insight.get('zone', insight.get('metrics', insight.get('country', 'Hallazgo')))}\n"
                report += f"**Hallazgo:** {insight['description']}\n\n"
                report += f"**Recomendación:** {insight['recommendation']}\n\n"
            report += "---\n\n"
        
        report += "\n*Reporte generado automáticamente por Rappi AI Analyst*\n"
        
        return report