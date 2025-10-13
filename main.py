import customtkinter as ctk
import database_manager as db
import sqlite3
from datetime import datetime
from PIL import Image
from tkcalendar import DateEntry
from tkinter import messagebox, filedialog
import webbrowser
import os
import json
from weasyprint import HTML

RUTA_COMANDOS = r"C:\PVD_Comandos"

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# --- Ventana para Añadir/Editar Equipo ---
class EquipoDialog(ctk.CTkToplevel):
    def __init__(self, parent, equipo=None):
        super().__init__(parent)
        self.parent = parent
        self.equipo = equipo

        self.title("Editar Equipo" if self.equipo else "Añadir Nuevo Equipo")
        self.geometry("400x250")
        self.transient(parent)
        self.grab_set()

        ctk.CTkLabel(self, text="Nombre del Equipo:").pack(pady=(10,0))
        self.nombre_entry = ctk.CTkEntry(self, placeholder_text="Ej: PC-04")
        self.nombre_entry.pack(padx=20, fill="x")

        ctk.CTkLabel(self, text="Tipo de Equipo:").pack(pady=(10,0))
        self.tipo_combo = ctk.CTkComboBox(self, values=["Escritorio", "Portátil", "Tablet", "Otro"])
        self.tipo_combo.pack(padx=20, fill="x")

        ctk.CTkLabel(self, text="Número de Serie (Opcional):").pack(pady=(10,0))
        self.serie_entry = ctk.CTkEntry(self)
        self.serie_entry.pack(padx=20, fill="x")
        
        if self.equipo:
            self.nombre_entry.insert(0, self.equipo["nombre"])
            self.tipo_combo.set(self.equipo["tipo"])
            self.serie_entry.insert(0, self.equipo["numero_serie"])

        self.save_button = ctk.CTkButton(self, text="Guardar Equipo", command=self.guardar)
        self.save_button.pack(pady=20)

    def guardar(self):
        nombre, tipo, serie = self.nombre_entry.get(), self.tipo_combo.get(), self.serie_entry.get()
        if not nombre or not tipo:
            messagebox.showerror("Error", "El nombre y el tipo son obligatorios.")
            return

        if self.equipo:
            db.update_equipo(self.equipo["id"], nombre, tipo, serie)
        else:
            db.add_equipo(nombre, tipo, serie)

        self.parent.cargar_vista_sesiones()
        self.destroy()

