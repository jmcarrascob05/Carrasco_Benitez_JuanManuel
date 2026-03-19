#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk                       # Librería gráfica estándar de Python
from tkinter import ttk                    # Widgets adicionales: barras de progreso y tabla
import os, re, threading, time            # Sistema de archivos, expresiones regulares, hilos y temporizadores
from datetime import datetime             # Para fechas y horas

# ── Configuración global ──────────────────────────────────────────────────────

# Carpeta donde cada contenedor deposita su archivo .txt con métricas
DIR = r"C:\Users\jmanu\OneDrive\Documentos\ASIR2\proyecto-rustyx\datos_contenedores"

# Ruta del archivo donde se guardan todas las caídas detectadas
ARCHIVO_CAIDAS = os.path.join(DIR, "caidas.log")

# Diccionario que mapea el nombre técnico del contenedor → nombre legible para la UI
CONTENEDORES = {
    'rustyx-balanceador': 'Balanceador',
    'rustyx-web1': 'Servidor Web 1',
    'rustyx-web2': 'Servidor Web 2',
    'rustyx-db': 'Base de Datos'
}

# ── Parseo de métricas (Parsear es extraer la informacion)────────────────────────────────────────────────────────

# Convierte un valor de memoria a megabytes (MB) según su unidad.
# El dict actúa como tabla de conversión:
#   - Gi (gibibytes) → × 1024
#   - Mi (mebibytes) → × 1  (ya está en MB)
#   - Ki (kibibytes) → ÷ 1024
#   - sin unidad     → asume bytes, divide entre 1 048 576
def _a_mb(val, unit):
    return val * {'Gi': 1024, 'Mi': 1, 'Ki': 1/1024}.get(unit, 1/1048576)


# Lee el archivo de texto de un contenedor y extrae todas sus métricas.
# El archivo lo genera un script en el propio contenedor; contiene la
# salida de comandos como `top`, `df`, `ps`, etc.
# Devuelve un con las claves:
#     timestamp, nginx, mariadb, cpu, memoria, disco, procesos
# Si el archivo no existe o está vacío devuelve {} (dict vacío).
def parsear(archivo): # Parsear es extraer la informacion
    # Si el archivo no existe todavía, no hay nada que leer
    if not os.path.exists(archivo):
        return {}

    try:
        # Leemos todo el contenido de una vez; errors='ignore' evita crashes
        # si hay caracteres no-UTF8 en la salida del contenedor
        txt = open(archivo, encoding='utf-8', errors='ignore').read()

        # Descartamos archivos demasiado pequeños (probablemente vacíos o corruptos)
        if len(txt) < 50:
            return {}

        d = {}  # Aquí iremos acumulando los datos extraídos

        # Timestamp
        # El script del contenedor escribe una línea "TIMESTAMP: YYYY-MM-DD HH:MM:SS"
        # Si no la encontramos usamos un objeto anónimo que devuelve 'Desconocido'
        d['timestamp'] = (
            re.search(r'TIMESTAMP: (.+)', txt)
            or type('', (), {'group': lambda *_: 'Desconocido'})()
        ).group(1)

        # Estado de servicios
        # Si el proceso maestro de nginx aparece en la salida de ps/top → está activo
        d['nginx']   = 'ejecutando' if 'nginx: master' in txt else 'detenido'
        # Lo mismo para MariaDB (el proceso se llama 'mariadbd')
        d['mariadb'] = 'ejecutando' if 'mariadbd'      in txt else 'detenido'

        # CPU
        # Formato 1 de `top`: "Cpu(s): 12.5 us, ..."  → tomamos directamente el % de usuario
        m = re.search(r'%?Cpu\(s\):\s*([\d.]+)\s*us', txt, re.I)
        if m:
            d['cpu'] = min(100.0, float(m.group(1)))
        else:
            # Formato 2 de `top`: "Cpu(s): ... 87.5 id"  → calculamos uso = 100 - idle
            m = re.search(r'Cpu\(s\).*?([\d.]+)%?\s*id', txt, re.I)
            d['cpu'] = min(100.0, 100 - float(m.group(1))) if m else 0.0

        # Memoria
        # Formato con unidades (ej: "Mem: 1.9Gi  512Mi ..."):
        #   grupo 1+2 = total con unidad, grupo 3+4 = usado con unidad
        m = re.search(r'Mem:\s+([\d.]+)(Gi|Mi|Ki)?\s+([\d.]+)(Gi|Mi|Ki)?', txt)
        if m:
            total = _a_mb(float(m.group(1)), m.group(2) or '')
            usado = _a_mb(float(m.group(3)), m.group(4) or '')
            d['memoria'] = min(100.0, usado / total * 100) if total else 0.0
        else:
            # Formato sin unidades (ej: "Mem: 2048000  512000"), valores en KB
            m = re.search(r'Mem:\s+(\d+)\s+(\d+)', txt)
            total, usado = (int(m.group(1)), int(m.group(2))) if m else (0, 0)
            d['memoria'] = min(100.0, usado / total * 100) if total else 0.0

        # Disco
        # Buscamos la línea de `df` que muestra el uso del directorio raíz "/"
        # Ejemplo: "  23%  /"  → capturamos el 23
        m = re.search(r'(\d+)%\s+/$', txt, re.M)
        d['disco'] = float(m.group(1)) if m else 0.0

        # Número de procesos
        # Contamos líneas de `ps` que empiezan con usuario + PID + uso de CPU
        # Restamos 1 para excluir la cabecera de la tabla
        d['procesos'] = max(0, len(re.findall(r'^\S+\s+\d+\s+[\d.]+', txt, re.M)) - 1)

        return d

    except Exception as e:
        print(f"Error procesando {archivo}: {e}")
        return {}


