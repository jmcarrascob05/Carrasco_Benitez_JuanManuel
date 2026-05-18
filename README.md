# Documentacion del proyecto RustyX

## 1. Resumen del proyecto

RustyX es una pagina web de catalogo de videojuegos desarrollada en PHP y MariaDB. La aplicacion permite consultar juegos, filtrarlos, ver su ficha individual, registrarse, iniciar sesion, valorar juegos, comentar, crear listas personales y gestionar contenido desde un panel de administracion.

El proyecto se ha preparado inicialmente con Docker para el entorno local, pero la web esta hecha con PHP clasico, por lo que tambien se puede subir a un hosting compartido como InfinityFree adaptando la configuracion de la base de datos.

## 2. Estructura principal

```text
web/rustyx/
  index.php              Catalogo principal
  juego.php              Ficha de cada videojuego
  login.php              Inicio de sesion
  registro.php           Registro de usuarios
  perfil.php             Perfil y avatar
  mis-listas.php         Listas personales
  config.php             Configuracion y funciones comunes
  admin/                 Panel de administracion
  partials/              Cabecera, footer y navegacion admin
  css/style.css          Estilos visuales
  assets/avatars/        Avatares subidos por usuarios
  assets/games/          Portadas subidas desde admin

sql/schema.sql           Esquema y datos iniciales de la base de datos
docker-compose.yml       Entorno local con balanceador, web y base de datos
```

## 3. Tecnologias utilizadas

- PHP 8 para la logica del servidor.
- MariaDB/MySQL para almacenar usuarios, juegos, comentarios, valoraciones y listas.
- HTML y CSS para la interfaz.
- JavaScript sencillo para el filtro rapido local y cambio de vista del catalogo.
- Docker para probar la infraestructura en local.
- InfinityFree como opcion de despliegue externo.

## 4. Base de datos

La base de datos principal se define en `sql/schema.sql`.

Tablas importantes:

- `usuarios`: guarda los datos de usuarios, contrasenas con hash, rol y avatar.
- `roles`: diferencia usuarios normales, administradores y otros roles.
- `videojuegos`: almacena titulo, descripcion, precio, estado, imagen y trailer de YouTube.
- `generos` y `plataformas`: catalogos auxiliares.
- `videojuego_genero` y `videojuego_plataforma`: relaciones muchos a muchos.
- `valoraciones`: puntuaciones de usuarios a juegos.
- `comentarios`: opiniones de usuarios.
- `lista` y `lista_videojuego`: listas personales de juegos.
- `admin_log`: registro de algunas acciones administrativas.

## 5. Funcionalidades realizadas

### Catalogo

El catalogo esta en `web/rustyx/index.php`.

Permite:

- Buscar por titulo o desarrollador.
- Filtrar por genero.
- Filtrar por plataforma.
- Filtrar por estado.
- Filtrar por precio maximo.
- Ordenar por puntuacion, fecha, precio o titulo.
- Paginar resultados.
- Cambiar entre vista de tarjetas y vista de lista.

Los filtros principales se hacen en servidor con SQL preparado. El filtro rapido se hace en navegador con JavaScript, ocultando tarjetas ya cargadas.

### Usuarios

El usuario puede registrarse e iniciar sesion.

En `registro.php` se validan campos como nombre, email, usuario y contrasena. La contrasena no se guarda en texto plano, sino usando:

```php
password_hash($password, PASSWORD_BCRYPT, ['cost' => 12]);
```

En `login.php` se comprueba con:

```php
password_verify($password, $user['password']);
```

### Perfil

En `perfil.php` el usuario puede:

- Ver sus datos.
- Subir o borrar avatar.
- Consultar numero de valoraciones, comentarios y listas.
- Ver ultimas valoraciones y comentarios.

La subida de avatar valida tipo MIME real, tamano maximo y permisos antes de guardar el archivo.

### Listas personales

En `mis-listas.php` el usuario puede:

- Crear listas.
- Eliminar listas propias.
- Ver juegos de una lista.
- Cambiar el estado de un juego: pendiente, jugando, completado o abandonado.
- Quitar juegos de una lista.

Todas las acciones comprueban el usuario conectado para evitar modificar listas ajenas.

### Panel de administracion

El panel admin esta en `web/rustyx/admin/`.

Permite:

- Crear, editar y eliminar juegos.
- Subir portadas de juegos.
- Asignar generos y plataformas.
- Cambiar roles de usuarios.
- Eliminar usuarios.
- Ver estadisticas en dashboard.
- Moderar comentarios y valoraciones.
- Exportar datos CSV.

El acceso se protege con `requireAdmin()`, definida en `config.php`.

## 6. Funcion destacada: exportacion CSV

La exportacion esta en:

```text
web/rustyx/admin/exportar.php
```

Solo puede usarla un administrador:

```php
require_once '../config.php';
requireAdmin();
```

El tipo de exportacion se recibe por URL:

```php
$tipo = $_GET['tipo'] ?? 'valoraciones';
```

Ejemplos:

```text
/admin/exportar.php?tipo=valoraciones
/admin/exportar.php?tipo=usuarios
/admin/exportar.php?tipo=comentarios
/admin/exportar.php?tipo=juegos
```

PHP envia cabeceras HTTP para que el navegador descargue un archivo:

```php
header('Content-Type: text/csv; charset=utf-8');
header('Content-Disposition: attachment; filename="rustyx_'.$tipo.'_'.date('Ymd_His').'.csv"');
```

Despues abre la salida del navegador como si fuera un archivo:

```php
$out = fopen('php://output', 'w');
```

Y escribe filas con:

```php
fputcsv($out, $r);
```

