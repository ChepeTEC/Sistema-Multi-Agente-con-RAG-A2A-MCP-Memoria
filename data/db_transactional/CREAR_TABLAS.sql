-- 1. Tabla de Clientes Ficticios
CREATE TABLE
    IF NOT EXISTS clientes (
        id SERIAL PRIMARY KEY,
        nombre VARCHAR(100) NOT NULL,
        identificacion VARCHAR(50) UNIQUE NOT NULL,
        pais_residencia VARCHAR(50) NOT NULL,
        nivel_riesgo VARCHAR(20) CHECK (nivel_riesgo IN ('BAJO', 'MEDIO', 'ALTO')) NOT NULL,
        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

-- 2. Tabla de Cuentas Ficticias
CREATE TABLE
    IF NOT EXISTS cuentas (
        id SERIAL PRIMARY KEY,
        cliente_id INTEGER REFERENCES clientes (id) ON DELETE CASCADE,
        numero_cuenta VARCHAR(50) UNIQUE NOT NULL,
        tipo_cuenta VARCHAR(30) CHECK (
            tipo_cuenta IN ('AHORRO', 'CORRIENTE', 'TARJETA_CREDITO')
        ),
        saldo DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
        estado VARCHAR(20) CHECK (estado IN ('ACTIVA', 'BLOQUEADA', 'CERRADA')) DEFAULT 'ACTIVA'
    );

-- 3. Tabla de Transacciones Ficticias
CREATE TABLE
    IF NOT EXISTS transacciones (
        id SERIAL PRIMARY KEY,
        cuenta_id INTEGER REFERENCES cuentas (id) ON DELETE CASCADE,
        monto DECIMAL(15, 2) NOT NULL,
        tipo VARCHAR(20) CHECK (
            tipo IN ('DEPOSITO', 'RETIRO', 'COMPRA', 'TRANSFERENCIA')
        ),
        fecha_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        pais_origen VARCHAR(50) NOT NULL,
        estado VARCHAR(20) CHECK (estado IN ('APROBADA', 'FALLIDA', 'PENDIENTE')) NOT NULL,
        comercio_o_destino VARCHAR(100)
    );

-- 4. Tabla de Casos de Revisión o Fraude Ficticio
CREATE TABLE IF NOT EXISTS casos_fraude (
        id SERIAL PRIMARY KEY,
        transaccion_id INTEGER REFERENCES transacciones (id) ON DELETE CASCADE,
        motivo VARCHAR(255) NOT NULL,
        severidad VARCHAR(20) CHECK (severidad IN ('BAJA', 'MEDIA', 'ALTA', 'CRITICA')) NOT NULL,
        estado_caso VARCHAR(20) CHECK (
            estado_caso IN ('ABIERTO', 'INVESTIGACION', 'CERRADO')
        ) DEFAULT 'ABIERTO',
        fecha_apertura TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

-- 5. Tabla de Reglas de Uso de Herramientas
CREATE TABLE
    IF NOT EXISTS reglas_herramientas (
        id SERIAL PRIMARY KEY,
        nombre_herramienta VARCHAR(100) UNIQUE NOT NULL,
        descripcion TEXT NOT NULL,
        restricciones TEXT NOT NULL,
        requiere_justificacion BOOLEAN DEFAULT TRUE,
        limite_filas INTEGER DEFAULT 50
    );