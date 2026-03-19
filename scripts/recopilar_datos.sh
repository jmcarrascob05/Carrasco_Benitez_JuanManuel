#!/bin/bash

# Define el directorio del volumen compartido
carpeta_compartida="/datos_compartidos"

# Obtiene el nombre del contenedor desde el hostname
contenedor=$(hostname)

# Construye la ruta del archivo
archivo_datos="$carpeta_compartida/${contenedor}.txt"

# Cabecera del archivo con identificación y timestamp
echo "--------------------------------------------" > "$archivo_datos"
echo "CONTENEDOR: $contenedor" >> "$archivo_datos"
echo "TIMESTAMP: $(date '+%Y-%m-%d %H:%M:%S')" >> "$archivo_datos"
echo "--------------------------------------------" >> "$archivo_datos"
echo "" >> "$archivo_datos"

# Recopila y lista de todos los procesos activos con uso de CPU/RAM
echo "--- PROCESOS ACTIVOS ---" >> "$archivo_datos"
ps aux >> "$archivo_datos"
echo "" >> "$archivo_datos"

# Coge los datos de uso de CPU
echo "--- USO DE CPU ---" >> "$archivo_datos"
top -bn1 | head -15 >> "$archivo_datos" 2>/dev/null || echo "top no disponible" >> "$archivo_datos"
echo "" >> "$archivo_datos"

# Coge el uso de memoria RAM
echo "--- USO DE MEMORIA ---" >> "$archivo_datos"
free -h >> "$archivo_datos"
echo "" >> "$archivo_datos"

# Coge el uso de disco 
echo "--- USO DE DISCO ---" >> "$archivo_datos"
df -h >> "$archivo_datos"
echo "" >> "$archivo_datos"

# Verifica si los servicios estan funcionando
echo "--- SERVICIOS ---" >> "$archivo_datos"

# Busca proceso nginx
echo "NGINX:" >> "$archivo_datos"
ps aux | grep -v grep | grep nginx >> "$archivo_datos" 2>&1 || echo " No encontrado" >> "$archivo_datos"

# Busca proceso mariadb
echo "MARIADB:" >> "$archivo_datos"
ps aux | grep -v grep | grep mariadbd >> "$archivo_datos" 2>&1 || echo " No encontrado" >> "$archivo_datos"

# Confirma el correcto funcionamiento
echo "[$(date '+%H:%M:%S')] Datos guardados"