`fputcsv()` se encarga de convertir arrays PHP en lineas CSV validas. Tambien se escribe un BOM UTF-8 para que Excel abra correctamente acentos y caracteres especiales:

```php
fprintf($out, chr(0xEF).chr(0xBB).chr(0xBF));
```

## 7. Funcion destacada: trailers de YouTube embebidos

Los trailers se muestran en:

```text
web/rustyx/juego.php
```

Cada juego puede tener un campo `youtube_url` en la base de datos. Puede ser una URL completa o solo el ID del video.

La funcion que extrae el ID es:

```php
function youtubeId(?string $url): string {
    if (!$url) return '';
    if (strlen($url)===11 && preg_match('/^[a-zA-Z0-9_-]{11}$/',$url)) return $url;
    if (preg_match('/(?:v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/',$url,$m)) return $m[1];
    return '';
}
```

Acepta formatos como:

```text
dQw4w9WgXcQ
https://www.youtube.com/watch?v=dQw4w9WgXcQ
https://youtu.be/dQw4w9WgXcQ
```

Si se obtiene un ID valido, se crea un `iframe`:

```php
<iframe src="https://www.youtube-nocookie.com/embed/<?= h($ytId) ?>"
        title="Trailer <?= h($juego['titulo']) ?>"
        allowfullscreen loading="lazy"></iframe>
```

Se usa `youtube-nocookie.com` porque es la variante de embed con mejor privacidad. Tambien se usa `loading="lazy"` para que el video cargue solo cuando sea necesario.

## 8. Subida a InfinityFree

InfinityFree permite alojar webs PHP con MySQL/MariaDB. Segun su pagina oficial, ofrece PHP, MySQL/MariaDB, subdominios gratuitos, SSL y subida mediante FTP o File Manager.

### 8.1. Importante sobre Docker

En InfinityFree no se sube el `docker-compose.yml`, ni Nginx, ni contenedores. Solo se sube la web PHP.

Para este proyecto hay que subir el contenido de:

```text
web/rustyx/
```

al directorio publico de InfinityFree:

```text
htdocs/
```

El resultado deberia quedar asi:

```text
htdocs/index.php
htdocs/config.php
htdocs/juego.php
htdocs/admin/
htdocs/assets/
htdocs/css/
htdocs/partials/
```

No debe quedar asi:

```text
htdocs/web/rustyx/index.php
```

porque entonces la pagina principal no estaria en la raiz del sitio.

### 8.2. Crear base de datos

Pasos generales:

1. Entrar en el panel de InfinityFree.
2. Crear una base de datos MySQL.
3. Apuntar estos datos:
   - host MySQL
   - nombre de base de datos
   - usuario
   - contrasena
4. Entrar en phpMyAdmin desde InfinityFree.
5. Importar el archivo:

```text
sql/schema.sql
```

Si phpMyAdmin da problema con:

```sql
CREATE DATABASE
USE rustyxdb
```

se pueden quitar esas dos lineas, porque InfinityFree normalmente ya crea la base de datos desde el panel y phpMyAdmin trabaja dentro de ella.

### 8.3. Cambiar config.php para InfinityFree

En local, `config.php` apunta a la base de datos Docker:

```php
define('DB_HOST', '192.168.30.10');
define('DB_NAME', 'rustyxdb');
define('DB_USER', 'rustyxuser');
define('DB_PASS', 'rustyxpass');
```

En InfinityFree hay que cambiarlo por los datos reales del panel:

```php
define('DB_HOST', 'sqlXXX.infinityfree.com');
define('DB_NAME', 'if0_XXXXXXXX_rustyxdb');
define('DB_USER', 'if0_XXXXXXXX');
define('DB_PASS', 'TU_PASSWORD');
```

Los nombres exactos dependen de tu cuenta.

### 8.4. Subir archivos

La forma recomendada es FTP, por ejemplo con FileZilla.

Datos que necesitas:

- servidor FTP
- usuario FTP
- contrasena FTP
- carpeta remota `htdocs`

Pasos:

1. Abrir FileZilla.
2. Conectar con los datos FTP de InfinityFree.
3. Entrar en `htdocs`.
4. Subir todo el contenido de `web/rustyx/`.
5. Comprobar que `index.php` queda directamente dentro de `htdocs`.

### 8.5. Carpetas de subida

La web usa estas carpetas para archivos subidos:

```text
assets/avatars/
assets/games/
```

En InfinityFree deben existir y tener permisos de escritura suficientes. Si la subida de imagenes falla, revisar permisos desde FTP.

### 8.6. Limitaciones importantes

- InfinityFree free hosting no permite conectar a su MySQL desde programas externos como MySQL Workbench. La base de datos se usa desde PHP subido al hosting o desde phpMyAdmin.
- No hay que subir Docker.
- Las credenciales reales de la base de datos no deben publicarse en documentacion o repositorios publicos.
- Si se suben archivos grandes, es mejor usar FTP y no el File Manager.

## 9. Fuentes consultadas sobre InfinityFree

- InfinityFree indica soporte para PHP, MySQL/MariaDB, SSL y subida de webs propias por FTP o File Manager: https://www.infinityfree.com/
- Documentacion de InfinityFree sobre subida por FTP: https://forum.infinityfree.com/t/how-to-upload-files-with-ftp/49306
- Documentacion de inicio de cuenta en InfinityFree: https://forum.infinityfree.com/t/getting-started-with-a-new-web-hosting-account/49312
- Limitacion de acceso remoto a MySQL en hosting gratuito: https://forum.infinityfree.com/t/connecting-to-mysql-from-an-external-application/49339


