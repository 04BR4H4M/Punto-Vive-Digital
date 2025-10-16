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
import time

# --- CONFIGURACIÓN ---
# Ruta a la carpeta compartida para los comandos del agente
RUTA_COMANDOS = r"C:\PVD_Comandos"

# --- APARIENCIA DE LA APLICACIÓN ---
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# --- VENTANA DE DIÁLOGO PARA AÑADIR/EDITAR EQUIPO ---
class EquipoDialog(ctk.CTkToplevel):
    def __init__(self, parent, equipo=None):
        super().__init__(parent)
        self.parent = parent
        self.equipo = equipo

        self.title("Editar Ítem de Inventario" if self.equipo else "Añadir Nuevo Ítem")
        self.geometry("400x350")
        self.transient(parent)
        self.grab_set()

        ctk.CTkLabel(self, text="Nombre del Ítem:").pack(pady=(10,0))
        self.nombre_entry = ctk.CTkEntry(self, placeholder_text="Ej: PC-04 o Sillas")
        self.nombre_entry.pack(padx=20, fill="x")
        self.nombre_entry.focus()

        ctk.CTkLabel(self, text="Tipo:").pack(pady=(10,0))
        self.tipo_combo = ctk.CTkComboBox(self, values=["Escritorio", "Portátil", "Tablet", "Silla", "Cargador", "Otro"])
        self.tipo_combo.pack(padx=20, fill="x")

        ctk.CTkLabel(self, text="Número de Serie (Opcional):").pack(pady=(10,0))
        self.serie_entry = ctk.CTkEntry(self)
        self.serie_entry.pack(padx=20, fill="x")

        self.asignable_var = ctk.StringVar(value="off")
        self.asignable_check = ctk.CTkCheckBox(self, text="Asignable para Sesiones (PC/Laptop)",
                                               variable=self.asignable_var, onvalue="on", offvalue="off",
                                               command=self.toggle_cantidad)
        self.asignable_check.pack(pady=10)

        ctk.CTkLabel(self, text="Cantidad:").pack(pady=(10,0))
        self.cantidad_entry = ctk.CTkEntry(self)
        self.cantidad_entry.pack(padx=20, fill="x")
        
        if self.equipo:
            self.nombre_entry.insert(0, self.equipo["nombre"])
            self.tipo_combo.set(self.equipo["tipo"])
            self.serie_entry.insert(0, self.equipo["numero_serie"])
            if self.equipo["es_asignable"] == 1:
                self.asignable_check.select()
            self.cantidad_entry.insert(0, str(self.equipo["cantidad"]))
            self.toggle_cantidad()

        self.save_button = ctk.CTkButton(self, text="Guardar Ítem", command=self.guardar)
        self.save_button.pack(pady=20)

    def toggle_cantidad(self):
        if self.asignable_var.get() == "on":
            self.cantidad_entry.delete(0, 'end')
            self.cantidad_entry.insert(0, "1")
            self.cantidad_entry.configure(state="disabled")
        else:
            self.cantidad_entry.configure(state="normal")

    def guardar(self):
        nombre, tipo, serie = self.nombre_entry.get(), self.tipo_combo.get(), self.serie_entry.get()
        cantidad_str = self.cantidad_entry.get()
        es_asignable_val = 1 if self.asignable_var.get() == "on" else 0

        if not nombre or not tipo or not cantidad_str:
            messagebox.showerror("Error", "Los campos Nombre, Tipo y Cantidad son obligatorios.")
            return
        
        try:
            cantidad_val = int(cantidad_str)
        except ValueError:
            messagebox.showerror("Error", "La cantidad debe ser un número.")
            return

        if self.equipo:
            db.update_equipo(self.equipo["id"], nombre, tipo, serie, cantidad_val, es_asignable_val)
        else:
            db.add_equipo(nombre, tipo, serie, cantidad_val, es_asignable_val)

        self.parent.cargar_vista_inventario()
        self.parent.cargar_vista_sesiones()
        self.destroy()

# --- VENTANA DE DIÁLOGO PARA ASIGNAR SESIÓN ---
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

        button_30m = ctk.CTkButton(button_frame, text="30 Segundos", width=100, command=lambda: self.confirmar(.30))
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

