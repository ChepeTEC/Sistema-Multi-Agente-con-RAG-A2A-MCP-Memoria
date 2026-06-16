import os
import json
import sys
from pathlib import Path

raiz_proyecto = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'agents'))
sys.path.append(raiz_proyecto)
from transactional_agent import TransactionalAgent

def ejecutar_test():
    print("=" * 60)
    print(" INICIANDO TEST DEL AGENTE TRANSACCIONAL (MODO SÍNCRONO) ")
    print("=" * 60)

    # 1. Validación rápida de la API Key en el entorno actual
    if not os.getenv("GEMINI_API_KEY"):
        print("[ALERTA] No se detectó GEMINI_API_KEY en las variables de entorno.")
        print("Asegúrate de que tu orquestador ejecute load_dotenv() antes de llamar al agente.\n")
    
    try:
        # 2. Instanciamos el agente (tal como lo harán tus compañeros)
        print("[1/3] Instanciando TransactionalAgent...")
        agente = TransactionalAgent()
        
        # 3. Definimos una pregunta que obligue al agente a usar el Servidor MCP y Docker
        pregunta = (
            "Revisa las últimas 10 transacciones del cliente 3. Si detectas un retiro o compra que supere por mucho su gasto promedio histórico, o que esté dirigido a un comercio de riesgo ALTO, abre un caso de fraude inmediatamente con severidad CRITICA y explícame al detalle qué datos usaste para tomar esta decisión"


        )
        print(f"[2/3] Enviando pregunta de prueba:\n     '{pregunta}'")
        print("-" * 60)
        print("Pensando... (Conectando a MCP y procesando con Gemini)")
        
        # 4. LLAMADA SÍNCRONA: Probamos que 'answer' resuelva la corrutina internamente
        resultado = agente.answer(question=pregunta)
        print("-" * 60)
        print("[3/3] ¡Respuesta recibida con éxito!")
        
        # 5. Mostramos el diccionario resultante formateado
        print("\nESTRUCTURA DEL DICCIONARIO DEVUELTO:")
        print(json.dumps(resultado, indent=4, ensure_ascii=False))
        
        print("\n" + "=" * 60)
        print(" 🎉 TEST FINALIZADO: EL ADAPTADOR SÍNCRONO FUNCIONA PERFECTO 🎉 ")
        print("=" * 60)

    except Exception as e:
        print("\n" + "!" * 60)
        print(f" ❌ EL TEST FALLÓ: {str(e)}")
        print("!" * 60)

if __name__ == "__main__":
    ejecutar_test()