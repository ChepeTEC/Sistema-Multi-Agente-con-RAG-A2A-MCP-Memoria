import json
import psycopg2
from mcp.server.fastmcp import FastMCP

# ==========================================
# 1. CONFIGURACIÓN INICIAL Y CONEXIÓN
# ==========================================

mcp = FastMCP("Servidor Transaccional Seguro")

DB_CONFIG = {
    'dbname': 'mcp_db',
    'user': 'admin',
    'password': 'password',
    'host': 'localhost',
    'port': '5432'
}

def obtener_conexion():
    """Crea y retorna una conexión a la base de datos PostgreSQL en Docker."""
    return psycopg2.connect(**DB_CONFIG)

# ==========================================
# 2. FUNCIONES DE SEGURIDAD (RÚBRICA)
# ==========================================

def enmascarar_cuenta(numero_cuenta: str) -> str:
    """REGLA DE SEGURIDAD: Oculta la cuenta dejando solo los últimos 4 dígitos."""
    if not numero_cuenta or len(numero_cuenta) < 4:
        return numero_cuenta
    return "****-****-****-" + numero_cuenta[-4:]

def validar_justificacion(justificacion: str) -> str | None:
    """REGLA DE SEGURIDAD: Verifica que el agente envíe una justificación válida."""
    if not justificacion or len(justificacion) < 10:
        return json.dumps({"error": "Seguridad: Se requiere una justificación detallada (>10 caracteres) para ejecutar esta acción."})
    return None

# ==========================================
# 3. HERRAMIENTAS MCP (LECTURA Y AUDITORÍA)
# ==========================================

@mcp.tool()
def get_client_profile(cliente_id: int, justificacion: str) -> str:
    """
    Obtiene el perfil general de un cliente y el estado de sus cuentas.
    
    Args:
        cliente_id (int): El ID único del cliente.
        justificacion (str): Motivo de la auditoría.
    """
    error = validar_justificacion(justificacion)
    if error: return error

    query = """
        SELECT c.id, c.nombre, c.nivel_riesgo, cu.numero_cuenta, cu.estado, cu.saldo
        FROM clientes c
        LEFT JOIN cuentas cu ON c.id = cu.cliente_id
        WHERE c.id = %s;
    """
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute(query, (cliente_id,))
        filas = cursor.fetchall()
        
        if not filas:
            return json.dumps({"status": "not_found", "message": "Cliente no encontrado."})
            
        resultados = []
        for fila in filas:
            resultados.append({
                "cliente_id": fila[0],
                "nombre": fila[1],
                "nivel_riesgo": fila[2],
                "cuenta_segura": enmascarar_cuenta(fila[3]), # Anonimización aplicada
                "estado_cuenta": fila[4],
                "saldo_actual": float(fila[5]) if fila[5] else 0.0
            })
            
        return json.dumps({"status": "success", "data": resultados})
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@mcp.tool()
def search_transactions(cliente_id: int, justificacion: str, start_date: str = None, end_date: str = None) -> str:
    """
    Busca transacciones de un cliente. Para búsquedas históricas, usa rangos de fecha.
    No permite búsquedas masivas.
    
    Args:
        cliente_id (int): ID del cliente (Obligatorio para evitar consultas masivas).
        justificacion (str): Motivo de la búsqueda.
        start_date (str, opcional): Fecha inicio (YYYY-MM-DD).
        end_date (str, opcional): Fecha fin (YYYY-MM-DD).
    """
    error = validar_justificacion(justificacion)
    if error: return error

    # Construcción dinámica de la query para soportar rangos de fechas (Rúbrica)
    query = """
        SELECT t.id, t.monto, t.tipo, t.fecha_hora, t.pais_origen, t.estado, t.comercio_o_destino, c.numero_cuenta
        FROM transacciones t
        JOIN cuentas c ON t.cuenta_id = c.id
        WHERE c.cliente_id = %s
    """
    params = [cliente_id]

    if start_date:
        query += " AND t.fecha_hora >= %s"
        params.append(start_date)
    if end_date:
        query += " AND t.fecha_hora <= %s"
        params.append(end_date)
        
    # Límite estricto para evitar colapsos
    query += " ORDER BY t.fecha_hora DESC LIMIT 50;"
    
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        filas = cursor.fetchall()
        
        resultados = []
        for fila in filas:
            resultados.append({
                "transaccion_id": fila[0],
                "monto": float(fila[1]),
                "tipo": fila[2],
                "fecha": fila[3].strftime("%Y-%m-%d %H:%M:%S") if hasattr(fila[3], 'strftime') else str(fila[3]),
                "pais_origen": fila[4],
                "estado": fila[5],
                "comercio": fila[6],
                "cuenta_segura": enmascarar_cuenta(fila[7])
            })
            
        return json.dumps({"status": "success", "count": len(resultados), "data": resultados})
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@mcp.tool()
def get_client_spending_behavior(cliente_id: int, justificacion: str) -> str:
    """
    Calcula el comportamiento promedio de gasto mensual de un cliente para detectar desviaciones.
    
    Args:
        cliente_id (int): ID del cliente.
        justificacion (str): Motivo de la evaluación estadística.
    """
    error = validar_justificacion(justificacion)
    if error: return error

    query = """
        SELECT COUNT(t.id), AVG(t.monto), MAX(t.monto)
        FROM transacciones t
        JOIN cuentas c ON t.cuenta_id = c.id
        WHERE c.cliente_id = %s AND t.tipo IN ('RETIRO', 'COMPRA');
    """
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute(query, (cliente_id,))
        fila = cursor.fetchone()
        
        return json.dumps({
            "status": "success",
            "comportamiento": {
                "total_transacciones_salida": fila[0],
                "gasto_promedio_historico": float(fila[1]) if fila[1] else 0.0,
                "gasto_maximo_registrado": float(fila[2]) if fila[2] else 0.0
            }
        })
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@mcp.tool()
def get_merchant_risk_score(merchant_name: str, justificacion: str) -> str:
    """
    Evalúa el nivel de riesgo de un comercio específico según bases de datos internas.
    
    Args:
        merchant_name (str): Nombre del comercio o destinatario.
        justificacion (str): Motivo de la verificación.
    """
    error = validar_justificacion(justificacion)
    if error: return error

    # Simulación de un motor de riesgo (Puedes cambiarlo por una consulta SQL si tienes una tabla de comercios)
    comercios_riesgosos = ["casino", "bet", "crypto", "apuestas", "lotería", "offshore"]
    merchant_lower = merchant_name.lower()
    
    riesgo = "BAJO"
    if any(palabra in merchant_lower for palabra in comercios_riesgosos):
        riesgo = "ALTO"
        
    return json.dumps({
        "status": "success", 
        "comercio": merchant_name, 
        "nivel_riesgo_sugerido": riesgo,
        "nota": "Riesgo ALTO si coincide con plataformas de criptomonedas o apuestas."
    })

