import sqlite3

# Nombre del archivo de la base de datos
DB_NAME = "pvd_database.db"

# Conectarse a la base de datos (se creará si no existe)
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# --- Crear la tabla de Equipos ---
cursor.execute("""
CREATE TABLE IF NOT EXISTS equipos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    tipo TEXT NOT NULL,
    numero_serie TEXT,
    estado TEXT NOT NULL DEFAULT 'Disponible' 
);
""")
print("Tabla 'equipos' creada o ya existente.")

# --- Crear la tabla de Reservas del Recinto ---
cursor.execute("""
CREATE TABLE IF NOT EXISTS reservas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entidad TEXT NOT NULL,
    motivo TEXT,
    fecha_inicio TEXT NOT NULL,
    fecha_fin TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'Confirmada'
);
""")
print("Tabla 'reservas' creada o ya existente.")

# --- Crear la tabla de Sesiones (ACTUALIZADA) ---
# Hemos añadido la columna 'hora_fin_estimada'
cursor.execute("""
CREATE TABLE IF NOT EXISTS sesiones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipo_id INTEGER NOT NULL,
    usuario_temporal TEXT NOT NULL,
    hora_inicio TEXT NOT NULL,
    hora_fin TEXT,
    hora_fin_estimada TEXT, -- <<<--- ESTA ES LA LÍNEA NUEVA
    FOREIGN KEY (equipo_id) REFERENCES equipos (id)
);
""")
print("Tabla 'sesiones' creada o ya existente.")

# Guardar los cambios (commit) y cerrar la conexión
conn.commit()
conn.close()

print(f"\n¡Base de datos '{DB_NAME}' configurada exitosamente!")