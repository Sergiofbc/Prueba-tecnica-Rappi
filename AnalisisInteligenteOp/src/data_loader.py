import pandas as pd
import numpy as np
import os

def load_metrics_data():
    """Carga datos de métricas desde Excel"""
    # Buscar archivo Excel en data/
    excel_files = [f for f in os.listdir('data/') if f.endswith(('.xlsx', '.xls'))]
    
    df = None
    
    for file in excel_files:
        try:
            print(f"📂 Leyendo archivo: {file}")
            xl = pd.ExcelFile(f'data/{file}')
            
            # Buscar la hoja RAW_INPUT_METRICS
            if 'RAW_INPUT_METRICS' in xl.sheet_names:
                print(f"📄 Leyendo hoja: RAW_INPUT_METRICS")
                df = pd.read_excel(f'data/{file}', sheet_name='RAW_INPUT_METRICS')
                break
        except Exception as e:
            print(f"Error con {file}: {e}")
            continue
    
    if df is None:
        raise Exception("No se encontró la hoja RAW_INPUT_METRICS en ningún archivo Excel")
    
    print(f"📊 Columnas encontradas: {df.columns.tolist()}")
    
    # Las columnas ya están bien nombradas, solo asegurar que están en mayúsculas
    df.columns = [col.upper() for col in df.columns]
    
    # Verificar columnas necesarias
    required_cols = ['COUNTRY', 'CITY', 'ZONE', 'ZONE_TYPE', 'ZONE_PRIORITIZATION', 'METRIC']
    for col in required_cols:
        if col not in df.columns:
            print(f"⚠️ Advertencia: No se encontró columna '{col}'")
    
    # Identificar columnas de semanas (las que tienen L y W)
    week_cols = [col for col in df.columns if 'L' in col and 'W' in col and col not in required_cols]
    print(f"📊 Columnas de semanas encontradas: {week_cols}")
    
    # ID vars existentes
    existing_id_vars = [col for col in required_cols if col in df.columns]
    
    # Convertir a formato largo
    df_long = pd.melt(
        df,
        id_vars=existing_id_vars,
        value_vars=week_cols,
        var_name='WEEK',
        value_name='VALUE'
    )
    
    # Extraer número de semana (ej: L8W_ROLL -> 8)
    df_long['WEEK_NUM'] = df_long['WEEK'].str.extract(r'L(\d+)W')
    df_long['WEEK_NUM'] = pd.to_numeric(df_long['WEEK_NUM'], errors='coerce')
    
    # Limpiar valores
    df_long['VALUE'] = pd.to_numeric(df_long['VALUE'], errors='coerce')
    df_long = df_long.dropna(subset=['VALUE'])
    
    print(f"✅ Datos procesados: {len(df_long)} registros")
    print(f"📊 Zonas únicas: {df_long['ZONE'].nunique()}")
    print(f"📊 Métricas únicas: {df_long['METRIC'].nunique()}")
    
    return df_long

def load_orders_data():
    """Carga datos de órdenes desde Excel"""
    excel_files = [f for f in os.listdir('data/') if f.endswith(('.xlsx', '.xls'))]
    
    df = None
    
    for file in excel_files:
        try:
            xl = pd.ExcelFile(f'data/{file}')
            
            # Buscar la hoja RAW_ORDERS
            if 'RAW_ORDERS' in xl.sheet_names:
                print(f"📄 Leyendo hoja: RAW_ORDERS")
                df = pd.read_excel(f'data/{file}', sheet_name='RAW_ORDERS')
                break
        except:
            continue
    
    if df is None:
        print("⚠️ No se encontró hoja RAW_ORDERS, creando datos dummy...")
        # Crear datos dummy basados en métricas
        df_metrics = load_metrics_data()
        df = df_metrics[['COUNTRY', 'CITY', 'ZONE']].drop_duplicates().copy()
        df['METRIC'] = 'Orders'
        
        # Crear columnas de semanas
        for w in range(9):
            df[f'L{w}W'] = np.random.randint(100, 1000, len(df))
        
        return df
    
    # Limpiar nombres
    df.columns = [col.upper() for col in df.columns]
    
    # Verificar columnas
    required_cols = ['COUNTRY', 'CITY', 'ZONE', 'METRIC']
    existing_id_vars = [col for col in required_cols if col in df.columns]
    
    # Identificar columnas de semanas
    week_cols = [col for col in df.columns if 'L' in col and 'W' in col and col not in required_cols]
    
    # Convertir a formato largo
    df_long = pd.melt(
        df,
        id_vars=existing_id_vars,
        value_vars=week_cols,
        var_name='WEEK',
        value_name='ORDERS'
    )
    
    # Extraer número de semana
    df_long['WEEK_NUM'] = df_long['WEEK'].str.extract(r'L(\d+)W')
    df_long['WEEK_NUM'] = pd.to_numeric(df_long['WEEK_NUM'], errors='coerce')
    df_long['ORDERS'] = pd.to_numeric(df_long['ORDERS'], errors='coerce')
    df_long = df_long.dropna(subset=['ORDERS'])
    
    return df_long

def get_zone_summary():
    """Resumen de todas las zonas para contexto"""
    print("📊 Generando resumen de zonas...")
    
    df_metrics = load_metrics_data()
    df_orders = load_orders_data()
    
    # Pivot para tener métricas como columnas
    pivot_cols = ['COUNTRY', 'CITY', 'ZONE', 'WEEK_NUM']
    
    # Agregar ZONE_TYPE si existe
    if 'ZONE_TYPE' in df_metrics.columns:
        pivot_cols.append('ZONE_TYPE')
    
    # Agregar ZONE_PRIORITIZATION si existe
    if 'ZONE_PRIORITIZATION' in df_metrics.columns:
        pivot_cols.append('ZONE_PRIORITIZATION')
    
    # Crear pivot
    pivot = df_metrics.pivot_table(
        index=pivot_cols,
        columns='METRIC',
        values='VALUE',
        aggfunc='mean'
    ).reset_index()
    
    # Agregar órdenes si existen
    if len(df_orders) > 0 and 'ORDERS' in df_orders.columns:
        orders_pivot = df_orders.pivot_table(
            index=['COUNTRY', 'CITY', 'ZONE', 'WEEK_NUM'],
            columns='METRIC',
            values='ORDERS',
            aggfunc='sum'
        ).reset_index()
        
        final = pd.merge(pivot, orders_pivot, on=['COUNTRY', 'CITY', 'ZONE', 'WEEK_NUM'], how='left')
    else:
        final = pivot
    
    print(f"✅ Resumen generado: {len(final)} registros")
    print(f"📊 Columnas disponibles: {final.columns.tolist()[:10]}...")
    
    return final

def get_available_metrics():
    """Devuelve lista de métricas disponibles"""
    df = load_metrics_data()
    return df['METRIC'].unique().tolist()

def get_available_zones():
    """Devuelve lista de zonas disponibles"""
    df = load_metrics_data()
    return df['ZONE'].unique().tolist()

def get_available_countries():
    """Devuelve lista de países disponibles"""
    df = load_metrics_data()
    return df['COUNTRY'].unique().tolist()