# --- Clase AsignarSesionDialog (sin cambios) ---
class AsignarSesionDialog(ctk.CTkToplevel):
    def __init__(self, parent, equipo_id, equipo_nombre):
        super().__init__(parent)
        self.parent = parent
        self.equipo_id = equipo_id
        self.title(f"Asignar: {equipo_nombre}")
        self.geometry("450x200")
        self.transient(parent)
        self.grab_set()
        self.label_usuario = ctk.CTkLabel(self, text="Nombre del Usuario Temporal:")
        self.label_usuario.pack(pady=(10, 0))
        self.usuario_entry = ctk.CTkEntry(self, placeholder_text="Ej: Juan Pérez")
        self.usuario_entry.pack(padx=20, pady=5, fill="x")
        self.usuario_entry.focus()
        self.label_duracion = ctk.CTkLabel(self, text="Seleccione la Duración:")
        self.label_duracion.pack(pady=(15, 5))
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=10)
        button_30m = ctk.CTkButton(button_frame, text="30 Minutos", width=100, command=lambda: self.confirmar(30))
        button_30m.grid(row=0, column=0, padx=5)
        button_60m = ctk.CTkButton(button_frame, text="1 Hora", width=100, command=lambda: self.confirmar(60))
        button_60m.grid(row=0, column=1, padx=5)
        button_120m = ctk.CTkButton(button_frame, text="2 Horas", width=100, command=lambda: self.confirmar(120))
        button_120m.grid(row=0, column=2, padx=5)
        button_libre = ctk.CTkButton(button_frame, text="Tiempo Libre", width=100, fg_color="#5a2d82", hover_color="#4a1f6e", command=lambda: self.confirmar(None))
        button_libre.grid(row=0, column=3, padx=5)

    def confirmar(self, duracion_minutos):
        usuario = self.usuario_entry.get()
        if not usuario:
            self.label_usuario.configure(text="¡El nombre no puede estar vacío!", text_color="red")
            return
        self.parent.iniciar_sesion_remota(self.equipo_id, usuario, duracion_minutos)
        self.parent.cargar_vista_sesiones()
        self.destroy()
        
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Sistema de Gestión PVD")
        self.geometry("1200x600")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.timer_labels = {}
        self.reserva_en_edicion_id = None
        
        self.laptop_icon = ctk.CTkImage(Image.open("assets/laptop_icon.png"), size=(64, 64))
        # --- Sidebar ---
        self.sidebar_frame = ctk.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Sistema PVD", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        self.sesiones_button = ctk.CTkButton(self.sidebar_frame, text="Control de Sesiones", command=lambda: self.select_frame_by_name("sesiones"))
        self.sesiones_button.grid(row=1, column=0, padx=20, pady=10)
        self.reservas_button = ctk.CTkButton(self.sidebar_frame, text="Reservas del Recinto", command=lambda: self.select_frame_by_name("reservas"))
        self.reservas_button.grid(row=2, column=0, padx=20, pady=10)
        self.reportes_button = ctk.CTkButton(self.sidebar_frame, text="Generar Reportes", command=lambda: self.select_frame_by_name("reportes"))
        self.reportes_button.grid(row=3, column=0, padx=20, pady=10)
        self.sesiones_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.reservas_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.reportes_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.select_frame_by_name("sesiones")
        self.update_timers()
        
    def select_frame_by_name(self, name):
        for frame in [self.sesiones_frame, self.reservas_frame, self.reportes_frame]:
            frame.grid_remove()
        if name == "sesiones":
            self.sesiones_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
            self.cargar_vista_sesiones()
        elif name == "reservas":
            self.reservas_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
            self.cargar_vista_reservas()
        elif name == "reportes":
            self.reportes_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
            self.cargar_vista_reportes()
            
    def cargar_vista_sesiones(self):
        for widget in self.sesiones_frame.winfo_children():
            widget.destroy()
        self.timer_labels.clear()
        
        add_button_frame = ctk.CTkFrame(self.sesiones_frame, fg_color="transparent")
        add_button_frame.pack(fill="x", pady=(0, 10))
        add_equipo_button = ctk.CTkButton(add_button_frame, text="➕ Añadir Nuevo Equipo", command=self.abrir_dialogo_equipo)
        add_equipo_button.pack(side="right")
        
        scrollable_frame = ctk.CTkScrollableFrame(self.sesiones_frame, fg_color="transparent")
        scrollable_frame.pack(fill="both", expand=True)
        scrollable_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        equipos = db.get_all_equipos()

        if not equipos:
            # --- LÍNEA CORREGIDA ---
            label = ctk.CTkLabel(scrollable_frame, text="No hay equipos registrados. Haz clic en 'Añadir Nuevo Equipo' para comenzar.")
            label.grid(row=0, column=0, columnspan=4, pady=20) # Usamos grid en lugar de pack
            return

        row_num, col_num = 0, 0
        for equipo in equipos:
            border_color = "gray25"
            if equipo["estado"] == "En Uso": border_color = "#3b8ed0"
            elif equipo["estado"] == "Mantenimiento": border_color = "#f57d00"
            
            card = ctk.CTkFrame(scrollable_frame, border_width=2, border_color=border_color)
            card.grid(row=row_num, column=col_num, padx=10, pady=10, sticky="nsew")

            options_frame = ctk.CTkFrame(card, fg_color="transparent")
            options_frame.pack(fill="x", padx=5, pady=5)
            delete_button = ctk.CTkButton(options_frame, text="❌", width=20, fg_color="transparent", hover_color="gray20", command=lambda eid=equipo["id"]: self.eliminar_equipo(eid))
            delete_button.pack(side="right")
            edit_button = ctk.CTkButton(options_frame, text="✏️", width=20, fg_color="transparent", hover_color="gray20", command=lambda e=equipo: self.abrir_dialogo_equipo(e))
            edit_button.pack(side="right", padx=5)
            
            icon_label = ctk.CTkLabel(card, image=self.laptop_icon, text="")
            icon_label.pack(pady=(0, 0))
            equipo_nombre = ctk.CTkLabel(card, text=equipo["nombre"], font=ctk.CTkFont(size=18, weight="bold"))
            equipo_nombre.pack(pady=(5, 5), padx=10)

            if equipo["estado"] == "En Uso":
                conn = db.conectar_db()
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM sesiones WHERE equipo_id = ? AND hora_fin IS NULL", (equipo["id"],))
                sesion_activa = cursor.fetchone()
                conn.close()
                usuario = sesion_activa['usuario_temporal'] if sesion_activa else "Error"
                sesion_id = sesion_activa['id'] if sesion_activa else None
                ctk.CTkLabel(card, text=f"USUARIO: {usuario}", font=ctk.CTkFont(size=12)).pack(pady=2, padx=10)
                if sesion_activa and sesion_activa['hora_fin_estimada']:
                    timer_label = ctk.CTkLabel(card, text="--:--:--", font=ctk.CTkFont(size=20, weight="bold"))
                    timer_label.pack(pady=5, padx=10)
                    self.timer_labels[sesion_id] = timer_label
                else:
                    ctk.CTkLabel(card, text="TIEMPO: Sin Límite", font=ctk.CTkFont(slant="italic")).pack(pady=5, padx=10)
                ctk.CTkLabel(card, text=f"ESTADO: {equipo['estado']}", font=ctk.CTkFont(size=12)).pack(pady=2, padx=10)
                action_button = ctk.CTkButton(card, text="Liberar", fg_color="red", command=lambda sid=sesion_id, eid=equipo["id"]: self.liberar_equipo(sid, eid))
                action_button.pack(pady=10, padx=10)
            else: 
                ctk.CTkLabel(card, text="USUARIO: N/A", font=ctk.CTkFont(size=12)).pack(pady=2, padx=10)
                ctk.CTkLabel(card, text="TIEMPO: N/A", font=ctk.CTkFont(size=12)).pack(pady=5, padx=10)
                ctk.CTkLabel(card, text=f"ESTADO: {equipo['estado']}", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=2, padx=10)
                action_button = ctk.CTkButton(card, text="Asignar", command=lambda eid=equipo["id"], nom=equipo["nombre"]: self.abrir_dialogo_asignar(eid, nom))
                action_button.pack(pady=10, padx=10)

            col_num += 1
            if col_num > 3:
                col_num, row_num = 0, row_num + 1

    # --- CRUD de Equipos ---
    def abrir_dialogo_equipo(self, equipo=None):
        dialog = EquipoDialog(self, equipo)

    def eliminar_equipo(self, equipo_id):
        equipo = next((e for e in db.get_all_equipos() if e['id'] == equipo_id), None)
        if equipo and equipo['estado'] == 'En Uso':
            messagebox.showerror("Error", "No se puede eliminar un equipo que está en uso.")
            return
        if messagebox.askyesno("Confirmar Eliminación", f"¿Estás seguro de que quieres eliminar el equipo?"):
            db.delete_equipo(equipo_id)
            self.cargar_vista_sesiones()

    # --- CRUD de Reservas y otras funciones (sin cambios) ---
    # ...
    def cargar_vista_reservas(self):
        for widget in self.reservas_frame.winfo_children():
            widget.destroy()
        self.form_frame = ctk.CTkFrame(self.reservas_frame)
        self.form_frame.pack(fill="x", padx=10, pady=10)
        self.form_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.form_frame, text="Entidad:", anchor="w").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.reserva_entidad_entry = ctk.CTkEntry(self.form_frame, placeholder_text="Ej: Alcaldía Local")
        self.reserva_entidad_entry.grid(row=0, column=1, columnspan=3, padx=10, pady=5, sticky="ew")
        ctk.CTkLabel(self.form_frame, text="Motivo:", anchor="w").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.reserva_motivo_entry = ctk.CTkEntry(self.form_frame, placeholder_text="Ej: Reunión comunal")
        self.reserva_motivo_entry.grid(row=1, column=1, columnspan=3, padx=10, pady=5, sticky="ew")
        horas, minutos = [f"{h:02d}" for h in range(24)], ["00", "15", "30", "45"]
        ctk.CTkLabel(self.form_frame, text="Fecha Inicio:", anchor="w").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.reserva_inicio_date_entry = DateEntry(self.form_frame, date_pattern='yyyy-mm-dd', width=15)
        self.reserva_inicio_date_entry.grid(row=2, column=1, padx=(10, 0), pady=5, sticky="w")
        self.reserva_inicio_hora_combo = ctk.CTkComboBox(self.form_frame, values=horas, width=70)
        self.reserva_inicio_hora_combo.grid(row=2, column=2, padx=5, pady=5, sticky="w")
        self.reserva_inicio_min_combo = ctk.CTkComboBox(self.form_frame, values=minutos, width=70)
        self.reserva_inicio_min_combo.grid(row=2, column=3, padx=(0, 10), pady=5, sticky="w")
        self.reserva_inicio_hora_combo.set("14")
        self.reserva_inicio_min_combo.set("00")
        ctk.CTkLabel(self.form_frame, text="Fecha Fin:", anchor="w").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.reserva_fin_date_entry = DateEntry(self.form_frame, date_pattern='yyyy-mm-dd', width=15)
        self.reserva_fin_date_entry.grid(row=3, column=1, padx=(10, 0), pady=5, sticky="w")
        self.reserva_fin_hora_combo = ctk.CTkComboBox(self.form_frame, values=horas, width=70)
        self.reserva_fin_hora_combo.grid(row=3, column=2, padx=5, pady=5, sticky="w")
        self.reserva_fin_min_combo = ctk.CTkComboBox(self.form_frame, values=minutos, width=70)
        self.reserva_fin_min_combo.grid(row=3, column=3, padx=(0, 10), pady=5, sticky="w")
        self.reserva_fin_hora_combo.set("16")
        self.reserva_fin_min_combo.set("00")
        self.guardar_reserva_button = ctk.CTkButton(self.form_frame, text="Añadir Reserva", command=self.guardar_reserva)
        self.guardar_reserva_button.grid(row=4, column=2, columnspan=2, padx=10, pady=10, sticky="e")
        self.cancelar_edicion_button = ctk.CTkButton(self.form_frame, text="Cancelar Edición", fg_color="gray50", hover_color="gray30", command=self.cancelar_edicion)
        list_frame = ctk.CTkFrame(self.reservas_frame)
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        headers = ["Entidad", "Motivo", "Inicio", "Fin", "Acciones"]
        for i, header in enumerate(headers):
            label = ctk.CTkLabel(list_frame, text=header, font=ctk.CTkFont(weight="bold"))
            label.grid(row=0, column=i, padx=10, pady=10, sticky="w")
        reservas = db.get_all_reservas()
        for row_num, reserva in enumerate(reservas, start=1):
            ctk.CTkLabel(list_frame, text=reserva["entidad"]).grid(row=row_num, column=0, padx=10, pady=5, sticky="w")
            ctk.CTkLabel(list_frame, text=reserva["motivo"]).grid(row=row_num, column=1, padx=10, pady=5, sticky="w")
            ctk.CTkLabel(list_frame, text=reserva["fecha_inicio"]).grid(row=row_num, column=2, padx=10, pady=5, sticky="w")
            ctk.CTkLabel(list_frame, text=reserva["fecha_fin"]).grid(row=row_num, column=3, padx=10, pady=5, sticky="w")
            actions_frame = ctk.CTkFrame(list_frame, fg_color="transparent")
            actions_frame.grid(row=row_num, column=4, padx=5, pady=5)
            edit_button = ctk.CTkButton(actions_frame, text="Editar", width=60, command=lambda r=reserva: self.editar_reserva(r))
            edit_button.pack(side="left", padx=5)
            delete_button = ctk.CTkButton(actions_frame, text="Eliminar", width=60, fg_color="red", command=lambda rid=reserva["id"]: self.eliminar_reserva(rid))
            delete_button.pack(side="left")
        self.cancelar_edicion()
    def guardar_reserva(self):
        entidad = self.reserva_entidad_entry.get()
        motivo = self.reserva_motivo_entry.get()
        inicio = f"{self.reserva_inicio_date_entry.get()} {self.reserva_inicio_hora_combo.get()}:{self.reserva_inicio_min_combo.get()}"
        fin = f"{self.reserva_fin_date_entry.get()} {self.reserva_fin_hora_combo.get()}:{self.reserva_fin_min_combo.get()}"
        if not entidad:
            messagebox.showerror("Error de Validación", "El campo 'Entidad' no puede estar vacío.")
            return
        if self.reserva_en_edicion_id is None:
            db.add_reserva(entidad, motivo, inicio, fin)
        else:
            db.update_reserva(self.reserva_en_edicion_id, entidad, motivo, inicio, fin)
        self.cargar_vista_reservas()
    def editar_reserva(self, reserva):
        self.reserva_en_edicion_id = reserva["id"]
        self.reserva_entidad_entry.delete(0, 'end'); self.reserva_entidad_entry.insert(0, reserva["entidad"])
        self.reserva_motivo_entry.delete(0, 'end'); self.reserva_motivo_entry.insert(0, reserva["motivo"])
        try:
            fecha_inicio, hora_inicio = reserva["fecha_inicio"].split()
            hora_i, min_i = hora_inicio.split(":")
            self.reserva_inicio_date_entry.set_date(fecha_inicio)
            self.reserva_inicio_hora_combo.set(hora_i)
            self.reserva_inicio_min_combo.set(min_i)
            fecha_fin, hora_fin = reserva["fecha_fin"].split()
            hora_f, min_f = hora_fin.split(":")
            self.reserva_fin_date_entry.set_date(fecha_fin)
            self.reserva_fin_hora_combo.set(hora_f)
            self.reserva_fin_min_combo.set(min_f)
        except Exception as e:
            print(f"Error al parsear fecha/hora para editar: {e}")
        self.guardar_reserva_button.configure(text="Actualizar Reserva")
        self.cancelar_edicion_button.grid(row=4, column=1, padx=10, pady=10, sticky="e")
    def eliminar_reserva(self, reserva_id):
        if messagebox.askyesno("Confirmar Eliminación", "¿Estás seguro de que quieres eliminar esta reserva?"):
            db.delete_reserva(reserva_id)
            self.cargar_vista_reservas()
    def cancelar_edicion(self):
        self.reserva_en_edicion_id = None
        self.reserva_entidad_entry.delete(0, 'end')
        self.reserva_motivo_entry.delete(0, 'end')
        self.guardar_reserva_button.configure(text="Añadir Reserva")
        self.cancelar_edicion_button.grid_remove()
    def abrir_dialogo_asignar(self, equipo_id, equipo_nombre):
        dialog = AsignarSesionDialog(self, equipo_id, equipo_nombre)
    def iniciar_sesion_remota(self, equipo_id, usuario, duracion_minutos):
        db.iniciar_sesion(equipo_id, usuario, duracion_minutos)
        equipo = next((e for e in db.get_all_equipos() if e['id'] == equipo_id), None)
        if not equipo: return
        ruta_archivo_comando = os.path.join(RUTA_COMANDOS, f"{equipo['nombre']}.json")
        comando = {"estado": "activo"}
        if duracion_minutos is not None:
            hora_fin_timestamp = datetime.now().timestamp() + (duracion_minutos * 60)
            comando["hora_fin_timestamp"] = hora_fin_timestamp
        try:
            with open(ruta_archivo_comando, 'w') as f:
                json.dump(comando, f)
        except Exception as e:
            messagebox.showerror("Error de Red", f"No se pudo escribir el archivo de comando.\nError: {e}")
    def liberar_equipo(self, sesion_id, equipo_id):
        if sesion_id:
            db.liberar_sesion(sesion_id, equipo_id)
            equipo = next((e for e in db.get_all_equipos() if e['id'] == equipo_id), None)
            if equipo:
                ruta_archivo_comando = os.path.join(RUTA_COMANDOS, f"{equipo['nombre']}.json")
                if os.path.exists(ruta_archivo_comando):
                    try:
                        os.remove(ruta_archivo_comando)
                    except Exception as e:
                        print(f"No se pudo borrar el archivo de comando: {e}")
            self.cargar_vista_sesiones()
    def update_timers(self):
        conn = db.conectar_db()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, hora_fin_estimada FROM sesiones WHERE hora_fin IS NULL AND hora_fin_estimada IS NOT NULL")
        sesiones_activas = cursor.fetchall()
        conn.close()
        for sesion in sesiones_activas:
            sesion_id = sesion['id']
            if sesion_id in self.timer_labels:
                hora_fin_estimada_str = sesion['hora_fin_estimada']
                try:
                    hora_fin_dt = datetime.strptime(hora_fin_estimada_str, "%Y-%m-%d %H:%M:%S")
                    tiempo_restante = hora_fin_dt - datetime.now()
                    if tiempo_restante.total_seconds() > 0:
                        horas, rem = divmod(tiempo_restante.seconds, 3600)
                        minutos, segundos = divmod(rem, 60)
                        self.timer_labels[sesion_id].configure(text=f"TIEMPO: {horas:02d}:{minutos:02d}:{segundos:02d}")
                    else:
                        self.timer_labels[sesion_id].configure(text="¡TIEMPO AGOTADO!", text_color="orange red")
                except (ValueError, TypeError):
                     self.timer_labels[sesion_id].configure(text="Error de formato")
        self.after(1000, self.update_timers)
    def cargar_vista_reportes(self):
        for widget in self.reportes_frame.winfo_children():
            widget.destroy()
        report_frame = ctk.CTkFrame(self.reportes_frame)
        report_frame.pack(padx=10, pady=10, fill="x")
        ctk.CTkLabel(report_frame, text="Reporte de Historial de Uso de Equipos", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(5,10))
        ctk.CTkButton(report_frame, text="📄 Generar PDF", command=self.generar_reporte_sesiones).pack(pady=10)
    def generar_reporte_sesiones(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("Archivos PDF", "*.pdf")], title="Guardar reporte como...")
        if not filepath: return
        sesiones = db.get_completed_sessions()
        if not sesiones:
            messagebox.showinfo("Reporte Vacío", "No hay sesiones completadas.")
            return
        html = "<html><head><style>body { font-family: sans-serif; } table { border-collapse: collapse; width: 100%; } th, td { border: 1px solid #ddd; text-align: left; padding: 8px; } tr:nth-child(even) { background-color: #f2f2f2; } th { background-color: #4CAF50; color: white; }</style></head><body>"
        html += f"<h1>Reporte de Uso de Equipos</h1><p>Generado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>"
        html += "<table><tr><th>Equipo</th><th>Usuario</th><th>Inicio</th><th>Fin</th><th>Duración</th></tr>"
        for s in sesiones:
            try:
                inicio = datetime.strptime(s['hora_inicio'], '%Y-%m-%d %H:%M:%S')
                fin = datetime.strptime(s['hora_fin'], '%Y-%m-%d %H:%M:%S')
                duracion = fin - inicio
                total_seconds = int(duracion.total_seconds())
                horas, rem = divmod(total_seconds, 3600)
                minutos, segundos = divmod(rem, 60)
                duracion_str = f"{horas:02d}:{minutos:02d}:{segundos:02d}"
            except (ValueError, TypeError):
                duracion_str = "N/A"
            html += f"<tr><td>{s['equipo_nombre']}</td><td>{s['usuario_temporal']}</td><td>{s['hora_inicio']}</td><td>{s['hora_fin']}</td><td>{duracion_str}</td></tr>"
        html += "</table></body></html>"
        try:
            HTML(string=html).write_pdf(filepath)
            messagebox.showinfo("Éxito", f"Reporte guardado en:\n{filepath}")
            if messagebox.askyesno("Abrir Reporte", "¿Deseas abrir el reporte ahora?"):
                if os.name == 'nt':
                    os.startfile(filepath)
                else:
                    webbrowser.open(f'file://{os.path.realpath(filepath)}')
        except Exception as e:
            messagebox.showerror("Error al Generar PDF", f"Ocurrió un error: {e}")

if __name__ == "__main__":
    # Remove the automatic creation of example teams
    app = App()
    app.mainloop()