# ── Registro de caídas ────────────────────────────────────────────────────────

# Añade una línea al archivo caidas.log con el formato:
#     2024-06-01 14:32:10 | Balanceador | nginx detenido
# Crea el directorio si no existe. Si falla la escritura solo imprime
# el error (no queremos que un fallo de log rompa la monitorización).
def guardar_caida(contenedor, motivo):
    linea = f"{datetime.now():%Y-%m-%d %H:%M:%S} | {contenedor} | {motivo}"
    try:
        os.makedirs(os.path.dirname(ARCHIVO_CAIDAS), exist_ok=True)
        open(ARCHIVO_CAIDAS, 'a', encoding='utf-8').write(linea)
    except Exception as e:
        print(f"Error guardando caída: {e}")


# ── Ventana historial de caídas ───────────────────────────────────────────────

# Ventana secundaria (Toplevel) que muestra el contenido de caidas.log
# en una tabla ordenada de más reciente a más antigua.
# Permite filtrar por fecha escribiendo un prefijo (YYYY-MM-DD).
class VentanaCaidas:

    def __init__(self, padre):
        # Creamos la ventana secundaria sobre la ventana principal (padre)
        w = tk.Toplevel(padre)
        w.title("Historial de Caídas")
        w.geometry("800x500")
        w.configure(bg='#2c3e50')

        # Barra de filtros
        bar = tk.Frame(w, bg='#34495e', pady=8)
        bar.pack(fill='x', padx=10, pady=(10, 0))

        tk.Label(bar, text="Filtrar por fecha (YYYY-MM-DD):",
                 bg='#34495e', fg='white', font=('Arial', 10)).pack(side='left', padx=(10, 5))

        # Campo de texto donde el usuario escribe la fecha a filtrar
        self.filtro = tk.Entry(bar, width=14, font=('Arial', 10))
        self.filtro.pack(side='left')

        # Botón que aplica el filtro recargando la tabla
        tk.Button(bar, text="Filtrar", bg='#2980b9', fg='white',
                  font=('Arial', 10), cursor='hand2',
                  command=self.cargar).pack(side='left', padx=8)

        # Botón que limpia el filtro y muestra todos los registros
        tk.Button(bar, text="Mostrar todo", bg='#7f8c8d', fg='white',
                  font=('Arial', 10), cursor='hand2',
                  command=lambda: [self.filtro.delete(0, 'end'), self.cargar()]).pack(side='left')

        # Tabla de registros
        cols = ('Fecha y Hora', 'Contenedor', 'Motivo')
        self.tabla = ttk.Treeview(w, columns=cols, show='headings', height=18)

        # Configuramos encabezado y ancho de cada columna
        for col, width in zip(cols, (160, 200, 380)):
            self.tabla.heading(col, text=col)
            self.tabla.column(col, width=width)

        self.tabla.pack(fill='both', expand=True, padx=10, pady=10)

        # Scrollbar vertical vinculada a la tabla
        ttk.Scrollbar(w, orient='vertical', command=self.tabla.yview).pack(side='right', fill='y')
        self.tabla.configure(yscrollcommand=ttk.Scrollbar(w).set)

        # Etiqueta que muestra cuántos registros hay y el filtro activo
        self.total_lbl = tk.Label(w, text="", bg='#2c3e50', fg='#ecf0f1', font=('Arial', 9))
        self.total_lbl.pack(pady=(0, 8))

        # Cargamos los datos al abrir la ventana
        self.cargar()

    # Lee caidas.log, aplica el filtro de fecha si existe y rellena la tabla.
    # Los registros se muestran de más reciente a más antiguo (reversed).
    def cargar(self):
        # Vaciamos la tabla antes de rellenarla
        self.tabla.delete(*self.tabla.get_children())
        filtro = self.filtro.get().strip()

        # Si el archivo no existe aún, informamos y salimos
        if not os.path.exists(ARCHIVO_CAIDAS):
            self.total_lbl.config(text="Sin caídas registradas todavía.")
            return

        try:
            lineas = open(ARCHIVO_CAIDAS, encoding='utf-8').readlines()
        except Exception as e:
            self.total_lbl.config(text=f"Error leyendo fichero: {e}")
            return

        total = 0
        for linea in reversed(lineas):           # Más reciente primero
            partes = linea.strip().split(' | ', 2)
            # Descartamos líneas mal formateadas o que no coincidan con el filtro
            if len(partes) != 3 or (filtro and not partes[0].startswith(filtro)):
                continue
            self.tabla.insert('', 'end', values=tuple(partes))
            total += 1

        # Mostramos el total de registros visibles (y el filtro aplicado si hay)
        self.total_lbl.config(
            text=f"{total} registro(s)" + (f"  —  Filtro: {filtro}" if filtro else "")
        )


