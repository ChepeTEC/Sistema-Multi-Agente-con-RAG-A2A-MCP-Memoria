import json
import sys
import os


ruta_mcp = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'mcp'))
sys.path.append(ruta_mcp)

from mcp_server import (
    obtener_conexion,
    get_client_profile,
    search_transactions,
    get_client_spending_behavior,
    create_fraud_case
)

def imprimir_resultado(nombre_test, json_string):
    """Función auxiliar para imprimir el JSON de forma bonita en la terminal."""
    print(f"\n{'='*50}")
    print(f" 🧪 TEST: {nombre_test}")
    print(f"{'='*50}")
    try:
        # Convertimos el string JSON a diccionario para imprimirlo con sangrías
        data = json.loads(json_string)
        print(json.dumps(data, indent=4, ensure_ascii=False))
    except Exception as e:
        print(f"❌ Error parseando JSON: {e}")
        print(f"Respuesta cruda: {json_string}")

def ejecutar_tests():
    print("\n🚀 INICIANDO BATERÍA DE PRUEBAS DEL SERVIDOR MCP...\n")

    # ---------------------------------------------------------
    # TEST 1: Conexión a la Base de Datos
    # ---------------------------------------------------------
    try:
        conn = obtener_conexion()
        print("✅ TEST 1: Conexión a la base de datos PostgreSQL exitosa.")
        conn.close()
    except Exception as e:
        print(f"❌ TEST 1: Error de conexión a la BD. Revisa que tu Docker esté encendido.\nError: {e}")
        return  # Detenemos el test si no hay base de datos

    # ---------------------------------------------------------
    # TEST 2: Validación de Seguridad (Justificación corta)
    # ---------------------------------------------------------
    # Simulamos que la IA intenta buscar sin dar una buena justificación
    resultado_seguridad = get_client_profile(1, "nada")
    imprimir_resultado("Validación de Seguridad (Debe dar error)", resultado_seguridad)

    # ---------------------------------------------------------
    # TEST 3: Perfil del Cliente y Anonimización
    # ---------------------------------------------------------
    # Simulamos un cliente_id = 1. Si tu BD usa otros IDs, cambia el '1'
    resultado_perfil = get_client_profile(1, "Auditoría de rutina solicitada por el usuario.")
    imprimir_resultado("Perfil del Cliente (Revisar asteriscos en cuenta)", resultado_perfil)

    # ---------------------------------------------------------
    # TEST 4: Búsqueda Histórica de Transacciones con Fechas
    # ---------------------------------------------------------
    resultado_transacciones = search_transactions(
        cliente_id=1,
        justificacion="Revisión de movimientos históricos por posible anomalía en el extranjero.",
        start_date="2023-01-01",
        end_date="2026-12-31"
    )
    imprimir_resultado("Búsqueda de Transacciones (Con filtro de fechas)", resultado_transacciones)

    # ---------------------------------------------------------
    # TEST 5: Análisis de Comportamiento de Gasto
    # ---------------------------------------------------------
    resultado_comportamiento = get_client_spending_behavior(
        cliente_id=1,
        justificacion="Análisis de patrón de gastos para calcular el riesgo del cliente."
    )
    imprimir_resultado("Comportamiento de Gasto Mensual", resultado_comportamiento)

    # ---------------------------------------------------------
    # TEST 6: Creación de Caso de Fraude (COMENTADO POR SEGURIDAD)
    # ---------------------------------------------------------
    # Descomenta las siguientes líneas si quieres probar que la base de datos hace el INSERT correctamente.
    # Necesitarás un 'transaccion_id' que sepas que existe en tu BD (ej. 1).
    """
    resultado_fraude = create_fraud_case(
        transaccion_id=1,
        reason="Monto inusualmente alto a las 3 AM en comercio de apuestas",
        severity="ALTA",
        justificacion="El cliente tiene un gasto promedio de $50 y esta transacción es de $5000 a un casino."
    )
    imprimir_resultado("Creación de Caso de Fraude", resultado_fraude)
    """

    print("\n" + "="*50)
    print(" 🎉 TODOS LOS TESTS HAN SIDO EJECUTADOS 🎉")
    print("="*50 + "\n")

if __name__ == "__main__":
    ejecutar_tests()