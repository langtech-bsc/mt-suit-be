# Backend Base 🚀

[![Built with FastAPI](https://img.shields.io/badge/Built%20with-FastAPI-green.svg?style=for-the-badge)](https://fastapi.tiangolo.com/)
[![Powered by Python](https://img.shields.io/badge/Powered%20by-Python%203.12-blue.svg?style=for-the-badge)](https://www.python.org/)
[![Docker Ready](https://img.shields.io/badge/Docker-Ready-blue.svg?style=for-the-badge&logo=docker)](https://www.docker.com/)

Bienvenido al Backend Base. Este proyecto es una base robusta y escalable para construir servicios API modernos utilizando FastAPI y un conjunto de herramientas de producción de primer nivel.

---

## ✨ Características Principales

Este proyecto no es solo un "Hola Mundo", está diseñado con las mejores prácticas para un entorno de producción:

*   **Framework Moderno**: Construido sobre **FastAPI** para un rendimiento excepcional y una documentación de API automática (Swagger y ReDoc).
*   **Base de Datos Asíncrona**: Utiliza **SQLAlchemy 2.0** con soporte completo para operaciones asíncronas, conectándose a una base de datos **PostgreSQL**.
*   **Migraciones de Base de Datos**: Integración con **Alembic** para gestionar la evolución del esquema de la base de datos de forma segura y versionada.
*   **Autenticación JWT**: Sistema completo de autenticación con tokens JWT, incluyendo login, logout y protección de endpoints.
*   **CRUD de Usuarios**: Sistema completo de gestión de usuarios con roles (superusuario) y permisos.
*   **Arquitectura Limpia**: Separación clara de responsabilidades con capas de modelos, schemas, CRUD y API.
*   **Listo para Producción**: Despliegue con **Docker** y **Gunicorn**, utilizando `uvicorn.workers` para gestionar múltiples procesos y aprovechar al máximo los recursos del servidor.
*   **Configuración Centralizada**: Gestión de la configuración a través de variables de entorno y un archivo `.env` con validación de datos gracias a **Pydantic Settings**.
*   **Logging Avanzado**:
    *   Logs estructurados y con **colores** en la consola para una fácil lectura.
    *   Integración con **Tamarin Logs Manager** para la centralización y análisis de logs en un servicio externo.
    *   Formateadores inteligentes que envían logs limpios (texto plano) a servicios externos.
*   **Sistema de Alertas Inteligente**:
    *   Notificaciones por correo electrónico para eventos críticos (fallos de conexión, errores en servicios externos) usando **Mailjet**.
    *   **Limitador de Tasa (Rate Limiter)** persistente que previene la inundación de correos en caso de errores repetitivos, protegiendo la reputación del remitente.
*   **Gestión de Dependencias**: Uso de **Poetry** para una gestión de dependencias declarativa, determinista y reproducible.

---

## ⚙️ Puesta en Marcha del Proyecto

Sigue estos pasos para levantar el proyecto en un entorno de producción utilizando Docker.

### Requisitos Previos

Asegúrate de tener instaladas las siguientes herramientas en tu sistema:
*   **Git**: Para clonar el repositorio.
*   **Docker**: Para construir y ejecutar la imagen del contenedor.
*   **Docker Compose**: Para orquestar el servicio definido en `docker-compose.yml`.

### Paso 1: Clonar el Repositorio

Abre tu terminal y clona el proyecto en tu máquina local.

```sh
git clone <URL_DEL_REPOSITORIO>
cd Base_Backend
```

### Paso 2: Configurar el Entorno

La configuración de la aplicación se gestiona a través de un archivo `.env`. Este archivo es ignorado por Git para proteger tus secretos.

1.  **Crea tu archivo de configuración** copiando el ejemplo proporcionado:
    ```sh
    cp .env.example .env
    ```

2.  **Edita el archivo `.env`** y rellena las variables con tus propios valores. A continuación se detalla cada sección:

    #### Docker & Gunicorn
    *   `WEB_PORT`: El puerto en tu máquina local que se mapeará al puerto 8000 del contenedor (ej: `8000`).
    *   `WORKERS`: El número de procesos trabajadores que Gunicorn lanzará para manejar las peticiones. Un buen punto de partida es `(2 * NÚMERO_DE_CPUS) + 1`.

    #### Conexión a la Base de Datos (PostgreSQL)
    *   `DB_HOST`: La dirección del servidor de tu base de datos.
    *   `DB_PORT`: El puerto de la base de datos (normalmente `5432`).
    *   `DB_USER`: El nombre de usuario para la conexión.
    *   `DB_PASSWORD`: La contraseña del usuario.
    *   `DB_NAME`: El nombre de la base de datos a la que se conectará la aplicación.

    #### Configuración de Logging
    *   `LOG_LEVEL`: Nivel mínimo de los logs a mostrar (`DEBUG`, `INFO`, `WARNING`, `ERROR`).
    *   `LOG_COLOR`: `true` para activar los logs con colores en la consola, `false` para texto plano.

    #### Tamarin Logs Manager
    *   `TAMARIN_LOGS_ENABLED`: Ponlo en `true` para activar el envío de logs a Tamarin.
    *   `TAMARIN_APP_TOKEN`: El token de aplicación único generado en la plataforma de Tamarin.

    #### Configuración de Mailjet (Notificaciones por Correo)
    *   `MAILJET_ENABLED`: Ponlo en `true` para activar el envío de correos.
    *   `MAILJET_API_KEY` y `MAILJET_API_SECRET`: Tus credenciales de la API de Mailjet.
    *   `MAILJET_SENDER_EMAIL` y `MAILJET_SENDER_NAME`: El remitente que aparecerá en los correos.
    *   `MAILJET_RECEIVER_EMAILS`: Una lista de correos de los destinatarios de las alertas, en formato de string JSON (ej: `["alerta1@dominio.com", "alerta2@dominio.com"]`).

    #### JWT & Seguridad
    *   `JWT_SECRET_KEY`: Clave secreta para firmar los tokens JWT. **MUY IMPORTANTE**: Genera una clave segura en producción usando `openssl rand -hex 32`.
    *   `JWT_ALGORITHM`: Algoritmo de encriptación para JWT (por defecto: `HS256`).
    *   `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`: Tiempo de expiración del token en minutos (por defecto: `30`).

### Paso 3: Setup Rápido con Makefile

El proyecto incluye un `Makefile` con comandos útiles. Para ver todos los comandos disponibles:

```sh
make help
```

**Setup completo inicial** (construir, levantar, migrar y crear superusuario):

```sh
make setup
```

**O manualmente paso a paso:**

1. **Construir y levantar servicios:**
   ```sh
   make up
   # O con docker compose directamente:
   docker compose up -d --build
   ```

2. **Aplicar migraciones:**
   ```sh
   make migrate
   # O:
   docker compose exec backend_app alembic upgrade head
   ```

3. **Crear superusuario:**
   ```sh
   make superuser
   # O:
   docker compose exec backend_app python create_superuser.py
   ```

### Paso 4: Verificar el Funcionamiento

1.  **Ver logs en tiempo real:**
    ```sh
    make logs-app
    # O:
    docker compose logs -f backend_app
    ```

2.  **Acceder a la API**:
    - Swagger UI: http://localhost:8000/docs
    - ReDoc: http://localhost:8000/redoc
    - Health check: http://localhost:8000/v1/health

---

## 🗃️ Migraciones de Base de Datos (Alembic)

Para gestionar cambios en el esquema de la base de datos, se utiliza Alembic.

**Con Makefile:**

```sh
# Aplicar migraciones pendientes
make migrate

# Crear nueva migración
make migrate-create msg="descripcion del cambio"

# Ver historial
make migrate-history

# Revertir última migración
make migrate-downgrade
```

**Con comandos directos:**

```sh
# Aplicar migraciones
docker compose exec backend_app alembic upgrade head

# Crear migración
docker compose exec backend_app alembic revision --autogenerate -m "descripcion"

# Ver historial
docker compose exec backend_app alembic history
```

---

## 👤 Sistema de Usuarios y Autenticación

El proyecto incluye un sistema completo de autenticación JWT y gestión de usuarios.

### Estructura del Proyecto

```
app/
├── api/                  # Endpoints de la API
│   ├── auth.py          # Login y logout
│   ├── users.py         # CRUD de usuarios
│   └── deps.py          # Dependencias de autenticación
├── models/              # Modelos de SQLAlchemy
│   └── user.py          # Modelo de Usuario
├── schemas/             # Schemas de Pydantic
│   └── user.py          # Schemas de Usuario y Token
├── crud/                # Operaciones CRUD
│   └── user.py          # Operaciones de usuario
└── core/
    └── security.py      # Utilidades de seguridad (JWT, hashing)
```

### Crear el Primer Superusuario

Después de aplicar las migraciones, crea un superusuario para administrar el sistema:

```sh
docker compose exec backend_app python create_superuser.py
```

O sin Docker:

```sh
python create_superuser.py
```

### Endpoints Disponibles

Ver el archivo [API_USAGE.md](API_USAGE.md) para una guía completa de todos los endpoints disponibles.

**Endpoints principales:**

- `POST /v1/users` - Registrar nuevo usuario (público)
- `POST /v1/auth/login` - Login y obtener token JWT
- `POST /v1/auth/logout` - Logout
- `GET /v1/users/me` - Obtener perfil del usuario autenticado
- `PUT /v1/users/me` - Actualizar perfil del usuario autenticado
- `GET /v1/users` - Listar usuarios (solo superusuarios)
- `GET /v1/users/{id}` - Obtener usuario por ID (solo superusuarios)
- `PUT /v1/users/{id}` - Actualizar usuario (solo superusuarios)
- `DELETE /v1/users/{id}` - Eliminar usuario (solo superusuarios)

---

## 🐳 Docker y Comandos Útiles

El proyecto incluye un `Makefile` con comandos útiles para facilitar el desarrollo y mantenimiento.

### Comandos Más Usados

```sh
make help          # Ver todos los comandos disponibles
make up            # Levantar servicios
make down          # Detener servicios
make restart       # Reiniciar servicios
make logs          # Ver logs de todos los servicios
make logs-app      # Ver logs solo de la aplicación
make shell         # Abrir shell en el contenedor
make db-shell      # Abrir shell de PostgreSQL
make migrate       # Aplicar migraciones
make superuser     # Crear superusuario
make clean         # Limpiar contenedores y volúmenes
```

### Dockerfile Optimizado

El `Dockerfile` utiliza:
- **Multi-stage build** para imágenes más pequeñas (~200-300MB)
- **Usuario no-root** para mejor seguridad
- **Health checks** automáticos
- **Imagen slim** de Python 3.12

### Docker Compose

Incluye dos servicios:
- **db**: PostgreSQL 16 Alpine con volumen persistente
- **backend_app**: FastAPI con Gunicorn + Uvicorn workers

Ver [DOCKER_GUIDE.md](DOCKER_GUIDE.md) para más detalles sobre Docker.

---

## 📚 Documentación Adicional

- [API_USAGE.md](API_USAGE.md) - Guía completa de uso de la API con ejemplos
- [DOCKER_GUIDE.md](DOCKER_GUIDE.md) - Guía detallada de Docker y despliegue
- [CHANGELOG.md](CHANGELOG.md) - Registro de cambios y mejoras implementadas

---

## 🛠️ Comandos de Desarrollo

### Con Poetry (desarrollo local sin Docker)

```sh
# Instalar dependencias
poetry install

# Activar entorno virtual
poetry shell

# Ejecutar servidor de desarrollo
uvicorn app.main:app --reload

# Aplicar migraciones
alembic upgrade head

# Crear superusuario
python create_superuser.py
```

### Testing y Calidad de Código

```sh
# Ejecutar tests (cuando se implementen)
make test

# Linter
make lint

# Formatear código
make format
```

# Acknowledgements

This work was funded by the Ministerio para la Transformación Digital y de la Función Pública - Funded by EU – NextGenerationEU within the framework of the [project ILENIA] (https://proyectoilenia.es/) with reference 2022/TL22/00215337 
---

## 🚀 Despliegue en Producción

### Checklist de Seguridad

- [ ] Cambiar `JWT_SECRET_KEY` (usar `openssl rand -hex 32`)
- [ ] Usar contraseñas fuertes para base de datos
- [ ] Configurar `SWAGGER_ENABLED=false` o proteger con credenciales
- [ ] Configurar CORS apropiadamente
- [ ] Ajustar número de workers según CPUs
- [ ] Configurar backup automático de base de datos
- [ ] Configurar logs persistentes
- [ ] Usar volúmenes persistentes para datos críticos
- [ ] Configurar monitoreo y alertas

### Variables Críticas para Producción

```bash
# Generar clave segura
JWT_SECRET_KEY=$(openssl rand -hex 32)

# Ajustar workers según CPUs
WORKERS=$((2 * $(nproc) + 1))

# Logging
LOG_LEVEL=INFO
LOG_TO_FILE=true

# Seguridad
SWAGGER_ENABLED=false  # O proteger con USER_SWAGGER/PASSWORD_SWAGGER
```
