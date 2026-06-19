import json
import sys
import os
import unittest
from unittest.mock import patch


ruta_mcp = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'mcp'))
sys.path.append(ruta_mcp)

from mcp_server import (
    obtener_conexion,
    get_client_profile,
    search_transactions,
    get_client_spending_behavior,
    create_fraud_case
)


class FakeCursor:
    def __init__(self, fetchone_result=None, fetchall_result=None):
        self.executed_query = None
        self.executed_params = None
        self.fetchone_result = fetchone_result
        self.fetchall_result = fetchall_result or []

    def execute(self, query, params=None):
        self.executed_query = query
        self.executed_params = params

    def fetchone(self):
        return self.fetchone_result or (20, 181.60, 1200.00)

    def fetchall(self):
        return self.fetchall_result

    def close(self):
        pass


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def close(self):
        pass

    def commit(self):
        pass


class McpServerUnitTests(unittest.TestCase):
    def test_spending_behavior_query_scopes_types_to_requested_client(self):
        cursor = FakeCursor()

        with patch("mcp_server.obtener_conexion", return_value=FakeConnection(cursor)):
            result = json.loads(get_client_spending_behavior(
                cliente_id=1,
                justificacion="Auditoria de comportamiento de gasto del cliente 1.",
            ))

        normalized_query = " ".join(cursor.executed_query.split())
        self.assertIn("WHERE c.cliente_id = %s AND t.tipo IN ('RETIRO', 'COMPRA')", normalized_query)
        self.assertEqual(cursor.executed_params, (1,))
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["comportamiento"]["total_transacciones_salida"], 20)

    def test_mcp_rejects_short_justification_before_database_access(self):
        with patch("mcp_server.obtener_conexion") as connection:
            result = json.loads(get_client_profile(
                cliente_id=1,
                justificacion="corto",
            ))

        connection.assert_not_called()
        self.assertIn("error", result)
        self.assertIn("justificación", result["error"])

    def test_client_profile_masks_account_numbers(self):
        cursor = FakeCursor(
            fetchall_result=[
                (1, "Cliente Demo", "MEDIO", "1234567890123456", "ACTIVA", 1500.25),
            ]
        )

        with patch("mcp_server.obtener_conexion", return_value=FakeConnection(cursor)):
            result = json.loads(get_client_profile(
                cliente_id=1,
                justificacion="Auditoria autorizada del perfil financiero.",
            ))

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"][0]["cuenta_segura"], "****-****-****-3456")
        self.assertNotIn("1234567890123456", json.dumps(result))

    def test_fraud_summary_rejects_massive_window(self):
        from mcp_server import get_fraud_case_summary

        with patch("mcp_server.obtener_conexion") as connection:
            result = json.loads(get_fraud_case_summary(
                justificacion="Revision agregada de patrones de fraude.",
                days=999,
            ))

        connection.assert_not_called()
        self.assertIn("error", result)
        self.assertIn("365", result["error"])

    def test_create_fraud_case_rejects_invalid_severity_before_insert(self):
        with patch("mcp_server.obtener_conexion") as connection:
            result = json.loads(create_fraud_case(
                transaccion_id=1,
                reason="Operacion inusual",
                severity="URGENTE",
                justificacion="Apertura de caso por patron sospechoso documentado.",
            ))

        connection.assert_not_called()
        self.assertIn("error", result)
        self.assertIn("Severidad", result["error"])

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
