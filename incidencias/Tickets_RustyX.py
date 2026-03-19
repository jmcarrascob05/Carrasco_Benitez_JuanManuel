import csv
from datetime import datetime
import os

# Archivos CSV donde se almacenan los datos
ARCHIVO_USUARIOS = "usuarios.csv"
ARCHIVO_INCIDENCIAS = "incidencias.csv"


def verificar_login(usuario, password):
    #Verifica si el usuario y contraseña existen en usuarios.csv
    try:
        # open() abre el archivo en modo lectura ('r')
        # DictReader lee el CSV y convierte cada fila en un diccionario(busque informacion y era recomendable hacerlo asi)
        # delimiter=';' indica que las columnas están separadas por punto y coma
        with open(ARCHIVO_USUARIOS, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            
            # Recorre cada fila del CSV
            for row in reader:
                # strip() elimina espacios en blanco al inicio y final para una mejor lectura
                if row['usuario'].strip() == usuario and row['password'].strip() == password:
                    return True
        return False
    
    except FileNotFoundError:
        print(f"No se encuentra el archivo {ARCHIVO_USUARIOS}")
        return False
    except Exception as e:
        print(f"Error al leer usuarios: {e}")
        return False


def obtener_siguiente_id():
    # Calcula el siguiente ID disponible para una incidencia
    try:
        with open(ARCHIVO_INCIDENCIAS, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            # Lista de comprensión: obtiene todos los IDs del CSV
            ids = [int(row['ID']) for row in reader if row['ID'].isdigit()]
            # max() obtiene el ID más alto, luego suma 1, para que tengan un codigo unico
            return max(ids) + 1 if ids else 1
    except FileNotFoundError:
        # Si no existe el archivo, empieza desde ID 1
        return 1


def crear_incidencia(usuario_actual):
    # Crea una nueva incidencia y la guarda en el CSV
    print("--- CREAR INCIDENCIA ---")
    
    # Solicita datos al usuario
    descripcion = input("Descripción: ")
    tipo = input("Tipo (WEB/BD/RED/SERVIDOR): ").upper()  # upper() convierte a mayúsculas
    prioridad = input("Prioridad (BAJA/MEDIA/ALTA): ").upper()
    
    # Diccionario con los datos de la nueva incidencia para el encaebzado(forma recomendable)
    nueva = {
        'ID': obtener_siguiente_id(),
        'Fecha': datetime.now().strftime("%Y-%m-%d"),  # strftime() formatea la fecha como nostros queramos
        'Hora': datetime.now().strftime("%H:%M:%S"),
        'Usuario': usuario_actual,
        'Tipo': tipo,
        'Prioridad': prioridad,
        'Descripcion': descripcion,
        'Estado': 'ABIERTA'
    }
    
    # Verifica si el archivo existe para saber si escribir encabezados
    archivo_existe = os.path.exists(ARCHIVO_INCIDENCIAS)
    
    # 'a' = append (añadir al final del archivo)
    # newline='' evita líneas en blanco adicionales en Windows
    # DictWriter escribe diccionarios como filas CSV
    with open(ARCHIVO_INCIDENCIAS, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=nueva.keys(), delimiter=';')
        
        # Si el archivo no existe, escribe primero los encabezados
        if not archivo_existe:
            writer.writeheader()
        
        # writerow() escribe la fila con los datos de la incidencia
        writer.writerow(nueva)
    
    print(f"Incidencia #{nueva['ID']} creada correctamente")


def listar_incidencias():
    # Muestra todas las incidencias registradas
    print("LISTA DE INCIDENCIAS")
    try:
        with open(ARCHIVO_INCIDENCIAS, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=';')
            
            # Recorre cada incidencia y la printea formateada
            for row in reader:
                print(f"ID:{row['ID']} | {row['Fecha']} | {row['Usuario']} | {row['Estado']} | {row['Descripcion']}")
    
    except FileNotFoundError:
        print("No hay incidencias registradas")


def menu_principal(usuario):
    # Menú principal del sistema
    while True:  # Bucle infinito hasta que el usuario elija salir
        print(f"GESTIÓN DE INCIDENCIAS - Usuario: {usuario}")
        print("1. Crear incidencia")
        print("2. Ver incidencias")
        print("3. Salir")
        
        opcion = input("Opción: ")
        
        if opcion == "1":
            crear_incidencia(usuario)
        elif opcion == "2":
            listar_incidencias()
        elif opcion == "3":
            print("Saliendo del sistema...")
            break  # Sale del bucle while


def main():
    # Función principal: Login y acceso al menú
    print("SISTEMA DE GESTIÓN DE INCIDENCIAS")
    
    usuario = input("Usuario: ")
    password = input("Contraseña: ")
    
    if verificar_login(usuario, password):
        print("Login correcto")
        menu_principal(usuario)
    else:
        print("Usuario o contraseña incorrectos")

# Ejecuta main() solo cuando se llama directamente al script, es el inicio del script
if __name__ == "__main__":
    main()

