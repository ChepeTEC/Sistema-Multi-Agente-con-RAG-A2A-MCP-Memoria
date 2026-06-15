import os
import psycopg2
from faker import Faker
import random
from datetime import datetime, timedelta

# Inicializamos Faker para generar datos realistas en español
fake = Faker('es_ES')

# Configuración de conexión leyendo variables de entorno (ideal para Docker)
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME', 'mcp_db'),
    'user': os.getenv('DB_USER', 'admin'),
    'password': os.getenv('DB_PASSWORD', 'password'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432')
}

# Esquema completo de la base de datos
SQL_CREACION = ""
with open('./CREAR_TABLAS.sql', 'r') as f:
    SQL_CREACION = f.read()

def generar_datos_ficticios(cursor):
    print("Generando clientes y cuentas ficticias...")
    clientes_ids = []
    cuentas_ids = []
    
    # 1. Crear 10 Clientes (Mezclando niveles de riesgo)
    for _ in range(10):
        riesgo = random.choices(['BAJO', 'MEDIO', 'ALTO'], weights=[70, 20, 10])[0]
        cursor.execute(
            """INSERT INTO clientes (nombre, identificacion, pais_residencia, nivel_riesgo)
               VALUES (%s, %s, %s, %s) RETURNING id;""",
            (fake.name(), fake.unique.ssn(), fake.country(), riesgo)
        )
        cliente_id = cursor.fetchone()[0]
        clientes_ids.append(cliente_id)

        # 2. Crear 1 o 2 cuentas por cliente
        for _ in range(random.randint(1, 2)):
            tipo_cuenta = random.choice(['AHORRO', 'CORRIENTE', 'TARJETA_CREDITO'])
            cursor.execute(
                """INSERT INTO cuentas (cliente_id, numero_cuenta, tipo_cuenta, saldo)
                   VALUES (%s, %s, %s, %s) RETURNING id;""",
                (cliente_id, fake.unique.iban(), tipo_cuenta, round(random.uniform(500, 10000), 2))
            )
            cuentas_ids.append(cursor.fetchone()[0])

    print("Generando transacciones normales...")
    
    # 3. Generar Transacciones Normales
    for cuenta_id in cuentas_ids:
        for _ in range(random.randint(5, 10)):
            cursor.execute(
                """INSERT INTO transacciones (cuenta_id, monto, tipo, fecha_hora, pais_origen, estado, comercio_o_destino)
                   VALUES (%s, %s, %s, %s, %s, %s, %s);""",
                (cuenta_id, round(random.uniform(10, 300), 2), 'COMPRA', fake.date_time_this_month(), 
                 'Costa Rica', 'APROBADA', fake.company())
            )

    print("Generando casos sospechosos requeridos por la rúbrica...")
    cuenta_victima = random.choice(cuentas_ids)
    fecha_base = fake.date_time_this_month()
    
    # Caso A: Transacciones en países distintos durante el mismo día
    cursor.execute(
        """INSERT INTO transacciones (cuenta_id, monto, tipo, fecha_hora, pais_origen, estado, comercio_o_destino)
           VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;""",
        (cuenta_victima, 50.00, 'COMPRA', fecha_base, 'Costa Rica', 'APROBADA', 'Supermercado Local')
    )
    cursor.execute(
        """INSERT INTO transacciones (cuenta_id, monto, tipo, fecha_hora, pais_origen, estado, comercio_o_destino)
           VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;""",
        (cuenta_victima, 800.00, 'COMPRA', fecha_base + timedelta(hours=2), 'Rusia', 'APROBADA', 'Tienda Electrónica')
    )
    tx_sospechosa_1 = cursor.fetchone()[0]

    # Caso B: Transacciones de madrugada (Ej. 3:15 AM)
    cursor.execute(
        """INSERT INTO transacciones (cuenta_id, monto, tipo, fecha_hora, pais_origen, estado, comercio_o_destino)
           VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id;""",
        (random.choice(cuentas_ids), 1200.00, 'RETIRO', fecha_base.replace(hour=3, minute=15), 'Costa Rica', 'APROBADA', 'Cajero Automático')
    )
    tx_sospechosa_2 = cursor.fetchone()[0]

    # Caso C: Transacciones fallidas seguidas por aprobadas (Fuerza bruta)
    cuenta_ataque = random.choice(cuentas_ids)
    fecha_ataque = fake.date_time_this_month()
    for m in range(3): # 3 intentos fallidos
        cursor.execute(
            "INSERT INTO transacciones (cuenta_id, monto, tipo, fecha_hora, pais_origen, estado, comercio_o_destino) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (cuenta_ataque, 500.00, 'COMPRA', fecha_ataque + timedelta(minutes=m), 'Brasil', 'FALLIDA', 'Casino Online')
        )
    # Finalmente una aprobada
    cursor.execute(
        "INSERT INTO transacciones (cuenta_id, monto, tipo, fecha_hora, pais_origen, estado, comercio_o_destino) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (cuenta_ataque, 500.00, 'COMPRA', fecha_ataque + timedelta(minutes=4), 'Brasil', 'APROBADA', 'Casino Online')
    )
    tx_sospechosa_3 = cursor.fetchone()[0]

    print("Registrando casos de fraude y reglas de MCP...")
    # 4. Insertar Casos de Fraude pre-creados
    casos = [
        (tx_sospechosa_1, "Transacción internacional en tiempo imposible respecto a compra anterior", "ALTA"),
        (tx_sospechosa_2, "Retiro inusualmente alto de madrugada", "MEDIA"),
        (tx_sospechosa_3, "Múltiples intentos fallidos seguidos de aprobación (posible robo de credenciales)", "CRITICA")
    ]
    
    for tx_id, motivo, severidad in casos:
        cursor.execute(
            "INSERT INTO casos_fraude (transaccion_id, motivo, severidad, estado_caso) VALUES (%s, %s, %s, %s)",
            (tx_id, motivo, severidad, 'INVESTIGACION')
        )

    # 5. Llenar reglas de herramientas
    cursor.execute("""
        INSERT INTO reglas_herramientas (nombre_herramienta, descripcion, restricciones) VALUES 
        ('search_transactions', 'Busca transacciones de un usuario', 'No mostrar cuenta completa. Máximo 50 filas.'),
        ('create_fraud_case', 'Crea un ticket de revisión', 'Requiere justificación válida y severidad clara.')
    """)

def inicializar_base_datos():
    conn = None
    cursor = None
    try:
        print(f"Conectando a la base de datos en {DB_CONFIG['host']}...")
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 1. Ejecutar la creación de tablas
        print("Verificando/Creando tablas en el esquema...")
        cursor.execute(SQL_CREACION)
        conn.commit()

        # 2. Verificar si ya hay datos (para no duplicar si se ejecuta varias veces)
        cursor.execute("SELECT COUNT(*) FROM clientes;")
        cantidad_clientes = cursor.fetchone()[0]

        if cantidad_clientes > 0:
            print(f"La base de datos ya contiene {cantidad_clientes} clientes. Omitiendo generación de datos ficticios.")
        else:
            print("La base de datos está vacía. Procediendo a generar datos ficticios...")
            generar_datos_ficticios(cursor)
            conn.commit()
            print("¡Proceso completado con éxito!")

    except Exception as e:
        print(f"Error operando la base de datos: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    inicializar_base_datos()