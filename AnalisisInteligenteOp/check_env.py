# check_env.py
import os
from dotenv import load_dotenv

print("="*50)
print("🔍 DIAGNÓSTICO DE ENTORNO")
print("="*50)

# Cargar .env
load_dotenv()
print("\n📁 Archivo .env cargado")

# Verificar variables
nvidia_key = os.getenv("NVIDIA_API_KEY")
gemini_key = os.getenv("GEMINI_API_KEY")
deepseek_key = os.getenv("DEEPSEEK_API_KEY")

print(f"\n🔑 NVIDIA_API_KEY: {'✅ Configurada' if nvidia_key else '❌ No encontrada'}")
print(f"🔑 GEMINI_API_KEY: {'✅ Configurada' if gemini_key else '❌ No encontrada'}")
print(f"🔑 DEEPSEEK_API_KEY: {'✅ Configurada' if deepseek_key else '❌ No encontrada'}")

if nvidia_key:
    print(f"   (primeros caracteres: {nvidia_key[:10]}...)")

# Verificar que podemos importar
print("\n📦 Verificando imports...")
try:
    from src.llm_client import LLMClient
    print("   ✅ LLMClient importado")
    
    # Probar conexión
    print("\n📡 Probando conexión con NVIDIA...")
    client = LLMClient(provider='nvidia', api_key=nvidia_key)
    response = client.chat([{"role": "user", "content": "Responde: OK"}])
    print(f"   ✅ Respuesta: {response[:50]}...")
    
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "="*50)
print("✅ Diagnóstico completado")