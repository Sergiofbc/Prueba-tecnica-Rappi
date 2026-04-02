# test_api.py
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
print(f"🔑 API Key encontrada: {'Sí' if api_key else 'No'}")

if api_key:
    try:
        # Usar la nueva librería
        from google import genai
        
        client = genai.Client(api_key=api_key)
        
        # Probar con el modelo correcto
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents="Responde solo: 'Funciona correctamente'"
        )
        
        print(f"✅ Respuesta de Gemini: {response.text}")
        print("🎉 Todo funciona correctamente!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Soluciones:")
        print("1. Verifica que la API key sea correcta")
        print("2. Asegúrate de tener créditos en tu cuenta de Google Cloud")
        print("3. Prueba en: https://aistudio.google.com/")
else:
    print("❌ No se encontró API key")
    print("\n📝 Para obtener una API key gratis:")
    print("1. Ve a: https://aistudio.google.com/apikey")
    print("2. Inicia sesión con tu cuenta de Google")
    print("3. Haz clic en 'Create API Key'")
    print("4. Copia la key y ejecuta:")
    print('   echo "GEMINI_API_KEY=tu_key" > .env')