# ── Monitor principal ─────────────────────────────────────────────────────────

# Ventana principal de la aplicación.
# Muestra una cuadrícula 2×2 con un panel por cada contenedor.
# Cada panel incluye: estado, timestamp, barras de CPU/RAM/disco,
# estado de servicios y número de procesos activos.
# La monitorización corre en un hilo de fondo (_bucle) para no bloquear
# la interfaz gráfica. Cada 3 segundos lee los archivos y actualiza la UI.
class Monitor:

    def __init__(self, ventana):
        self.ventana = ventana
        self.ventana.title("Monitor RustyX")
        self.ventana.geometry("1400x850")
        self.ventana.configure(bg='#2c3e50')

        self.paneles = {}  # Dict: cid → dict de widgets del panel

        # Rastrea el último estado conocido de cada contenedor/servicio.
        # Sirve para detectar TRANSICIONES (activo → caído) y evitar
        # registrar la misma caída repetidamente en cada ciclo.
        self._prev = {c: 'activo' for c in CONTENEDORES}

        self._construir()   # Construye todos los widgets
        self.iniciar()      # Arranca la monitorización inmediatamente al abrir

    # ── Construcción de la interfaz ───────────────────────────────────────────

    # Crea y coloca todos los widgets de la ventana principal.
    def _construir(self):

        # Cabecera
        hdr = tk.Frame(self.ventana, bg='#34495e', height=80)
        hdr.pack(fill='x', padx=10, pady=10)
        hdr.pack_propagate(False)   # Evita que los hijos redimensionen el Frame

        tk.Label(hdr, text="Monitor RustyX - Datos desde Contenedores",
                 font=('Arial', 20, 'bold'), bg='#34495e', fg='white').pack(side='left', padx=20, pady=15)

        # Botón que abre la ventana del historial de caídas
        tk.Button(hdr, text="Historial de Caídas", font=('Arial', 11, 'bold'),
                  bg='#8e44ad', fg='white', cursor='hand2',
                  command=lambda: VentanaCaidas(self.ventana)).pack(side='left', padx=10)

        # Indicador de estado global (siempre ACTIVO al arrancar)
        self.lbl_estado = tk.Label(hdr, text="● DETENIDO",
                                   font=('Arial', 16, 'bold'), bg='#34495e', fg='#e74c3c')
        self.lbl_estado.pack(side='right', padx=20)

        # Reloj en tiempo real (se actualiza cada segundo via _tick)
        self.lbl_hora = tk.Label(hdr, text="", font=('Arial', 12), bg='#34495e', fg='#ecf0f1')
        self.lbl_hora.pack(side='right', padx=20)
        self._tick()   # Arrancamos el reloj

        # Cuadrícula 2×2 de paneles
        grid = tk.Frame(self.ventana, bg='#2c3e50')
        grid.pack(fill='both', expand=True, padx=10, pady=5)

        # enumerate() nos da el índice i para calcular fila (i//2) y columna (i%2)
        for i, (cid, nombre) in enumerate(CONTENEDORES.items()):
            self._crear_panel(grid, cid, nombre).grid(
                row=i // 2, column=i % 2, padx=5, pady=5, sticky='nsew'
            )

        # Hacemos que las filas y columnas se expandan proporcionalmente al redimensionar
        for i in range(2):
            grid.grid_rowconfigure(i, weight=1)
            grid.grid_columnconfigure(i, weight=1)



    # Crea el LabelFrame de un contenedor con todos sus widgets y los
    # guarda en self.paneles[cid] para poder actualizarlos después.

    def _crear_panel(self, padre, cid, nombre):
        f = tk.LabelFrame(padre, text=f"  {nombre}  ",
                          font=('Arial', 14, 'bold'), bg='#34495e', fg='white',
                          relief='raised', bd=3)
        widgets = {}

        # Indicador de estado y timestamp del último dato recibido
        widgets['estado']    = tk.Label(f, text="SIN DATOS", font=('Arial', 10),
                                        bg='#34495e', fg='#95a5a6')
        widgets['timestamp'] = tk.Label(f, text="Última actualización: ---",
                                        font=('Arial', 8), bg='#34495e', fg='#95a5a6')
        widgets['estado'].pack(pady=3)
        widgets['timestamp'].pack(pady=2)

        # Creamos los tres bloques métrica (CPU, RAM, Disco) en un bucle
        # para evitar repetir el mismo código tres veces
        for key, label in (('cpu', 'CPU'), ('ram', 'RAM'), ('disco', 'Disco')):
            lbl = tk.Label(f, text=f"{label}: ---%", font=('Arial', 12),
                           bg='#34495e', fg='#ecf0f1', anchor='w')
            lbl.pack(fill='x', padx=10, pady=2)
            bar = ttk.Progressbar(f, length=200, mode='determinate')
            bar.pack(fill='x', padx=10, pady=2)
            widgets[f'lbl_{key}'] = lbl   # Ej: widgets['lbl_cpu']
            widgets[f'bar_{key}'] = bar   # Ej: widgets['bar_cpu']

        tk.Label(f, text="Servicios:", font=('Arial', 10, 'bold'),
                 bg='#34495e', fg='#ecf0f1').pack(anchor='w', padx=10, pady=3)

        # Etiquetas para nginx y mariadb (también en bucle para evitar repetición)
        for svc in ('nginx', 'mariadb'):
            lbl = tk.Label(f, text=f"  {svc}: ---", font=('Arial', 9),
                           bg='#34495e', fg='#95a5a6', anchor='w')
            lbl.pack(anchor='w', padx=15)
            widgets[svc] = lbl   # Ej: widgets['nginx']

        # Contador de procesos activos
        widgets['procesos'] = tk.Label(f, text="Procesos activos: ---",
                                       font=('Arial', 9), bg='#34495e', fg='#95a5a6')
        widgets['procesos'].pack(pady=3)

        # Registramos los widgets del panel para actualizarlos en _actualizar()
        self.paneles[cid] = widgets
        return f

    # ── Lógica de actualización ───────────────────────────────────────────────

    # Recorre todos los paneles, lee el archivo de cada contenedor
    # y actualiza los widgets con los datos nuevos.
    # Se llama desde el hilo de fondo (_bucle) cada 3 segundos.
    def _actualizar(self):
        for cid, p in self.paneles.items():
            arch = os.path.join(DIR, f"{cid}.txt")

            # Caso 1: el archivo no existe
            if not os.path.exists(arch):
                self._caida(cid, "Archivo de datos no encontrado")
                p['estado'].config(text="SIN DATOS", fg='#95a5a6')
                continue

            # Caso 2: el archivo existe pero está desactualizado
            # Si lleva más de 20 s sin modificarse, el contenedor probablemente cayó
            try:
                edad = time.time() - os.path.getmtime(arch)
                if edad > 20:
                    self._caida(cid, f"Sin datos recientes ({int(edad)}s de antigüedad)")
                    p['estado'].config(text="SIN DATOS (antiguo)", fg='#e74c3c')
                    continue
            except:
                pass   # Si getmtime falla (race condition), continuamos sin bloquear

            # Caso 3: parseamos el archivo
            d = parsear(arch)
            if not d:
                self._caida(cid, "Archivo vacío o ilegible")
                p['estado'].config(text="SIN DATOS", fg='#95a5a6')
                continue

            # Contenedor OK → marcamos como activo y actualizamos widgets
            self._prev[cid] = 'activo'
            p['estado'].config(text="ACTIVO", fg='#2ecc71')
            p['timestamp'].config(text=f"Última actualización: {d.get('timestamp', '?')}")

            # Actualizamos las tres métricas (CPU, RAM, Disco) en bucle
            # Tupla: (clave_widget, clave_dict, texto_etiqueta)
            for key, dkey, label in (
                ('cpu',   'cpu',      'CPU'),
                ('ram',   'memoria',  'RAM'),
                ('disco', 'disco',    'Disco')
            ):
                val = d.get(dkey, 0)
                p[f'lbl_{key}'].config(text=f"{label}: {val:.1f}%")
                p[f'bar_{key}']['value'] = min(val, 100)   # La barra va de 0 a 100

            # Actualizamos el estado de cada servicio (nginx, mariadb)
            for svc in ('nginx', 'mariadb'):
                estado = d.get(svc, 'detenido')
                ok = estado == 'ejecutando'
                if not ok:
                    # Solo registramos caída si antes estaba activo (evita duplicados)
                    self._caida(cid, f"{svc} detenido", clave=f"{cid}_{svc}")
                else:
                    self._prev[f"{cid}_{svc}"] = 'activo'
                p[svc].config(
                    text=f"  {svc}: {estado.upper()}",
                    fg='#2ecc71' if ok else '#e74c3c'   # Verde si activo, rojo si detenido
                )

            p['procesos'].config(text=f"Procesos activos: {d.get('procesos', 0)}")

    # Registra una caída en el log y en caidas.log, pero SOLO si es
    # la primera vez que se detecta (transición activo → caído).
    # El parámetro `clave` permite distinguir caídas de servicios dentro
    # del mismo contenedor (ej: 'rustyx-web1_nginx' vs 'rustyx-web1').
    # Si no se pasa clave se usa el cid del contenedor.
    def _caida(self, cid, motivo, clave=None):
        clave = clave or cid
        # Comprobamos si ya habíamos registrado esta caída antes
        if self._prev.get(clave) != 'caido':
            self._prev[clave] = 'caido'   # Actualizamos estado para no repetir
            nombre = CONTENEDORES.get(cid, cid)
            guardar_caida(nombre, motivo)  # Escribe en caidas.log
            print(f"CAÍDA detectada: {nombre} — {motivo}")   # Solo se registra en caidas.log

    # Actualiza el reloj de la cabecera cada segundo.
    # Usa ventana.after() en lugar de un hilo para mantenerse en el hilo
    # principal de Tkinter (más seguro para modificar widgets).
    def _tick(self):
        self.lbl_hora.config(text=datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
        self.ventana.after(1000, self._tick)   # Se llama a sí mismo cada 1000 ms

    # Arranca la monitorización automáticamente al abrir la app.
    # Lanza _bucle en un hilo de fondo (daemon=True para que muera
    # automáticamente al cerrar la ventana).
    def iniciar(self):
        self.lbl_estado.config(text="ACTIVO", fg='#2ecc71')
        threading.Thread(target=self._bucle, daemon=True).start()

    # Bucle de monitorización que corre en un hilo secundario.
    # Llama a _actualizar() cada 3 segundos indefinidamente.
    # El hilo es daemon, por lo que muere solo al cerrar la ventana.
    def _bucle(self):
        while True:
            self._actualizar()
            time.sleep(3)   # Pausa de 3 segundos entre lecturas


# ── Punto de entrada ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    ttk.Style().theme_use('clam')   
    Monitor(root)                   # Crea la ventana y construye toda la UI
    root.mainloop()                 # Cede el control a Tkinter (bucle de eventos)