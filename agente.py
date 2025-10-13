import os
import time
import json
import subprocess
import configparser
# --- NUEVAS IMPORTACIONES PARA EL CANDADO ---
import sys
import win32event
import win32api
from winerror import ERROR_ALREADY_EXISTS

# --- CÓDIGO DEL CANDADO (MUTEX) ---
class SingleInstance:
    def __init__(self, name):
        self.mutex = win32event.CreateMutex(None, 1, name)
        self.lasterror = win32api.GetLastError()
    
    def already_running(self):
        return self.lasterror == ERROR_ALREADY_EXISTS
    
    def __del__(self):
        if self.mutex:
            win32api.CloseHandle(self.mutex)

# --- Nombre único para nuestro candado ---
APP_MUTEX_ID = "SistemaPVD.Agente.Mutex.v1"
instance_checker = SingleInstance(APP_MUTEX_ID)

if instance_checker.already_running():
    print("Ya hay una instancia del agente en ejecución. Cerrando.")
    sys.exit(0)

# --- FUNCIÓN PARA LEER LA CONFIGURACIÓN (sin cambios) ---
def leer_configuracion():
    config = configparser.ConfigParser()
    if not os.path.exists('config.ini'):
        print("¡ERROR! No se encontró el archivo 'config.ini'.")
        print("Creando archivo de ejemplo 'config.ini'...")
        config['Configuracion'] = {
            'ID_EQUIPO': 'PC-EJEMPLO',
            'RUTA_COMPARTIDA': r'\\NOMBRE-DEL-PC-ADMIN\PVD_Comandos'
        }
        with open('config.ini', 'w') as configfile:
            config.write(configfile)
        time.sleep(20) 
        return None, None
    
    config.read('config.ini')
    id_equipo = config['Configuracion']['ID_EQUIPO']
    ruta_compartida = config['Configuracion']['RUTA_COMPARTIDA']
    return id_equipo, ruta_compartida

# --- CÓDIGO PRINCIPAL DEL AGENTE (sin cambios) ---
ID_EQUIPO, RUTA_COMPARTIDA = leer_configuracion()

if ID_EQUIPO:
    sesion_activa = False
    tiempo_finalizacion = 0

    print(f"--- Agente de Control PVD v2.1 (Singleton) iniciado para: {ID_EQUIPO} ---")
    print(f"--- Buscando comandos en: {RUTA_COMPARTIDA} ---")

    ruta_archivo_comando = os.path.join(RUTA_COMPARTIDA, f"{ID_EQUIPO}.json")

    while True:
        try:
            if os.path.exists(ruta_archivo_comando):
                if not sesion_activa:
                    print(f"Comando detectado para {ID_EQUIPO}.")
                    with open(ruta_archivo_comando, 'r') as f:
                        comando = json.load(f)
                    if comando.get("estado") == "activo":
                        if comando.get("hora_fin_timestamp"):
                            tiempo_finalizacion = float(comando["hora_fin_timestamp"])
                        else:
                            tiempo_finalizacion = time.time() + 99999999
                        sesion_activa = True

            if sesion_activa:
                if not os.path.exists(ruta_archivo_comando):
                    print("Comando eliminado. Finalizando sesión.")
                    sesion_activa = False
                    tiempo_finalizacion = 0
                    continue

                if time.time() > tiempo_finalizacion:
                    print("¡Tiempo finalizado! Bloqueando equipo...")
                    subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
                    try:
                        os.remove(ruta_archivo_comando)
                    except OSError as e:
                        print(f"Error al eliminar archivo: {e}")
                    sesion_activa = False
                    tiempo_finalizacion = 0
                    time.sleep(30)

        except Exception as e:
            print(f"Ocurrió un error: {e}")
            time.sleep(15)

        time.sleep(5)