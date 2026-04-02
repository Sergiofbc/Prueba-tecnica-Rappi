import os
from typing import List, Dict, Optional
import requests

class LLMClient:
    """Cliente unificado para Gemini, DeepSeek y NVIDIA"""
    
    def __init__(self, provider: str = "nvidia", api_key: Optional[str] = None):
        """
        provider: "gemini", "deepseek", o "nvidia"
        """
        self.provider = provider
        
        if provider == "nvidia":
            self.api_key = api_key or os.getenv("NVIDIA_API_KEY")
            
            if not self.api_key:
                raise ValueError("""
❌ No se encontró API key de NVIDIA.
Obtén una gratis en: https://build.nvidia.com/
Luego crea el archivo .env con: NVIDIA_API_KEY=tu_api_key
                """)
            
            self.api_url = "https://integrate.api.nvidia.com/v1/chat/completions"
            # Usar modelo Llama 3.1 70B (gratuito y potente)
            self.model = "meta/llama-3.1-70b-instruct"
            print(f"✅ NVIDIA configurado con modelo: {self.model}")
            
        elif provider == "gemini":
            self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            
            if not self.api_key:
                raise ValueError("❌ No se encontró API key de Gemini")
            
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
            self.model_name = "gemini-2.0-flash"
            print(f"✅ Gemini configurado con modelo: {self.model_name}")
            
        elif provider == "deepseek":
            self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
            self.api_url = "https://api.deepseek.com/v1/chat/completions"
            self.model = "deepseek-chat"
        else:
            raise ValueError("provider must be 'nvidia', 'gemini', or 'deepseek'")
    
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        if self.provider == "nvidia":
            return self._nvidia_chat(messages, temperature)
        elif self.provider == "gemini":
            return self._gemini_chat(messages, temperature)
        else:
            return self._deepseek_chat(messages, temperature)
    
    def _nvidia_chat(self, messages: List[Dict[str, str]], temperature: float) -> str:
        """Usa la API de NVIDIA"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1000,
            "top_p": 0.95
        }
        
        try:
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
            
        except requests.exceptions.Timeout:
            return "⏰ La solicitud tardó demasiado. Por favor intenta de nuevo."
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if "401" in error_msg:
                return "❌ Error: API key inválida. Verifica tu clave en https://build.nvidia.com/"
            elif "429" in error_msg:
                return "⚠️ Has alcanzado el límite de solicitudes. Espera un momento y vuelve a intentar."
            else:
                return f"❌ Error con NVIDIA API: {error_msg}"
    
    def _gemini_chat(self, messages: List[Dict[str, str]], temperature: float) -> str:
        """Usa la API de Google Gemini"""
        user_message = ""
        for msg in reversed(messages):
            if msg["role"] == "user":
                user_message = msg["content"]
                break
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_message,
                config={
                    "temperature": temperature,
                    "max_output_tokens": 1000,
                }
            )
            return response.text
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                return "⚠️ Cuota de Gemini agotada. Espera un momento o cambia a NVIDIA."
            return f"❌ Error con Gemini: {error_msg}"
    
    def _deepseek_chat(self, messages: List[Dict[str, str]], temperature: float) -> str:
        if not self.api_key:
            return "Error: No se configuró API key de DeepSeek"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1000
        }
        
        try:
            response = requests.post(self.api_url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Error al llamar a DeepSeek: {e}"