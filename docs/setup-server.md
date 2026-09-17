# Guía de Instalación y Configuración del Servidor de ARIA

Esta guía detalla paso a paso cómo preparar, desplegar y mantener la infraestructura completa del asistente personal ARIA sobre un servidor dedicado con Ubuntu Server.

---

## 1. Requisitos de Hardware

Para ejecutar de manera fluida los modelos locales (`qwen3:8b` y `bge-m3`), la base de datos PostgreSQL con `pgvector`, Redis y los servicios backend y worker en Python, se recomiendan las siguientes especificaciones:

| Componente | Mínimo | Recomendado |
|---|---|---|
| **CPU** | 4 núcleos (x86_64) | 8+ núcleos |
| **Memoria RAM** | 16 GB | 32 GB o superior |
| **GPU (VRAM)** | Opcional (CPU-only posible pero lento) | NVIDIA con al menos 8–12 GB VRAM (RTX 3060/4060 o superior) |
| **Almacenamiento** | 50 GB SSD (NVMe recomendado) | 100+ GB SSD (los modelos ocupan ~6-8 GB) |
| **Conexión de red** | 100 Mbps | 1 Gbps con conexión permanente a Internet |

> [!NOTE]
> Con una GPU NVIDIA de al menos 8 GB VRAM, Qwen3 8B (cuantizado Q4) y BGE-M3 se ejecutarán con aceleración total, ofreciendo tiempos de respuesta de menos de 1 segundo en inferencia y embeddings.

---

## 2. Instalación de Ubuntu Server

1. Descarga la imagen ISO de **Ubuntu Server 24.04 LTS** (o 22.04 LTS) desde el sitio oficial de Ubuntu.
2. Crea una unidad USB de arranque utilizando herramientas como Rufus o BalenaEtcher.
3. Inicia el servidor desde el USB y sigue el asistente:
   - Idioma y distribución de teclado.
   - Configuración de red: asigna una IP estática local o reserva por DHCP en el router.
   - Configuración de almacenamiento: particionado estándar en el disco SSD/NVMe.
   - Perfil de usuario: crea el usuario administrador (ej. `aria` o tu nombre de usuario).
   - Servidor OpenSSH: **marca la opción para instalar OpenSSH server** e importa tus claves SSH si las utilizas.
4. Finaliza la instalación, retira el medio USB y reinicia el servidor.
5. Conéctate vía SSH desde tu máquina de desarrollo:
   ```bash
   ssh usuario@<ip-local-servidor>
   ```

---

## 3. Instalación de Dependencias con el Script Automatizado

ARIA incluye un script que aprovisiona automáticamente el entorno:
- Actualización de paquetes del sistema.
- Instalación del motor Docker y Docker Compose plugin.
- Instalación de Ollama.
- Instalación de Tailscale.
- Detección de GPU NVIDIA e instalación del NVIDIA Container Toolkit (si aplica).

### Pasos:

1. Clona el repositorio de ARIA en el servidor:
   ```bash
   git clone <url-del-repositorio> aria
   cd aria
   ```
2. Otorga permisos de ejecución al script de configuración:
   ```bash
   chmod +x scripts/setup-server.sh scripts/pull-models.sh infra/backup/backup.sh
   ```
3. Ejecuta el script de aprovisionamiento:
   ```bash
   ./scripts/setup-server.sh
   ```
4. Cierra la sesión SSH y vuelve a iniciar sesión para aplicar los permisos del grupo `docker`:
   ```bash
   exit
   # Volver a conectar:
   ssh usuario@<ip-local-servidor>
   cd aria
   ```

---

## 4. Configuración de Tailscale

Tailscale permite que la aplicación Flutter (móvil/escritorio) se comunique con el servidor desde cualquier lugar mediante una VPN WireGuard cifrada sin abrir puertos al exterior.

1. Inicia Tailscale en el servidor:
   ```bash
   sudo tailscale up
   ```
2. Haz clic en el enlace de autenticación generado en pantalla para vincular el servidor a tu tailnet.
3. Anota la IP asignada (rango `100.x.y.z`):
   ```bash
   tailscale ip -4
   ```
