# test_data.py - Colocar en la raíz del proyecto
import os
import sys

# Agregar src al path para poder importar los módulos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("="*60)
print("🔍 VERIFICACIÓN DEL SISTEMA RAPPI AI ANALYST")
print("="*60)

# Verificar directorio actual
print(f"\n📁 Directorio actual: {os.getcwd()}")

# Verificar archivos en data
print(f"\n📁 Archivos en carpeta data/:")
if os.path.exists('data'):
    for item in os.listdir('data'):
        size = os.path.getsize(f'data/{item}') / 1024
        print(f"   ✅ {item} ({size:.1f} KB)")
else:
    print("   ❌ Carpeta 'data' no encontrada!")

print("\n" + "="*60)
print("📊 CARGANDO DATOS...")
print("="*60)

try:
    from src.data_loader import load_metrics_data, load_orders_data, get_zone_summary
    
    print("\n1️⃣ Cargando métricas operacionales...")
    df_metrics = load_metrics_data()
    print(f"   ✅ Éxito! {len(df_metrics):,} registros")
    print(f"   📊 Columnas: {df_metrics.columns.tolist()}")
    print(f"   📍 Zonas únicas: {df_metrics['ZONE'].nunique()}")
    print(f"   📈 Métricas disponibles: {', '.join(df_metrics['METRIC'].unique()[:5])}...")
    print(f"   📅 Semanas: {df_metrics['WEEK_NUM'].min()} a {df_metrics['WEEK_NUM'].max()}")
    
    print("\n2️⃣ Cargando datos de órdenes...")
    df_orders = load_orders_data()
    print(f"   ✅ Éxito! {len(df_orders):,} registros")
    if 'ORDERS' in df_orders.columns:
        print(f"   📊 Total órdenes: {df_orders['ORDERS'].sum():,.0f}")
    
    print("\n3️⃣ Generando resumen de zonas...")
    df_summary = get_zone_summary()
    print(f"   ✅ Éxito! {len(df_summary):,} registros")
    
    print("\n" + "="*60)
    print("✅ TODO FUNCIONA CORRECTAMENTE!")
    print("="*60)
    
    print("\n🚀 Para ejecutar la aplicación:")
    print("   streamlit run app.py")
    
    print("\n📊 Ejemplo de datos cargados:")
    print(df_metrics.head(3).to_string())
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()