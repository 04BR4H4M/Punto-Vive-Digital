import sqlite3
from datetime import datetime, timedelta

DB_NAME = "pvd_database.db"

def conectar_db():
    conn = sqlite3.connect(DB_NAME)
    return conn

# --- FUNCIONES PARA EQUIPOS (ACTUALIZADAS) ---
def add_equipo(nombre, tipo, numero_serie=""):
    conn = conectar_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO equipos (nombre, tipo, numero_serie) VALUES (?, ?, ?)", (nombre, tipo, numero_serie))
        conn.commit()
    except sqlite3.IntegrityError:
        print(f"Error: El equipo con el nombre '{nombre}' ya existe.")
    finally:
        conn.close()

def get_all_equipos():
    conn = conectar_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM equipos ORDER BY nombre ASC")
    equipos = cursor.fetchall()
    conn.close()
    return equipos

def update_equipo_estado(equipo_id, nuevo_estado):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE equipos SET estado = ? WHERE id = ?", (nuevo_estado, equipo_id))
    conn.commit()
    conn.close()

# --- NUEVAS FUNCIONES ---
def update_equipo(equipo_id, nombre, tipo, numero_serie):
    """Actualiza los datos de un equipo existente."""
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE equipos SET nombre = ?, tipo = ?, numero_serie = ?
        WHERE id = ?
    """, (nombre, tipo, numero_serie, equipo_id))
    conn.commit()
    conn.close()

def delete_equipo(equipo_id):
    """Elimina un equipo de la base de datos."""
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM equipos WHERE id = ?", (equipo_id,))
    conn.commit()
    conn.close()

# --- FUNCIONES PARA SESIONES, RESERVAS Y REPORTES (sin cambios) ---
# ... (El resto del archivo no cambia)
def iniciar_sesion(equipo_id, usuario_temporal, duracion_minutos=None):
    hora_inicio_dt = datetime.now()
    hora_inicio_str = hora_inicio_dt.strftime("%Y-%m-%d %H:%M:%S")
    hora_fin_estimada_str = None
    if duracion_minutos is not None:
        hora_fin_estimada_dt = hora_inicio_dt + timedelta(minutes=duracion_minutos)
        hora_fin_estimada_str = hora_fin_estimada_dt.strftime("%Y-%m-%d %H:%M:%S")
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO sesiones (equipo_id, usuario_temporal, hora_inicio, hora_fin_estimada) VALUES (?, ?, ?, ?)", (equipo_id, usuario_temporal, hora_inicio_str, hora_fin_estimada_str))
    conn.commit()
    sesion_id = cursor.lastrowid
    conn.close()
    update_equipo_estado(equipo_id, "En Uso")
    return sesion_id
def liberar_sesion(sesion_id, equipo_id):
    hora_fin = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE sesiones SET hora_fin = ? WHERE id = ?", (hora_fin, sesion_id))
    conn.commit()
    conn.close()
    update_equipo_estado(equipo_id, "Disponible")
def add_reserva(entidad, motivo, fecha_inicio, fecha_fin):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO reservas (entidad, motivo, fecha_inicio, fecha_fin) VALUES (?, ?, ?, ?)", (entidad, motivo, fecha_inicio, fecha_fin))
    conn.commit()
    conn.close()
def get_all_reservas():
    conn = conectar_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reservas ORDER BY fecha_inicio DESC")
    reservas = cursor.fetchall()
    conn.close()
    return reservas
def update_reserva(reserva_id, entidad, motivo, fecha_inicio, fecha_fin):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE reservas SET entidad = ?, motivo = ?, fecha_inicio = ?, fecha_fin = ? WHERE id = ?", (entidad, motivo, fecha_inicio, fecha_fin, reserva_id))
    conn.commit()
    conn.close()
def delete_reserva(reserva_id):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reservas WHERE id = ?", (reserva_id,))
    conn.commit()
    conn.close()
def get_completed_sessions():
    conn = conectar_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            s.usuario_temporal,
            s.hora_inicio,
            s.hora_fin,
            e.nombre AS equipo_nombre
        FROM sesiones s
        JOIN equipos e ON s.equipo_id = e.id
        WHERE s.hora_fin IS NOT NULL
        ORDER BY s.hora_inicio DESC
    """)
    sesiones = cursor.fetchall()
    conn.close()
    return sesiones