4. Para más detalles, consulta la [Guía de Tailscale](file:///c:/Users/deluxXe/Documents/Personal%20Jarvis/aria/infra/tailscale/README.md).

---

## 5. Descarga de Modelos de Inteligencia Artificial

Ollama debe descargar los modelos necesarios:
- **`qwen3:8b`**: Modelo principal para razonamiento, chat y ejecución de herramientas (tool-calling).
- **`bge-m3`**: Modelo para generación de embeddings semánticos multilingües.

Ejecuta el script dedicado:
```bash
./scripts/pull-models.sh
```

Verifica que los modelos figuren en la lista de Ollama:
```bash
ollama list
```

---

## 6. Variables de Entorno

Copia la plantilla de configuración `.env.example` a un archivo `.env` en la raíz del proyecto:
```bash
cp .env.example .env
```

Edita `.env` con un editor de texto (ej. `nano .env`) y personaliza las siguientes variables:
```env
# Base de datos
DATABASE_URL=postgresql+asyncpg://aria:aria_secret@postgres:5432/aria
DATABASE_URL_SYNC=postgresql://aria:aria_secret@postgres:5432/aria
REDIS_URL=redis://redis:6379/0

# Ollama (se conecta al host físico mediante host.docker.internal)
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen3:8b
OLLAMA_EMBEDDING_MODEL=bge-m3

# Seguridad JWT
JWT_SECRET_KEY=genera_una_clave_segura_de_al_menos_32_caracteres
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=10080

# Credenciales de PostgreSQL
POSTGRES_USER=aria
POSTGRES_PASSWORD=aria_secret_cambia_esto
POSTGRES_DB=aria
LOG_LEVEL=INFO

# Claves externas de servicios (opcionales según las integraciones a usar)
GOOGLE_MAPS_API_KEY=
NEWS_API_KEY=
FINNHUB_API_KEY=
COINGECKO_API_URL=https://api.coingecko.com/api/v3
FCM_SERVER_KEY=
```

> [!TIP]
> Puedes generar una clave aleatoria para `JWT_SECRET_KEY` ejecutando:
> ```bash
> openssl rand -hex 32
> ```

---

## 7. Despliegue de los Servicios (Stack Docker)

Levanta los contenedores en segundo plano:
```bash
docker compose up -d --build
```
O usando el comando de `Makefile`:
```bash
make up
```

Comprueba que todos los contenedores (`postgres`, `redis`, `aria-backend`, `aria-worker`) estén en estado *healthy* o *running*:
```bash
docker compose ps
```

---

## 8. Ejecución de Migraciones de Base de Datos (Alembic)

Una vez que PostgreSQL esté activo y saludable, aplica las migraciones de base de datos para crear el esquema y las tablas correspondientes:

```bash
docker compose exec aria-backend alembic upgrade head
```
O bien:
```bash
make migrate
```

Si realizas cambios en los modelos de `backend/app/models/` en el futuro, puedes generar una nueva migración con:
```bash
docker compose exec aria-backend alembic revision --autogenerate -m "nombre_del_cambio"
```

---

## 9. Configuración de Copias de Seguridad Automatizadas

El script `infra/backup/backup.sh` realiza volcados comprimidos de PostgreSQL (`pg_dump | gzip`) en el directorio `/opt/aria/backups` y elimina automáticamente copias con más de 7 días de antigüedad.

1. Prepara el directorio de backups y permisos:
   ```bash
   sudo mkdir -p /opt/aria/backups
   sudo chown -R $USER:$USER /opt/aria/backups
   chmod +x /opt/aria/infra/backup/backup.sh
   ```
2. Configura una tarea programada en `crontab`:
   ```bash
   crontab -e
   ```
3. Añade la siguiente línea para ejecutar la copia todos los días a las 03:00 AM:
   ```cron
   0 3 * * * cd /ruta/hacia/aria && ./infra/backup/backup.sh >> /opt/aria/backups/backup.log 2>&1
   ```

---

## 10. Resolución de Problemas Comunes (Troubleshooting)

### 10.1 Ollama no responde desde los contenedores Docker
- **Causa:** `host.docker.internal` no resuelve o Ollama está escuchando únicamente en `127.0.0.1` en el host.
- **Solución:**
  1. Configura Ollama para escuchar en todas las interfaces del host creando una anulación en systemd:
     ```bash
     sudo systemctl edit ollama.service
     ```
  2. Añade:
     ```ini
     [Service]
     Environment="OLLAMA_HOST=0.0.0.0:11434"
     ```
  3. Reinicia el servicio:
     ```bash
     sudo systemctl daemon-reload
     sudo systemctl restart ollama
     ```

### 10.2 PostgreSQL rechaza conexiones o falla la extensión pgvector
- **Causa:** Contenedor aún en proceso de inicialización o permisos incorrectos.
- **Solución:**
  1. Revisa los logs del contenedor:
     ```bash
     docker compose logs postgres
     ```
  2. Verifica que la extensión `vector` esté activa conectándote directamente:
     ```bash
     docker compose exec postgres psql -U aria -d aria -c "CREATE EXTENSION IF NOT EXISTS vector;"
     ```

### 10.3 Celery Worker no procesa tareas o se reinicia
- **Causa:** Redis no está listo o la URL de conexión en `.env` no es accesible.
- **Solución:**
  1. Comprueba la salud de Redis:
     ```bash
     docker compose exec redis redis-cli ping
     ```
     Debe responder `PONG`.
  2. Inspecciona los logs del worker:
     ```bash
     docker compose logs -f aria-worker
     ```

### 10.4 Conflicto de puertos al iniciar Docker
- **Causa:** Ya hay instancias locales de PostgreSQL (5432) o Redis (6379) ejecutándose en el sistema operativo host.
- **Solución:**
  Detén los servicios locales con `sudo systemctl stop postgresql redis-server` o ajusta los puertos mapeados en `docker-compose.yml`.
