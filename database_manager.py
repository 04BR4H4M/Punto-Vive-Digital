import sqlite3
from datetime import datetime, timedelta
from tkinter import messagebox

DB_NAME = "pvd_database.db"

def conectar_db():
    """Crea una conexión a la base de datos."""
    conn = sqlite3.connect(DB_NAME)
    return conn

# --- FUNCIONES PARA EQUIPOS ---
def add_equipo(nombre, tipo, numero_serie="", cantidad=1, es_asignable=0):
    conn = conectar_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO equipos (nombre, tipo, numero_serie, cantidad, es_asignable) VALUES (?, ?, ?, ?, ?)",
                       (nombre, tipo, numero_serie, cantidad, es_asignable))
        conn.commit()
    except sqlite3.IntegrityError:
        messagebox.showerror("Error de Base de Datos", f"El equipo con el nombre '{nombre}' ya existe.")
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

def get_asignable_equipos():
    """Obtiene solo los equipos marcados como asignables para sesiones."""
    conn = conectar_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM equipos WHERE es_asignable = 1 ORDER BY nombre ASC")
    equipos = cursor.fetchall()
    conn.close()
    return equipos

def update_equipo(equipo_id, nombre, tipo, numero_serie, cantidad, es_asignable):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE equipos SET nombre = ?, tipo = ?, numero_serie = ?, cantidad = ?, es_asignable = ?
        WHERE id = ?
    """, (nombre, tipo, numero_serie, cantidad, es_asignable, equipo_id))
    conn.commit()
    conn.close()

def delete_equipo(equipo_id):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM equipos WHERE id = ?", (equipo_id,))
    conn.commit()
    conn.close()

def update_equipo_estado(equipo_id, nuevo_estado):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE equipos SET estado = ? WHERE id = ?", (nuevo_estado, equipo_id))
    conn.commit()
    conn.close()

# --- FUNCIONES PARA SESIONES ---
def iniciar_sesion(equipo_id, usuario_temporal, hora_fin_timestamp=None):
    hora_inicio_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sesiones (equipo_id, usuario_temporal, hora_inicio, hora_fin_timestamp)
        VALUES (?, ?, ?, ?)
    """, (equipo_id, usuario_temporal, hora_inicio_str, hora_fin_timestamp))
    conn.commit()
    sesion_id = cursor.lastrowid
    conn.close()
    update_equipo_estado(equipo_id, "En Uso")
    return sesion_id

def liberar_sesion(sesion_id, equipo_id):
    hora_fin_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE sesiones SET hora_fin = ? WHERE id = ?", (hora_fin_str, sesion_id))
    conn.commit()
    conn.close()
    update_equipo_estado(equipo_id, "Disponible")

# --- FUNCIONES PARA RESERVAS ---
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

# --- FUNCIONES PARA MANTENIMIENTO ---
def iniciar_mantenimiento(equipo_id, descripcion):
    """Inicia un registro de mantenimiento y actualiza el estado del equipo."""
    fecha_inicio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO mantenimientos (equipo_id, fecha_inicio, descripcion)
        VALUES (?, ?, ?)
    """, (equipo_id, fecha_inicio, descripcion))
    conn.commit()
    conn.close()
    update_equipo_estado(equipo_id, "Mantenimiento")

def finalizar_mantenimiento(equipo_id):
    """Finaliza el último mantenimiento activo de un equipo y lo pone disponible."""
    fecha_fin = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE mantenimientos SET fecha_fin = ?
        WHERE equipo_id = ? AND fecha_fin IS NULL
    """, (fecha_fin, equipo_id))
    conn.commit()
    conn.close()
    update_equipo_estado(equipo_id, "Disponible")

def get_mantenimiento_history():
    """Obtiene el historial completo de mantenimientos."""
    conn = conectar_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.*, e.nombre as equipo_nombre
        FROM mantenimientos m
        JOIN equipos e ON m.equipo_id = e.id
        ORDER BY m.fecha_inicio DESC
    """)
    historial = cursor.fetchall()
    conn.close()
    return historial

# --- FUNCIONES PARA REPORTES Y DEPURACIÓN ---
def get_completed_sessions():
    """Obtiene todas las sesiones finalizadas, uniendo el nombre del equipo."""
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

def get_old_records(months=6):
    """Obtiene registros de sesiones, reservas y mantenimientos más antiguos que X meses."""
    conn = conectar_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cutoff_date = (datetime.now() - timedelta(days=months*30)).strftime("%Y-%m-%d %H:%M:%S")
    
    old_sesiones = cursor.execute("SELECT * FROM sesiones WHERE hora_inicio < ?", (cutoff_date,)).fetchall()
    old_reservas = cursor.execute("SELECT * FROM reservas WHERE fecha_inicio < ?", (cutoff_date,)).fetchall()
    old_mantenimientos = cursor.execute("SELECT * FROM mantenimientos WHERE fecha_inicio < ?", (cutoff_date,)).fetchall()
    
    conn.close()
    return old_sesiones, old_reservas, old_mantenimientos

def delete_old_records(months=6):
    """Elimina registros antiguos de la base de datos."""
    conn = conectar_db()
    cursor = conn.cursor()
    cutoff_date = (datetime.now() - timedelta(days=months*30)).strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("DELETE FROM sesiones WHERE hora_inicio < ?", (cutoff_date,))
    cursor.execute("DELETE FROM reservas WHERE fecha_inicio < ?", (cutoff_date,))
    cursor.execute("DELETE FROM mantenimientos WHERE fecha_inicio < ?", (cutoff_date,))
    
    conn.commit()
    conn.close()
    print("Registros antiguos eliminados.")