# --- VENTANA DE DIÁLOGO PARA INICIAR MANTENIMIENTO ---
class MantenimientoDialog(ctk.CTkToplevel):
    def __init__(self, parent, equipo_id):
        super().__init__(parent)
        self.parent = parent
        self.equipo_id = equipo_id
        self.title("Iniciar Mantenimiento")
        self.geometry("400x200")
        self.transient(parent)
        self.grab_set()

        ctk.CTkLabel(self, text="Descripción del problema o mantenimiento:").pack(pady=(10,0))
        self.descripcion_entry = ctk.CTkEntry(self, placeholder_text="Ej: Limpieza de ventiladores")
        self.descripcion_entry.pack(padx=20, pady=5, fill="x")
        self.descripcion_entry.focus()
        
        ctk.CTkButton(self, text="Confirmar y Poner en Mantenimiento", command=self.confirmar).pack(pady=20)

    def confirmar(self):
        descripcion = self.descripcion_entry.get()
        if not descripcion:
            messagebox.showerror("Error", "La descripción es obligatoria.")
            return
        db.iniciar_mantenimiento(self.equipo_id, descripcion)
        self.parent.cargar_vista_inventario()
        self.parent.cargar_vista_sesiones()
        self.destroy()
        
# --- CLASE PRINCIPAL DE LA APLICACIÓN ---
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Sistema de Gestión PVD")
        self.geometry("1200x600")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.timer_labels = {}
        self.reserva_en_edicion_id = None
        
        # --- Cargar Imágenes ---
        self.laptop_icon = ctk.CTkImage(Image.open("assets/laptop_icon.png"), size=(64, 64))
        self.pvd_logo = ctk.CTkImage(Image.open("assets/logo.png"), size=(100, 100))
        
        # --- SIDEBAR (MENÚ LATERAL) ---
        self.sidebar_frame = ctk.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=5, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)
        
        self.logo_label_top = ctk.CTkLabel(self.sidebar_frame, text="Sistema PVD", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label_top.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        self.sesiones_button = ctk.CTkButton(self.sidebar_frame, text="Control de Sesiones", command=lambda: self.select_frame_by_name("sesiones"))
        self.sesiones_button.grid(row=1, column=0, padx=20, pady=10)
        
        self.inventario_button = ctk.CTkButton(self.sidebar_frame, text="Inventario", command=lambda: self.select_frame_by_name("inventario"))
        self.inventario_button.grid(row=2, column=0, padx=20, pady=10)
        
        self.reservas_button = ctk.CTkButton(self.sidebar_frame, text="Reservas del Recinto", command=lambda: self.select_frame_by_name("reservas"))
        self.reservas_button.grid(row=3, column=0, padx=20, pady=10)
        
        self.reportes_button = ctk.CTkButton(self.sidebar_frame, text="Generar Reportes", command=lambda: self.select_frame_by_name("reportes"))
        self.reportes_button.grid(row=4, column=0, padx=20, pady=10)
        
        self.logo_label_bottom = ctk.CTkLabel(self.sidebar_frame, image=self.pvd_logo, text="")
        self.logo_label_bottom.grid(row=5, column=0, padx=20, pady=20, sticky="s")
        
        # --- CONTENEDORES DE PANTALLAS ---
        self.sesiones_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.inventario_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.reservas_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.reportes_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        
        self.select_frame_by_name("sesiones")
        self.update_timers()
        
    def select_frame_by_name(self, name):
        for frame in [self.sesiones_frame, self.inventario_frame, self.reservas_frame, self.reportes_frame]:
            frame.grid_remove()
            
        if name == "sesiones":
            self.sesiones_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
            self.cargar_vista_sesiones()
        elif name == "inventario":
            self.inventario_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
            self.cargar_vista_inventario()
        elif name == "reservas":
            self.reservas_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
            self.cargar_vista_reservas()
        elif name == "reportes":
            self.reportes_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
            self.cargar_vista_reportes()

    # --- VISTA DE SESIONES (TARJETAS) ---
    def cargar_vista_sesiones(self):
        for widget in self.sesiones_frame.winfo_children():
            widget.destroy()
        self.timer_labels.clear()
        
        scrollable_frame = ctk.CTkScrollableFrame(self.sesiones_frame, fg_color="transparent")
        scrollable_frame.pack(fill="both", expand=True)
        scrollable_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        equipos = db.get_asignable_equipos()

        if not equipos:
            ctk.CTkLabel(scrollable_frame, text="No hay equipos asignables. Ve a 'Inventario' para añadir uno y marcarlo como 'Asignable'.").grid(row=0, column=0, columnspan=4, pady=20)
            return
            
        row_num, col_num = 0, 0
        for equipo in equipos:
            border_color = "gray25"
            if equipo["estado"] == "En Uso": border_color = "#3b8ed0"
            elif equipo["estado"] == "Mantenimiento": border_color = "#f57d00"
            
            card = ctk.CTkFrame(scrollable_frame, border_width=2, border_color=border_color)
            card.grid(row=row_num, column=col_num, padx=10, pady=10, sticky="nsew")
            
            icon_label = ctk.CTkLabel(card, image=self.laptop_icon, text="")
            icon_label.pack(pady=(10, 0))
            
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
                
                if sesion_activa and sesion_activa['hora_fin_timestamp']:
                    timer_label = ctk.CTkLabel(card, text="--:--:--", font=ctk.CTkFont(size=20, weight="bold"))
                    timer_label.pack(pady=5, padx=10)
                    self.timer_labels[sesion_id] = timer_label
                else:
                    ctk.CTkLabel(card, text="TIEMPO: Sin Límite", font=ctk.CTkFont(slant="italic")).pack(pady=5, padx=10)
                    
                ctk.CTkLabel(card, text=f"ESTADO: {equipo['estado']}", font=ctk.CTkFont(size=12)).pack(pady=2, padx=10)
                
                actions_card_frame = ctk.CTkFrame(card, fg_color="transparent")
                actions_card_frame.pack(pady=10, padx=10)

                liberar_button = ctk.CTkButton(actions_card_frame, text="Liberar", fg_color="red", command=lambda sid=sesion_id, eid=equipo["id"]: self.liberar_equipo(sid, eid))
                liberar_button.pack(side="left", padx=5)

                bloquear_button = ctk.CTkButton(actions_card_frame, text="Bloquear", command=lambda eid=equipo["id"]: self.bloquear_equipo_manual(eid))
                bloquear_button.pack(side="left", padx=5)
            else: 
                ctk.CTkLabel(card, text="USUARIO: N/A", font=ctk.CTkFont(size=12)).pack(pady=2, padx=10)
                ctk.CTkLabel(card, text="TIEMPO: N/A", font=ctk.CTkFont(size=12)).pack(pady=5, padx=10)
                ctk.CTkLabel(card, text=f"ESTADO: {equipo['estado']}", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=2, padx=10)
                
                action_button = ctk.CTkButton(card, text="Asignar", command=lambda eid=equipo["id"], nom=equipo["nombre"]: self.abrir_dialogo_asignar(eid, nom))
                if equipo['estado'] == 'Mantenimiento':
                    action_button.configure(state="disabled")
                action_button.pack(pady=10, padx=10)

            col_num += 1
            if col_num > 3:
                col_num, row_num = 0, row_num + 1

    # --- VISTA DE INVENTARIO ---
    def cargar_vista_inventario(self):
        for widget in self.inventario_frame.winfo_children():
            widget.destroy()
            
        top_frame = ctk.CTkFrame(self.inventario_frame)
        top_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(top_frame, text="Gestión de Inventario", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left", padx=10)
        
        add_button = ctk.CTkButton(top_frame, text="➕ Añadir Ítem", command=self.abrir_dialogo_equipo)
        add_button.pack(side="right", padx=10, pady=5)
        
        list_frame = ctk.CTkScrollableFrame(self.inventario_frame)
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        list_frame.grid_columnconfigure(0, weight=2)
        list_frame.grid_columnconfigure(1, weight=1)
        list_frame.grid_columnconfigure(2, weight=0)
        list_frame.grid_columnconfigure(3, weight=1)
        list_frame.grid_columnconfigure(4, weight=1)
        list_frame.grid_columnconfigure(5, weight=2)
        
        headers = ["Nombre", "Tipo", "Cantidad", "N° Serie", "Estado", "Acciones"]
        for i, header in enumerate(headers):
            label = ctk.CTkLabel(list_frame, text=header, font=ctk.CTkFont(weight="bold"))
            label.grid(row=0, column=i, padx=10, pady=10, sticky="w")
            
        equipos = db.get_all_equipos()
        for row_num, equipo in enumerate(equipos, start=1):
            ctk.CTkLabel(list_frame, text=equipo["nombre"]).grid(row=row_num, column=0, padx=10, pady=5, sticky="w")
            ctk.CTkLabel(list_frame, text=equipo["tipo"]).grid(row=row_num, column=1, padx=10, pady=5, sticky="w")
            ctk.CTkLabel(list_frame, text=equipo["cantidad"]).grid(row=row_num, column=2, padx=10, pady=5, sticky="w")
            ctk.CTkLabel(list_frame, text=equipo["numero_serie"]).grid(row=row_num, column=3, padx=10, pady=5, sticky="w")
            ctk.CTkLabel(list_frame, text=equipo["estado"]).grid(row=row_num, column=4, padx=10, pady=5, sticky="w")
            
            actions_frame = ctk.CTkFrame(list_frame, fg_color="transparent")
            actions_frame.grid(row=row_num, column=5, padx=5, pady=5, sticky="w")
            
            if equipo['estado'] == 'Disponible' and equipo['es_asignable'] == 1:
                maint_button = ctk.CTkButton(actions_frame, text="🔧 Mantenimiento", width=120, fg_color="#f57d00", hover_color="#b35900", command=lambda eid=equipo['id']: self.abrir_dialogo_mantenimiento(eid))
                maint_button.pack(side="left", padx=5)
            elif equipo['estado'] == 'Mantenimiento':
                maint_button = ctk.CTkButton(actions_frame, text="✅ Disponible", width=120, fg_color="green", hover_color="dark green", command=lambda eid=equipo['id']: self.finalizar_mantenimiento_equipo(eid))
                maint_button.pack(side="left", padx=5)
            
            edit_button = ctk.CTkButton(actions_frame, text="✏️", width=30, command=lambda e=equipo: self.abrir_dialogo_equipo(e))
            edit_button.pack(side="left", padx=5)
            delete_button = ctk.CTkButton(actions_frame, text="❌", width=30, fg_color="red", command=lambda eid=equipo["id"]: self.eliminar_equipo(eid))
            delete_button.pack(side="left")

    # --- CRUD DE EQUIPOS ---
    def abrir_dialogo_equipo(self, equipo=None):
        dialog = EquipoDialog(self, equipo)

    def eliminar_equipo(self, equipo_id):
        equipo = next((e for e in db.get_all_equipos() if e['id'] == equipo_id), None)
        if equipo and equipo['estado'] == 'En Uso':
            messagebox.showerror("Error", "No se puede eliminar un ítem que está en uso.")
            return
        if messagebox.askyesno("Confirmar Eliminación", f"¿Estás seguro de que quieres eliminar este ítem?"):
            db.delete_equipo(equipo_id)
            self.cargar_vista_inventario()
            self.cargar_vista_sesiones()

    # --- CRUD DE RESERVAS ---
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
        
        ctk.CTkLabel(self.form_frame, text="Fecha Fin:", anchor="w").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.reserva_fin_date_entry = DateEntry(self.form_frame, date_pattern='yyyy-mm-dd', width=15)
        self.reserva_fin_date_entry.grid(row=3, column=1, padx=(10, 0), pady=5, sticky="w")
        self.reserva_fin_hora_combo = ctk.CTkComboBox(self.form_frame, values=horas, width=70)
        self.reserva_fin_hora_combo.grid(row=3, column=2, padx=5, pady=5, sticky="w")
        self.reserva_fin_min_combo = ctk.CTkComboBox(self.form_frame, values=minutos, width=70)
        self.reserva_fin_min_combo.grid(row=3, column=3, padx=(0, 10), pady=5, sticky="w")
        
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

    # --- LÓGICA DEL AGENTE REMOTO ---
    def abrir_dialogo_asignar(self, equipo_id, equipo_nombre):
        dialog = AsignarSesionDialog(self, equipo_id, equipo_nombre)

    def iniciar_sesion_remota(self, equipo_id, usuario, duracion_minutos):
        # Esta función ahora SÓLO se usa para iniciar sesiones, no para bloquear
        hora_fin_timestamp = None
        if duracion_minutos is not None:
            hora_fin_timestamp = time.time() + (duracion_minutos * 60)
        
        db.iniciar_sesion(equipo_id, usuario, hora_fin_timestamp)
        
        equipo = next((e for e in db.get_all_equipos() if e['id'] == equipo_id), None)
        if not equipo: return
        
        ruta_archivo_comando = os.path.join(RUTA_COMANDOS, f"{equipo['nombre']}.json")
        comando = {"estado": "activo"}
        if hora_fin_timestamp:
            comando["hora_fin_timestamp"] = hora_fin_timestamp
            
        try:
            with open(ruta_archivo_comando, 'w') as f:
                json.dump(comando, f)
            print(f"Comando enviado a {equipo['nombre']}")
        except Exception as e:
            messagebox.showerror("Error de Red", f"No se pudo escribir el archivo de comando.\nError: {e}")

    def liberar_equipo(self, sesion_id, equipo_id):
        if sesion_id:
            db.liberar_sesion(sesion_id, equipo_id)
            
            equipo = next((e for e in db.get_all_equipos() if e['id'] == equipo_id), None)
            if equipo:
                ruta_archivo_comando = os.path.join(RUTA_COMANDOS, f"{equipo['nombre']}.json")
                if os.path.exists(ruta_archivo_comando):
                    try: os.remove(ruta_archivo_comando)
                    except Exception as e: print(f"No se pudo borrar el archivo de comando: {e}")
            self.cargar_vista_sesiones()
            self.cargar_vista_inventario()

    def bloquear_equipo_manual(self, equipo_id):
        equipo = next((e for e in db.get_all_equipos() if e['id'] == equipo_id), None)
        if equipo and messagebox.askyesno("Confirmar Bloqueo", f"¿Estás seguro de que quieres bloquear manualmente {equipo['nombre']}?"):
            self.enviar_comando_bloqueo(equipo_id)

    def enviar_comando_bloqueo(self, equipo_id):
        """Función dedicada para enviar solo la orden de bloqueo."""
        equipo = next((e for e in db.get_all_equipos() if e['id'] == equipo_id), None)
        if not equipo: return
        
        ruta_archivo_comando = os.path.join(RUTA_COMANDOS, f"{equipo['nombre']}.json")
        comando = {
            "estado": "activo",
            "hora_fin_timestamp": time.time() - 10 # Un tiempo en el pasado para forzar bloqueo
        }
        
        try:
            with open(ruta_archivo_comando, 'w') as f:
                json.dump(comando, f)
            print(f"Comando de bloqueo enviado a {equipo['nombre']}")
        except Exception as e:
            messagebox.showerror("Error de Red", f"No se pudo escribir el archivo de comando.\nError: {e}")
            
    # --- LÓGICA DE MANTENIMIENTO ---
    def abrir_dialogo_mantenimiento(self, equipo_id):
        dialog = MantenimientoDialog(self, equipo_id)

    def finalizar_mantenimiento_equipo(self, equipo_id):
        db.finalizar_mantenimiento(equipo_id)
        self.cargar_vista_inventario()
        self.cargar_vista_sesiones()

    # --- TEMPORIZADOR ---
    def update_timers(self):
        conn = db.conectar_db()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, hora_fin_timestamp FROM sesiones WHERE hora_fin IS NULL AND hora_fin_timestamp IS NOT NULL")
        sesiones_activas = cursor.fetchall()
        conn.close()
        for sesion in sesiones_activas:
            sesion_id = sesion['id']
            if sesion_id in self.timer_labels:
                hora_fin_ts = sesion['hora_fin_timestamp']
                
                tiempo_restante = hora_fin_ts - time.time()
                
                if tiempo_restante > 0:
                    horas, rem = divmod(int(tiempo_restante), 3600)
                    minutos, segundos = divmod(rem, 60)
                    self.timer_labels[sesion_id].configure(text=f"TIEMPO: {horas:02d}:{minutos:02d}:{segundos:02d}")
                else:
                    self.timer_labels[sesion_id].configure(text="¡TIEMPO AGOTADO!", text_color="orange red")
        
        self.after(1000, self.update_timers)

    # --- VISTA DE REPORTES ---
    def cargar_vista_reportes(self):
        for widget in self.reportes_frame.winfo_children():
            widget.destroy()
        
        ctk.CTkLabel(self.reportes_frame, text="Centro de Reportes", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=10)

        button_frame = ctk.CTkFrame(self.reportes_frame)
        button_frame.pack(pady=10, padx=20, fill="x")

        ctk.CTkButton(button_frame, text="📄 Historial de Uso de Equipos", height=40, command=self.generar_reporte_sesiones).pack(pady=5, fill="x")
        ctk.CTkButton(button_frame, text="📦 Reporte de Inventario General", height=40, command=self.generar_reporte_inventario).pack(pady=5, fill="x")
        ctk.CTkButton(button_frame, text="🗓️ Reporte de Reservas", height=40, command=self.generar_reporte_reservas).pack(pady=5, fill="x")
        ctk.CTkButton(button_frame, text="🛠️ Historial de Mantenimientos", height=40, command=self.generar_reporte_mantenimientos).pack(pady=5, fill="x")
        ctk.CTkButton(button_frame, text="🧹 Realizar Depuración Semestral", height=40, fg_color="#c90000", hover_color="#8c0000", command=self.realizar_depuracion).pack(pady=10, fill="x")
    
    def _generar_pdf(self, html_content, default_filename, auto_open=False):
        if auto_open:
            filepath = default_filename
        else:
            filepath = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("Archivos PDF", "*.pdf")], title="Guardar reporte como...", initialfile=default_filename)
        
        if not filepath: return False

        try:
            HTML(string=html_content).write_pdf(filepath)
            
            if auto_open:
                if os.path.exists(filepath):
                    if os.name == 'nt': os.startfile(filepath)
                    else: webbrowser.open(f'file://{os.path.realpath(filepath)}')
                return True
            else:
                messagebox.showinfo("Éxito", f"Reporte guardado exitosamente en:\n{filepath}")
                if messagebox.askyesno("Abrir Reporte", "¿Deseas abrir el reporte ahora?"):
                    if os.name == 'nt': os.startfile(filepath)
                    else: webbrowser.open(f'file://{os.path.realpath(filepath)}')
                return True

        except Exception as e:
            messagebox.showerror("Error al Generar PDF", f"Ocurrió un error: {e}")
            return False

    def _crear_html_base(self, titulo):
        return f"""
        <html><head><style>
            body {{ font-family: sans-serif; }} h1 {{ color: #333; }} p {{ color: #777; font-size: 0.9em; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }} th, td {{ border: 1px solid #ddd; text-align: left; padding: 8px; }}
            tr:nth-child(even) {{ background-color: #f2f2f2; }} th {{ background-color: #007bff; color: white; }}
        </style></head><body><h1>{titulo}</h1><p>Reporte generado el: {datetime.now().strftime('%Y-%m-%d a las %H:%M:%S')}</p>
        """

    def generar_reporte_sesiones(self):
        sesiones = db.get_completed_sessions()
        if not sesiones:
            messagebox.showinfo("Reporte Vacío", "No hay sesiones completadas para generar un reporte.")
            return
            
        html = self._crear_html_base("Reporte de Uso de Equipos")
        html += f"<p><strong>Total de Sesiones Registradas: {len(sesiones)}</strong></p>"
        html += "<table><tr><th>Equipo</th><th>Usuario</th><th>Inicio</th><th>Fin</th><th>Duración</th></tr>"
        for s in sesiones:
            try:
                inicio = datetime.strptime(s['hora_inicio'], '%Y-%m-%d %H:%M:%S')
                fin = datetime.strptime(s['hora_fin'], '%Y-%m-%d %H:%M:%S')
                duracion = fin - inicio
                total_seconds = int(duracion.total_seconds())
                horas, rem = divmod(total_seconds, 3600)
                minutos, segundos = divmod(rem, 60)
                duracion_str = f"{horas:02d}h {minutos:02d}m {segundos:02d}s"
            except (ValueError, TypeError):
                duracion_str = "N/A"
            html += f"<tr><td>{s['equipo_nombre']}</td><td>{s['usuario_temporal']}</td><td>{s['hora_inicio']}</td><td>{s['hora_fin']}</td><td>{duracion_str}</td></tr>"
        html += "</table></body></html>"
        self._generar_pdf(html, "Reporte_Uso_Equipos.pdf")

    def generar_reporte_inventario(self):
        equipos = db.get_all_equipos()
        if not equipos:
            messagebox.showinfo("Reporte Vacío", "No hay ítems en el inventario.")
            return
        
        html = self._crear_html_base("Reporte de Inventario General")
        html += f"<p><strong>Total de Ítems Registrados: {len(equipos)}</strong></p>"
        html += "<table><tr><th>Nombre</th><th>Tipo</th><th>Cantidad</th><th>N° Serie</th><th>Estado Actual</th></tr>"
        for equipo in equipos:
            html += f"<tr><td>{equipo['nombre']}</td><td>{equipo['tipo']}</td><td>{equipo['cantidad']}</td><td>{equipo['numero_serie']}</td><td>{equipo['estado']}</td></tr>"
        html += "</table></body></html>"
        self._generar_pdf(html, "Reporte_Inventario.pdf")
    
    def generar_reporte_reservas(self):
        reservas = db.get_all_reservas()
        if not reservas:
            messagebox.showinfo("Reporte Vacío", "No hay reservas registradas.")
            return
        
        html = self._crear_html_base("Reporte de Reservas de Recinto")
        html += f"<p><strong>Total de Reservas Registradas: {len(reservas)}</strong></p>"
        html += "<table><tr><th>Entidad</th><th>Motivo</th><th>Inicio</th><th>Fin</th></tr>"
        for r in reservas:
            html += f"<tr><td>{r['entidad']}</td><td>{r['motivo']}</td><td>{r['fecha_inicio']}</td><td>{r['fecha_fin']}</td></tr>"
        html += "</table></body></html>"
        self._generar_pdf(html, "Reporte_Reservas.pdf")

    def generar_reporte_mantenimientos(self):
        historial = db.get_mantenimiento_history()
        if not historial:
            messagebox.showinfo("Reporte Vacío", "No hay registros de mantenimiento.")
            return
            
        html = self._crear_html_base("Historial de Mantenimientos")
        html += f"<p><strong>Total de Registros de Mantenimiento: {len(historial)}</strong></p>"
        html += "<table><tr><th>Equipo</th><th>Descripción</th><th>Inicio</th><th>Fin</th></tr>"
        for h in historial:
            fecha_fin = h['fecha_fin'] if h['fecha_fin'] else "En Progreso"
            html += f"<tr><td>{h['equipo_nombre']}</td><td>{h['descripcion']}</td><td>{h['fecha_inicio']}</td><td>{fecha_fin}</td></tr>"
        html += "</table></body></html>"
        self._generar_pdf(html, "Reporte_Mantenimientos.pdf")

    def realizar_depuracion(self):
        old_sesiones, old_reservas, old_mantenimientos = db.get_old_records()
        total_records = len(old_sesiones) + len(old_reservas) + len(old_mantenimientos)
        
        if total_records == 0:
            messagebox.showinfo("Depuración", "No hay registros antiguos (más de 6 meses) para depurar.")
            return

        html = self._crear_html_base(f"Reporte de Depuración - {total_records} Registros Antiguos a Eliminar")
        if old_sesiones:
            html += "<h2>Sesiones Antiguas</h2><table><tr><th>Usuario</th><th>Inicio</th><th>Fin</th></tr>"
            for s in old_sesiones: html += f"<tr><td>{s['usuario_temporal']}</td><td>{s['hora_inicio']}</td><td>{s['hora_fin']}</td></tr>"
            html += "</table>"
        if old_reservas:
            html += "<h2>Reservas Antiguas</h2><table><tr><th>Entidad</th><th>Inicio</th><th>Fin</th></tr>"
            for r in old_reservas: html += f"<tr><td>{r['entidad']}</td><td>{r['fecha_inicio']}</td><td>{r['fecha_fin']}</td></tr>"
            html += "</table>"
        if old_mantenimientos:
            html += "<h2>Mantenimientos Antiguos</h2><table><tr><th>Descripción</th><th>Inicio</th><th>Fin</th></tr>"
            for m in old_mantenimientos: html += f"<tr><td>{m['descripcion']}</td><td>{m['fecha_inicio']}</td><td>{m['fecha_fin']}</td></tr>"
            html += "</table>"
        html += "</body></html>"
        
        filepath = os.path.join(os.path.expanduser("~"), "Desktop", "Reporte_Depuracion_PVD.pdf")
        
        if not self._generar_pdf(html, filepath, auto_open=True):
            messagebox.showerror("Error", "No se pudo generar el reporte de depuración. Operación cancelada.")
            return

        if messagebox.askyesno("Confirmar Depuración", f"Se ha generado y abierto un reporte en tu escritorio con los {total_records} registros antiguos.\n¿ESTÁS SEGURO de que quieres eliminarlos permanentemente?"):
            db.delete_old_records()
            messagebox.showinfo("Éxito", "La base de datos ha sido depurada.")

# --- PUNTO DE ENTRADA DE LA APLICACIÓN ---
if __name__ == "__main__":
    app = App()
    app.mainloop()