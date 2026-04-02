# test_nvidia.py
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("NVIDIA_API_KEY")
print(f"🔑 API Key de NVIDIA encontrada: {'Sí' if api_key else 'No'}")

if api_key:
    from src.llm_client import LLMClient
    
    print("📡 Probando conexión con NVIDIA API...")
    client = LLMClient(provider='nvidia', api_key=api_key)
    
    response = client.chat([
        {"role": "user", "content": "Responde solo: 'Funciona correctamente con NVIDIA'"}
    ])
    
    print(f"✅ Respuesta: {response}")
else:
    print("❌ No se encontró API key")
    print("\n📝 Para obtener una API key de NVIDIA gratis:")
    print("1. Ve a: https://build.nvidia.com/")
    print("2. Regístrate con tu cuenta")
    print("3. Ve a 'API Keys' y crea una nueva")
    print("4. Copia la key y ejecuta:")
    print('   echo "NVIDIA_API_KEY=tu_key" >> .env')