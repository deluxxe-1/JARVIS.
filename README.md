# ARIA - Tu Asistente de Inteligencia Artificial Personal

ARIA es un asistente personal impulsado por IA, diseñado para ofrecer asistencia inteligente mediante una arquitectura moderna, modular y eficiente. Emplea un backend robusto basado en Python y FastAPI, además de Ollama para los modelos generativos.

## Prerrequisitos

* Docker y Docker Compose
* Ollama (ejecutándose en la máquina anfitriona)
* Tailscale (opcional, para acceso remoto seguro)

## Inicio Rápido

1. Copia el archivo de variables de entorno:
   ```bash
   cp .env.example .env
   ```

2. Descarga los modelos necesarios para Ollama:
   ```bash
   make pull-models
   ```

3. Levanta los contenedores:
   ```bash
   make up
   ```

4. Ejecuta las migraciones de base de datos:
   ```bash
   make migrate
   ```

## Estructura del Proyecto

* `backend/`: Código fuente de la API en Python (FastAPI, SQLAlchemy, Celery).
* `docker-compose.yml`: Servicios principales (PostgreSQL, Redis, API, Worker).
* `docker-compose.dev.yml`: Sobrescrituras para desarrollo (hot-reload).
* `Makefile`: Comandos rápidos para facilitar el desarrollo.