@mcp.tool()
def get_fraud_case_summary(justificacion: str, days: int = 30) -> str:
    """
    Resume los casos de fraude existentes sin consultar transacciones masivamente.

    Args:
        justificacion (str): Motivo de la revision agregada de patrones de fraude.
        days (int): Ventana temporal a revisar. Por defecto limita a los ultimos 30 dias.
    """
    error = validar_justificacion(justificacion)
    if error: return error

    try:
        days = int(days)
    except (TypeError, ValueError):
        return json.dumps({"error": "days debe ser un entero positivo."})

    if days < 1 or days > 365:
        return json.dumps({"error": "days debe estar entre 1 y 365 para evitar consultas masivas."})

    summary_query = """
        SELECT severidad, estado_caso, COUNT(*)
        FROM casos_fraude
        WHERE fecha_apertura >= CURRENT_TIMESTAMP - (%s * INTERVAL '1 day')
        GROUP BY severidad, estado_caso
        ORDER BY severidad, estado_caso;
    """
    cases_query = """
        SELECT cf.id, cf.transaccion_id, cf.motivo, cf.severidad, cf.estado_caso,
               t.monto, t.tipo, t.fecha_hora, t.pais_origen, t.comercio_o_destino,
               c.cliente_id
        FROM casos_fraude cf
        JOIN transacciones t ON cf.transaccion_id = t.id
        JOIN cuentas c ON t.cuenta_id = c.id
        WHERE cf.fecha_apertura >= CURRENT_TIMESTAMP - (%s * INTERVAL '1 day')
        ORDER BY cf.fecha_apertura DESC
        LIMIT 20;
    """

    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute(summary_query, (days,))
        resumen = [
            {
                "severidad": fila[0],
                "estado": fila[1],
                "cantidad": fila[2],
            }
            for fila in cursor.fetchall()
        ]

        cursor.execute(cases_query, (days,))
        casos = []
        for fila in cursor.fetchall():
            casos.append({
                "caso_id": fila[0],
                "transaccion_id": fila[1],
                "motivo": fila[2],
                "severidad": fila[3],
                "estado": fila[4],
                "monto": float(fila[5]),
                "tipo": fila[6],
                "fecha": fila[7].strftime("%Y-%m-%d %H:%M:%S") if hasattr(fila[7], 'strftime') else str(fila[7]),
                "pais_origen": fila[8],
                "comercio": fila[9],
                "cliente_id": fila[10],
            })

        return json.dumps({
            "status": "success",
            "days": days,
            "summary": resumen,
            "cases_count": len(casos),
            "cases": casos,
        })
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

# ==========================================
# 4. HERRAMIENTAS MCP (ESCRITURA)
# ==========================================

@mcp.tool()
def create_fraud_case(transaccion_id: int, reason: str, severity: str, justificacion: str) -> str:
    """
    Abre un caso de investigación de fraude para una transacción sospechosa.
    Solo puede usarse para ALERTAR, no modifica la transacción original.
    
    Args:
        transaccion_id (int): ID de la transacción anómala.
        reason (str): Descripción corta de la anomalía.
        severity (str): Debe ser: BAJA, MEDIA, ALTA o CRITICA.
        justificacion (str): Argumentación profunda de los datos usados para concluir fraude.
    """
    error = validar_justificacion(justificacion)
    if error: return error

    if severity not in ['BAJA', 'MEDIA', 'ALTA', 'CRITICA']:
        return json.dumps({"error": "Severidad inválida. Use: BAJA, MEDIA, ALTA o CRITICA."})

    query = """
        INSERT INTO casos_fraude (transaccion_id, motivo, severidad, estado_caso)
        VALUES (%s, %s, %s, 'ABIERTO')
        RETURNING id;
    """
    
    try:
        conn = obtener_conexion()
        cursor = conn.cursor()
        cursor.execute(query, (transaccion_id, reason, severity))
        caso_id = cursor.fetchone()[0]
        conn.commit()
        
        return json.dumps({
            "status": "success", 
            "message": f"Caso de fraude #{caso_id} creado exitosamente.",
            "justificacion_registrada": justificacion
        })
    except Exception as e:
        return json.dumps({"error": str(e)})
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

# ==========================================
# 5. INICIO DEL SERVIDOR
# ==========================================
if __name__ == "__main__":
    # Inicia el servidor usando los canales de texto estándar (stdio)
    mcp.run()
