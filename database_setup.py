import sqlite3

# Nombre del archivo de la base de datos
DB_NAME = "pvd_database.db"

# Conectarse a la base de datos (se creará si no existe)
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# --- Crear la tabla de Equipos ---
# Contiene todo el inventario, tanto asignable como no asignable.
cursor.execute("""
CREATE TABLE IF NOT EXISTS equipos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    tipo TEXT NOT NULL,
    numero_serie TEXT,
    estado TEXT NOT NULL DEFAULT 'Disponible', 
    cantidad INTEGER NOT NULL DEFAULT 1,
    es_asignable INTEGER NOT NULL DEFAULT 0 -- 0 para No, 1 para Sí
);
""")
print("Tabla 'equipos' creada o ya existente.")

# --- Crear la tabla de Reservas del Recinto ---
# Para agendar el uso del espacio físico.
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

# --- Crear la tabla de Sesiones ---
# Un registro de cada vez que se presta un equipo asignable.
cursor.execute("""
CREATE TABLE IF NOT EXISTS sesiones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipo_id INTEGER NOT NULL,
    usuario_temporal TEXT NOT NULL,
    hora_inicio TEXT NOT NULL,
    hora_fin TEXT,
    hora_fin_timestamp REAL,
    FOREIGN KEY (equipo_id) REFERENCES equipos (id)
);
""")
print("Tabla 'sesiones' creada o ya existente.")

# --- Crear la tabla de Mantenimientos ---
# Historial de todos los mantenimientos realizados.
cursor.execute("""
CREATE TABLE IF NOT EXISTS mantenimientos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipo_id INTEGER NOT NULL,
    fecha_inicio TEXT NOT NULL,
    fecha_fin TEXT,
    descripcion TEXT NOT NULL,
    FOREIGN KEY (equipo_id) REFERENCES equipos (id)
);
""")
print("Tabla 'mantenimientos' creada o ya existente.")


# Guardar los cambios (commit) y cerrar la conexión
conn.commit()
conn.close()

print(f"\n¡Base de datos '{DB_NAME}' configurada exitosamente!")