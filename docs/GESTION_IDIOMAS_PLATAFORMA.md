# Gestión de Idiomas Soportados a Nivel de Plataforma

## Índice

1. [Descripción General](#descripción-general)
2. [Arquitectura de la Plataforma](#arquitectura-de-la-plataforma)
3. [Configuración Global](#configuración-global)
4. [Sistema de Rutas y Endpoints](#sistema-de-rutas-y-endpoints)
5. [Control de Acceso y Permisos](#control-de-acceso-y-permisos)
6. [Ciclo de Vida de Idiomas](#ciclo-de-vida-de-idiomas)
7. [Integración con Servicios](#integración-con-servicios)
8. [Deployment y Configuración](#deployment-y-configuración)
9. [Monitoreo y Observabilidad](#monitoreo-y-observabilidad)
10. [Escalabilidad y Rendimiento](#escalabilidad-y-rendimiento)
11. [Casos de Uso Empresariales](#casos-de-uso-empresariales)
12. [Mejores Prácticas](#mejores-prácticas)

---

## Descripción General

La **gestión de idiomas a nivel de plataforma** es el sistema centralizado que controla qué idiomas están disponibles para todos los servicios de traducción, proporcionando una capa de gobierno y control sobre la oferta multiidioma de la organización.

### Características del Sistema

- **Gobernanza Centralizada**: Un solo punto de control para todos los idiomas soportados
- **Multi-tenant Ready**: Preparado para escenarios de múltiples organizaciones
- **Auditoría Completa**: Registro de todas las operaciones sobre idiomas
- **Zero-Downtime**: Activación/desactivación sin interrupciones
- **API-First**: Gestión completamente automatizable vía API
- **Role-Based Access**: Control granular basado en roles y permisos

### Alcance

El sistema de gestión de idiomas afecta a:

1. **Endpoints de Traducción**: Validación de idiomas disponibles
2. **Providers de IA**: Configuración de idiomas soportados por modelo
3. **Interfaz de Usuario**: Selectores y listas de idiomas
4. **Reportes y Analytics**: Métricas por idioma
5. **Configuración de Clientes**: Restricciones por organización/usuario

---

## Arquitectura de la Plataforma

### Vista General del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                      INTERNET / CLIENTES                         │
│  (Web Apps, Mobile Apps, API Consumers, Admin Panels)          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                       LOAD BALANCER                              │
│  (NGINX, ALB, CloudFlare, etc.)                                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Application                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    app/main.py                            │  │
│  │  - CORS Middleware                                        │  │
│  │  - Exception Handlers                                     │  │
│  │  - API Router Registration                                │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │                                        │
│  ┌──────────────────────▼───────────────────────────────────┐  │
│  │              app/router/endpoints.py                      │  │
│  │  API Router (Prefix: /v1)                                │  │
│  │  ├─ /health          (Health Check)                       │  │
│  │  ├─ /v1/auth        (Authentication)                      │  │
│  │  ├─ /v1/users       (User Management)                     │  │
│  │  ├─ /v1/roles       (Roles & Permissions)                 │  │
│  │  ├─ /v1/translations (Translation Services) ◄─────────┐  │  │
│  │  └─ /v1/secom       (SECOM Integration)               │  │  │
│  └────────────────────────────────────────────────────────┼──┘  │
│                                                            │     │
│  ┌────────────────────────────────────────────────────────▼──┐  │
│  │          app/api/translations.py                         │  │
│  │  Translation Router:                                     │  │
│  │  ├─ GET    /languages        (List languages - PUBLIC)  │  │
│  │  ├─ POST   /languages        (Create language)          │  │
│  │  ├─ GET    /languages/{id}   (Get language)             │  │
│  │  ├─ PUT    /languages/{id}   (Update language)          │  │
│  │  ├─ PATCH  /languages/{id}/toggle (Toggle active)       │  │
│  │  ├─ DELETE /languages/{id}   (Delete language)          │  │
│  │  ├─ GET    /providers        (List providers)           │  │
│  │  ├─ POST   /translate        (Translate text)           │  │
│  │  └─ ...                                                  │  │
│  └────────────────────┬─────────────────────────────────────┘  │
│                       │                                          │
│  ┌────────────────────▼─────────────────────────────────────┐  │
│  │         app/api/deps.py (Dependencies)                   │  │
│  │  - get_session (DB Session)                              │  │
│  │  - get_current_user (JWT Auth)                           │  │
│  │  - get_current_active_user                               │  │
│  │  - PermissionChecker (translations:manage)               │  │
│  └────────────────────┬─────────────────────────────────────┘  │
└────────────────────────┼──────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   CRUD Layer │  │ Service Layer│  │ Validation   │
│              │  │              │  │              │
│ translation.py│ │ Translation  │  │ Pydantic     │
│              │  │   Services   │  │  Schemas     │
│ - create     │  │              │  │              │
│ - read       │  │ - HF Client  │  │ - Language   │
│ - update     │  │ - Grammar    │  │   Create     │
│ - delete     │  │ - PostEdit   │  │ - Language   │
│ - activate   │  │              │  │   Update     │
└──────┬───────┘  └──────────────┘  └──────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│                   PostgreSQL Database                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  languages                                                │  │
│  │  - id, code, name, native_name                           │  │
│  │  - is_active, sort_order                                 │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │  translation_providers                                    │  │
│  │  - id, name, endpoint, encrypted_api_key                 │  │
│  │  - input_language_ids, output_language_ids               │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │  translations                                             │  │
│  │  - id, source_language_id, target_language_id            │  │
│  │  - source_text, translated_text, user_id                 │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │  users, roles, permissions, role_permissions             │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Flujo de Datos Completo

#### Flujo 1: Usuario Público Lista Idiomas Disponibles

```
1. Cliente Frontend (Web/Mobile)
       │
       ├─ GET https://api.example.com/v1/translations/languages?only_active=true
       │
       ▼
2. NGINX/Load Balancer
       │
       ├─ Forward to FastAPI worker
       │
       ▼
3. FastAPI Application (app/main.py)
       │
       ├─ CORS Middleware ✓
       ├─ Routing to app/router/endpoints.py
       │
       ▼
4. API Router (/v1/translations)
       │
       ├─ Route to app/api/translations.py:list_languages()
       │  (ENDPOINT PÚBLICO - No requiere autenticación)
       │
       ▼
5. Endpoint Handler (app/api/translations.py:193-202)
       │
       ├─ Obtener session DB: get_session()
       ├─ Query params: skip=0, limit=100, only_active=True
       │
       ▼
6. CRUD Layer (app/crud/translation.py:179-190)
       │
       ├─ get_languages(db, skip=0, limit=100, only_active=True)
       ├─ SQL: SELECT * FROM languages
       │       WHERE is_active = true
       │       ORDER BY sort_order, name
       │       OFFSET 0 LIMIT 100
       │
       ▼
7. PostgreSQL Database
       │
       ├─ Execute query
       ├─ Return rows
       │
       ▼
8. Pydantic Serialization
       │
       ├─ Convert SQLAlchemy models → LanguageResponse schemas
       ├─ JSON serialization
       │
       ▼
9. HTTP Response
       │
       └─ 200 OK
          Content-Type: application/json
          Body: [
            {"id": 1, "code": "en", "name": "English", "native_name": "English", ...},
            {"id": 2, "code": "es", "name": "Spanish", "native_name": "Español", ...},
            ...
          ]
```

#### Flujo 2: Administrador Crea Nuevo Idioma

```
1. Admin Panel/CLI
       │
       ├─ POST https://api.example.com/v1/translations/languages
       │  Headers: Authorization: Bearer <JWT_TOKEN>
       │  Body: {"code": "ca", "name": "Catalan", "native_name": "Català", "sort_order": 10}
       │
       ▼
2. Load Balancer → FastAPI
       │
       ▼
3. CORS + Exception Handlers
       │
       ▼
4. API Router → translations.create_language()
       │
       ▼
5. Dependency Injection (app/api/deps.py)
       │
       ├─ get_session() → AsyncSession
       ├─ get_current_active_user() → User
       │   ├─ JWT Token decode
       │   ├─ Validate user exists
       │   └─ Check is_active = true
       │
       ├─ PermissionChecker(["translations:manage"])
       │   ├─ Check user.is_superuser OR
       │   └─ Check user has permission "translations:manage"
       │
       │   Si falla → 403 Forbidden: "Not enough permissions"
       │
       ▼
6. Endpoint Handler (app/api/translations.py:205-218)
       │
       ├─ Validar schema: LanguageCreate (Pydantic)
       │   ├─ code: min 2, max 10 chars
       │   ├─ name: min 1, max 100 chars
       │   ├─ native_name: min 1, max 100 chars
       │   └─ sort_order: >= 0
       │
       ├─ Verificar unicidad:
       │   existing = await get_language_by_code(db, "ca")
       │   if existing → 400 Bad Request: "Language with code 'ca' already exists"
       │
       ▼
7. CRUD Layer (app/crud/translation.py:144-150)
       │
       ├─ create_language(db, language_data)
       ├─ SQL: INSERT INTO languages (code, name, native_name, sort_order, is_active, created_at, updated_at)
       │       VALUES ('ca', 'Catalan', 'Català', 10, true, NOW(), NOW())
       │       RETURNING *
       │
       ▼
8. Database Commit
       │
       ├─ COMMIT transaction
       ├─ Refresh model (get generated id, timestamps)
       │
       ▼
9. Response
       │
       └─ 201 Created
          Location: /v1/translations/languages/15
          Body: {"id": 15, "code": "ca", "name": "Catalan", ...}
```

#### Flujo 3: Usuario Solicita Traducción (Validación de Idiomas)

```
1. Cliente
       │
       ├─ POST /v1/translations/translate
       │  Body: {"text": "Hello", "source_language_code": "en", "target_language_code": "es"}
       │
       ▼
2. FastAPI → Translation Endpoint
       │
       ├─ Auth: get_current_active_user() ✓
       ├─ Permissions: PermissionChecker(["translations:translate"]) ✓
       │
       ▼
3. Language Validation (app/api/translations.py:284-298)
       │
       ├─ source_lang = await get_language_by_code(db, "en")
       │   ├─ SQL: SELECT * FROM languages WHERE code = 'en'
       │   └─ if not source_lang OR not source_lang.is_active:
       │          → 400 Bad Request: "Source language 'en' not available"
       │
       ├─ target_lang = await get_language_by_code(db, "es")
       │   └─ if not target_lang OR not target_lang.is_active:
       │          → 400 Bad Request: "Target language 'es' not available"
       │
       ▼
4. Translation Service Factory
       │
       ├─ Get provider (default or specified)
       ├─ Decrypt API key
       ├─ Initialize HuggingFaceTranslationService
       │
       ▼
5. Execute Translation
       │
       ├─ Call Hugging Face API
       ├─ Process response
       │
       ▼
6. Save to History
       │
       ├─ INSERT INTO translations (
       │       provider_id, source_language_id, target_language_id,
       │       source_text, translated_text, character_count, user_id
       │   )
       │
       ▼
7. Response
       │
       └─ 200 OK
          Body: {
            "translated_text": "Hola",
            "source_language": {"id": 1, "code": "en", ...},
            "target_language": {"id": 2, "code": "es", ...},
            "character_count": 5,
            "created_at": "2025-12-21T10:00:00Z"
          }
```

---

## Configuración Global

### Archivo de Configuración

**Ubicación**: `app/core/config.py`

El sistema utiliza **Pydantic Settings** para gestión de configuración basada en variables de entorno.

#### Settings Relevantes para Idiomas

```python
class Settings(BaseSettings):
    """Global app settings loaded from environment."""

    # App Identity
    app_name: str = "Backend Base"
    app_version: str = "0.1.0"

    # CORS Configuration (afecta acceso público a /languages)
    cors_enabled: bool = True
    cors_origins: list[str] = ["*"]  # En producción: ["https://app.example.com"]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    # JWT & Security
    jwt_secret_key: SecretStr = "your-secret-key-change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    # Database
    database_url: str | None = None
    database_host: str = "localhost"
    database_port: int = 5432
    database_user: str = "postgres"
    database_password: SecretStr = "postgres"
    database_name: str = "backend_app"
    database_echo: bool = False
    database_pool_size: int = 5
    database_max_overflow: int = 10

    # Logging
    log_level: str = "DEBUG"
    log_to_file: bool = True
    log_json: bool = False
    log_color: bool = True
```

### Variables de Entorno

**Archivo**: `.env`

```bash
# ==================== APPLICATION ====================
APP_NAME="BSC Translation Platform"
APP_VERSION="1.0.0"
WORKERS=4

# ==================== CORS ====================
CORS_ENABLED=true
CORS_ORIGINS=https://app.example.com,https://admin.example.com
CORS_ALLOW_CREDENTIALS=true

# ==================== JWT SECURITY ====================
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production-256-bits
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# ==================== ENCRYPTION ====================
# Para encriptar API keys de providers
ENCRYPTION_KEY=D4xdS3PwWl5jxNmhpyKMBuBSgqbxEmO_wfLRZWLSR5o=

# ==================== DATABASE ====================
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/translations_db
# O usando componentes separados:
DB_HOST=db.example.com
DB_PORT=5432
DB_USER=translations_user
DB_PASSWORD=secure_password_here
DB_NAME=translations_production
DB_ECHO=false
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40

# ==================== LOGGING ====================
LOG_LEVEL=INFO
LOG_TO_FILE=true
LOG_JSON=true  # Para producción (mejor para parsers)
LOG_COLOR=false
LOG_DIR=/var/log/translations
LOG_FILENAME=app.log

# ==================== SWAGGER DOCS ====================
SWAGGER_ENABLED=true
USER_SWAGGER=admin
PASSWORD_SWAGGER=secure_docs_password

# ==================== MONITORING (Tamarin) ====================
TAMARIN_LOGS_ENABLED=true
TAMARIN_APP_NAME=BSC Translation Platform
TAMARIN_APP_TOKEN=your_tamarin_token_here
TAMARIN_API_URL=https://tamarin.macaqueconsulting.com/v1/tamarin/logs

# ==================== EMAIL (Mailjet) ====================
MAILJET_ENABLED=true
MAILJET_API_KEY=your_mailjet_api_key
MAILJET_API_SECRET=your_mailjet_api_secret
MAILJET_SENDER_EMAIL=noreply@example.com
MAILJET_SENDER_NAME=BSC Translation Platform
MAILJET_RECEIVER_EMAILS=admin@example.com,ops@example.com
```

### Generación de Claves

#### JWT Secret Key

```bash
# Generar clave segura de 256 bits
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### Encryption Key (para API keys)

```bash
# Generar clave compatible con Fernet (AES)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Configuración por Entorno

#### Development (.env.development)

```bash
APP_NAME="BSC Translation Platform [DEV]"
DATABASE_URL=postgresql+asyncpg://dev:dev@localhost:5432/translations_dev
LOG_LEVEL=DEBUG
LOG_JSON=false
LOG_COLOR=true
SWAGGER_ENABLED=true
USER_SWAGGER=
PASSWORD_SWAGGER=
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

#### Staging (.env.staging)

```bash
APP_NAME="BSC Translation Platform [STAGING]"
DATABASE_URL=postgresql+asyncpg://staging_user:${DB_PASSWORD}@db-staging.internal:5432/translations_staging
LOG_LEVEL=INFO
LOG_JSON=true
LOG_COLOR=false
SWAGGER_ENABLED=true
USER_SWAGGER=staging_admin
PASSWORD_SWAGGER=${STAGING_DOCS_PASSWORD}
CORS_ORIGINS=https://staging.example.com
TAMARIN_LOGS_ENABLED=true
```

#### Production (.env.production)

```bash
APP_NAME="BSC Translation Platform"
DATABASE_URL=postgresql+asyncpg://prod_user:${DB_PASSWORD}@db-prod.internal:5432/translations_production
LOG_LEVEL=WARNING
LOG_JSON=true
LOG_COLOR=false
SWAGGER_ENABLED=false  # O protegido con usuario/contraseña
CORS_ORIGINS=https://app.example.com,https://api.example.com
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=100
TAMARIN_LOGS_ENABLED=true
MAILJET_ENABLED=true
```

---

## Sistema de Rutas y Endpoints

### Estructura de Routing

**Archivo**: `app/router/endpoints.py`

```python
from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.roles import router as roles_router
from app.api.translations import router as translations_router
from app.api.users import router as users_router
from app.router.health import router as health_router
from app.router.secom import router as secom_router

# Router principal con prefijo /v1
api_router = APIRouter(prefix="/v1")

routers = [
    (health_router, "", "Health"),
    (auth_router, "auth", "Authentication"),
    (users_router, "users", "Users"),
    (roles_router, "roles", "Roles & Permissions"),
    (translations_router, "translations", "Translation Services"),  # ◄── Idiomas aquí
    (secom_router, "secom", "SECOM"),
]

for router, prefix, tag in routers:
    final_prefix = f"/{prefix}" if prefix else ""
    api_router.include_router(router, prefix=final_prefix, tags=[tag])
```

### Endpoints de Idiomas

**Archivo**: `app/api/translations.py`

**Base URL**: `https://api.example.com/v1/translations`

| Método | Endpoint | Autenticación | Permisos | Descripción |
|--------|----------|---------------|----------|-------------|
| **GET** | `/languages` | ❌ No requerida (público) | Ninguno | Lista idiomas activos |
| **POST** | `/languages` | ✅ JWT Token | `translations:manage` | Crear nuevo idioma |
| **GET** | `/languages/{id}` | ❌ No requerida (público) | Ninguno | Obtener idioma por ID |
| **PUT** | `/languages/{id}` | ✅ JWT Token | `translations:manage` | Actualizar idioma |
| **PATCH** | `/languages/{id}/toggle` | ✅ JWT Token | `translations:manage` | Activar/desactivar |
| **DELETE** | `/languages/{id}` | ✅ JWT Token | `translations:manage` | Eliminar idioma |

### URL Completas de Ejemplo

```
# Producción
https://api.translation.bsc.es/v1/translations/languages
https://api.translation.bsc.es/v1/translations/languages/15
https://api.translation.bsc.es/v1/translations/languages/15/toggle?is_active=true

# Staging
https://staging-api.translation.bsc.es/v1/translations/languages

# Development
http://localhost:8000/v1/translations/languages
```

### Documentación Interactiva (Swagger)

```
# Swagger UI
https://api.example.com/docs

# ReDoc
https://api.example.com/redoc

# OpenAPI JSON
https://api.example.com/openapi.json
```

**Protección de Documentación** (si está habilitada):

```python
# En app/main.py
if settings.swagger_enabled and settings.user_swagger and settings.password_swagger:
    # Requiere HTTP Basic Auth
    # Usuario: settings.user_swagger
    # Password: settings.password_swagger
```

---

## Control de Acceso y Permisos

### Modelo de Permisos

El sistema utiliza **RBAC (Role-Based Access Control)** con tres niveles:

```
Users ──► Roles ──► Permissions
```

### Permisos Relevantes para Idiomas

**Tabla**: `permissions`

| Scope | Permission | Descripción |
|-------|------------|-------------|
| `translations` | `translations:read` | Leer configuración de traducción |
| `translations` | `translations:translate` | Usar servicios de traducción |
| `translations` | `translations:manage` | Gestionar idiomas y providers |

### Roles Predefinidos

**Tabla**: `roles`

| Rol | Permisos | Uso |
|-----|----------|-----|
| **Superuser** | Todos | Usuario root del sistema |
| **Admin** | `translations:*`, `users:*`, `roles:*` | Administradores de plataforma |
| **Member** | `translations:read`, `translations:translate` | Usuarios regulares |

### Asignación de Permisos

**Dependencia**: `app/api/deps.py:PermissionChecker`

```python
from app.api.deps import PermissionChecker

# Endpoint que requiere gestión de idiomas
@router.post("/languages")
async def create_language(
    language: LanguageCreate,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(PermissionChecker(["translations:manage"]))],
):
    """Create a new language (requires translations:manage permission)."""
    # ...
```

### Flujo de Autorización

```
1. Request con JWT Token
       │
       ▼
2. Dependency: get_current_user()
       │
       ├─ Decode JWT token
       ├─ Extract username from token
       ├─ Query: SELECT * FROM users WHERE username = ?
       │
       ├─ Si usuario no existe → 401 Unauthorized
       │
       ▼
3. Dependency: get_current_active_user()
       │
       ├─ Check user.is_active == True
       ├─ Si no activo → 400 Bad Request: "Inactive user"
       │
       ▼
4. Dependency: PermissionChecker(["translations:manage"])
       │
       ├─ Si user.is_superuser → ALLOW ✓
       │
       ├─ Si NO es superuser:
       │   ├─ Query user permissions:
       │   │   SELECT p.scope, p.permission
       │   │   FROM permissions p
       │   │   JOIN role_permissions rp ON rp.permission_id = p.id
       │   │   JOIN user_roles ur ON ur.role_id = rp.role_id
       │   │   WHERE ur.user_id = ?
       │   │
       │   ├─ Build set: {"translations:read", "translations:translate", "translations:manage"}
       │   │
       │   └─ Check "translations:manage" in set
       │       ├─ Si NO tiene permiso → 403 Forbidden: "Not enough permissions"
       │       └─ Si tiene permiso → ALLOW ✓
       │
       ▼
5. Execute Endpoint Logic
```

### Ejemplos de Control de Acceso

#### Endpoint Público (Sin autenticación)

```python
@router.get("/languages", response_model=list[LanguageResponse])
async def list_languages(
    db: Annotated[AsyncSession, Depends(get_session)],
    # NO hay dependencia de autenticación
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    only_active: bool = Query(True),
):
    """List all languages (PUBLIC ENDPOINT)."""
    languages = await crud_translation.get_languages(db, skip, limit, only_active)
    return languages
```

#### Endpoint Protegido (Solo administradores)

```python
@router.post("/languages", response_model=LanguageResponse, status_code=201)
async def create_language(
    language: LanguageCreate,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: Annotated[User, Depends(PermissionChecker(["translations:manage"]))],
):
    """Create a new language (ADMIN ONLY)."""
    # Solo usuarios con permiso "translations:manage" pueden ejecutar esto
    # ...
```

### Gestión de Permisos vía API

#### Asignar Rol a Usuario

```bash
POST /v1/roles/{role_id}/users/{user_id}
Authorization: Bearer <superuser_token>
```

#### Crear Permiso Personalizado

```bash
POST /v1/roles/permissions
Authorization: Bearer <superuser_token>

{
  "scope": "translations",
  "permission": "translations:audit",
  "description": "View translation audit logs"
}
```

#### Asignar Permiso a Rol

```bash
POST /v1/roles/{role_id}/permissions/{permission_id}
Authorization: Bearer <superuser_token>
```

---

## Ciclo de Vida de Idiomas

### Estados de un Idioma

```
┌─────────────────────────────────────────────────────────────────┐
│                    CICLO DE VIDA DE IDIOMA                       │
└─────────────────────────────────────────────────────────────────┘

1. CREACIÓN
   ├─ POST /languages
   ├─ Estado inicial: is_active = true
   ├─ Asignado: id (auto-increment), created_at, updated_at
   └─ Visible en: GET /languages?only_active=true ✓

2. ACTIVO (is_active = true)
   ├─ Visible para usuarios finales
   ├─ Disponible en selectores de idioma
   ├─ Validación de traducción: PASA ✓
   └─ Reportes: Incluido

3. DESACTIVADO (is_active = false)
   ├─ NO visible para usuarios finales
   ├─ NO disponible en selectores
   ├─ Validación de traducción: FALLA ❌
   │   ("Source language 'xx' not available")
   ├─ Visible solo en: GET /languages?only_active=false
   └─ Historial: Preservado (traducciones antiguas intactas)

4. MODIFICACIÓN
   ├─ PUT /languages/{id}
   ├─ Campos modificables: name, native_name, sort_order, is_active
   ├─ Campo INMUTABLE: code (no se puede cambiar después de creado)
   └─ updated_at: Actualizado automáticamente

5. ELIMINACIÓN
   ├─ DELETE /languages/{id}
   ├─ Efecto: HARD DELETE (registro eliminado permanentemente)
   ├─ Restricción: Foreign Key Constraint
   │   └─ Si existen traducciones → Error 500 (Integrity Error)
   ├─ Recomendación: Usar DESACTIVACIÓN en lugar de eliminación
   └─ Pérdida de datos: ⚠️ IRREVERSIBLE
```

### Diagrama de Estados

```
     ┌─────────────────────┐
     │    [NO EXISTE]      │
     └──────────┬──────────┘
                │
          POST /languages
                │
                ▼
     ┌─────────────────────┐
     │  CREADO & ACTIVO    │◄──────────────────┐
     │  (is_active=true)   │                   │
     └──────────┬──────────┘                   │
                │                              │
                │  PATCH /toggle               │
                │  ?is_active=false            │
                │                         PUT /toggle
                ▼                        ?is_active=true
     ┌─────────────────────┐                   │
     │    DESACTIVADO      │───────────────────┘
     │  (is_active=false)  │
     └──────────┬──────────┘
                │
                │  DELETE /languages/{id}
                │  (No recomendado)
                ▼
     ┌─────────────────────┐
     │    [ELIMINADO]      │
     │  ⚠️ IRREVERSIBLE     │
     └─────────────────────┘
```

### Políticas Recomendadas

#### Política 1: Soft Delete (Desactivación)

```bash
# ✅ RECOMENDADO: Desactivar idioma
PATCH /v1/translations/languages/15/toggle?is_active=false

# Ventajas:
# - Preserva historial de traducciones
# - Reversible instantáneamente
# - No rompe relaciones de base de datos
# - Permite auditoría completa
```

#### Política 2: Hard Delete (Solo para errores)

```bash
# ⚠️ USAR SOLO PARA CORRECCIONES DE ERRORES
DELETE /v1/translations/languages/15

# Casos válidos:
# - Idioma creado por error (sin traducciones)
# - Código ISO incorrecto registrado
# - Duplicado accidental

# NUNCA usar si:
# - Existen traducciones asociadas
# - El idioma ha estado en producción
# - Hay auditoría que preservar
```

#### Política 3: Reactivación

```bash
# Reactivar idioma previamente desactivado
PATCH /v1/translations/languages/15/toggle?is_active=true

# Escenario: Idioma estuvo en mantenimiento temporal
```

---

## Integración con Servicios

### Relación con Translation Providers

Cada provider especifica qué idiomas soporta:

```json
{
  "id": 1,
  "name": "Salamandra 2B Multi",
  "provider_type": "huggingface",
  "input_language_ids": [1, 2, 3, 4, 5],   // en, es, ca, fr, de
  "output_language_ids": [1, 2, 3, 4, 5]
}
```

#### Script: Sincronizar Provider con Todos los Idiomas Activos

```bash
#!/bin/bash
# sync_provider_languages.sh

API_BASE="https://api.example.com/v1"
TOKEN="<admin_token>"
PROVIDER_ID=1

# Obtener todos los idiomas activos
LANG_IDS=$(curl -s "$API_BASE/translations/languages?only_active=true" | jq '[.[].id]')

echo "Idiomas activos: $LANG_IDS"

# Actualizar provider
curl -X PUT "$API_BASE/translations/providers/$PROVIDER_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"input_language_ids\": $LANG_IDS,
    \"output_language_ids\": $LANG_IDS
  }"

echo "✅ Provider $PROVIDER_ID actualizado con $(echo $LANG_IDS | jq 'length') idiomas"
```

### Relación con Translation History

Cada traducción registra los idiomas usados:

```sql
-- Tabla: translations
CREATE TABLE translations (
    id BIGSERIAL PRIMARY KEY,
    provider_id BIGINT REFERENCES translation_providers(id) ON DELETE CASCADE,
    source_language_id BIGINT REFERENCES languages(id) ON DELETE CASCADE,  -- ◄── Referencia
    target_language_id BIGINT REFERENCES languages(id) ON DELETE CASCADE,  -- ◄── Referencia
    source_text TEXT NOT NULL,
    translated_text TEXT NOT NULL,
    character_count INTEGER NOT NULL,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Implicación**: Si se elimina un idioma con historial, se produce error de foreign key constraint.

---

## Deployment y Configuración

### Docker Compose

```yaml
version: '3.8'

services:
  api:
    build: .
    image: bsc/translations-api:latest
    container_name: translations_api
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - APP_NAME=BSC Translation Platform
      - APP_VERSION=1.0.0
      - WORKERS=4
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/translations
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
      - CORS_ORIGINS=https://app.example.com
      - LOG_LEVEL=INFO
      - LOG_JSON=true
    depends_on:
      - db
    networks:
      - translations_network
    volumes:
      - ./logs:/app/logs

  db:
    image: postgres:15-alpine
    container_name: translations_db
    restart: unless-stopped
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=translations
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - translations_network

  nginx:
    image: nginx:alpine
    container_name: translations_nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - api
    networks:
      - translations_network

volumes:
  postgres_data:

networks:
  translations_network:
    driver: bridge
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: translations-api
  namespace: production
spec:
  replicas: 4
  selector:
    matchLabels:
      app: translations-api
  template:
    metadata:
      labels:
        app: translations-api
    spec:
      containers:
      - name: api
        image: bsc/translations-api:1.0.0
        ports:
        - containerPort: 8000
        env:
        - name: APP_NAME
          value: "BSC Translation Platform"
        - name: WORKERS
          value: "4"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: database-url
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: jwt-secrets
              key: secret-key
        - name: ENCRYPTION_KEY
          valueFrom:
            secretKeyRef:
              name: encryption-secrets
              key: encryption-key
        - name: LOG_LEVEL
          value: "INFO"
        - name: LOG_JSON
          value: "true"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: translations-api-service
  namespace: production
spec:
  selector:
    app: translations-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

### Health Checks

```python
# app/router/health.py
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_session)):
    """Health check endpoint for load balancers."""
    try:
        # Verificar conexión a DB
        await db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "version": settings.app_version
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }
```

---

## Monitoreo y Observabilidad

### Logging Estructurado

```python
# app/core/logger.py
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# Ejemplo de uso en endpoints
@router.post("/languages")
async def create_language(language: LanguageCreate, ...):
    logger.info(
        f"Creating language: {language.code}",
        extra={
            "action": "language_create",
            "language_code": language.code,
            "user_id": current_user.id,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    # ...
```

### Métricas con Prometheus

```python
from prometheus_client import Counter, Histogram

language_operations = Counter(
    'language_operations_total',
    'Total language operations',
    ['operation', 'status']
)

language_response_time = Histogram(
    'language_response_time_seconds',
    'Language endpoint response time'
)

@router.post("/languages")
@language_response_time.time()
async def create_language(...):
    try:
        # Logic
        language_operations.labels(operation='create', status='success').inc()
    except Exception as e:
        language_operations.labels(operation='create', status='error').inc()
        raise
```

### Queries de Auditoría

```sql
-- Idiomas creados por usuario
SELECT
    l.code,
    l.name,
    l.created_at,
    u.username AS created_by
FROM languages l
JOIN audit_log al ON al.table_name = 'languages' AND al.record_id = l.id
JOIN users u ON al.user_id = u.id
WHERE al.action = 'INSERT'
ORDER BY l.created_at DESC;

-- Cambios de estado (activación/desactivación)
SELECT
    l.code,
    al.old_values->>'is_active' AS was_active,
    al.new_values->>'is_active' AS now_active,
    u.username AS changed_by,
    al.created_at AS changed_at
FROM audit_log al
JOIN languages l ON al.record_id = l.id
JOIN users u ON al.user_id = u.id
WHERE al.table_name = 'languages' AND al.action = 'UPDATE'
  AND al.old_values->>'is_active' != al.new_values->>'is_active'
ORDER BY al.created_at DESC;
```

---

## Escalabilidad y Rendimiento

### Caching de Idiomas

```python
from functools import lru_cache
from datetime import datetime, timedelta

# Cache en memoria (simple)
_language_cache = None
_cache_timestamp = None
CACHE_TTL = timedelta(minutes=5)

async def get_active_languages_cached(db: AsyncSession):
    """Get active languages with simple in-memory cache."""
    global _language_cache, _cache_timestamp

    now = datetime.utcnow()
    if _language_cache and _cache_timestamp and (now - _cache_timestamp) < CACHE_TTL:
        return _language_cache

    # Cache miss o expirado
    languages = await crud_translation.get_languages(db, only_active=True)
    _language_cache = languages
    _cache_timestamp = now
    return languages
```

### Redis Cache (Producción)

```python
import json
import redis.asyncio as redis
from app.core.config import settings

redis_client = redis.from_url(settings.redis_url)

async def get_active_languages_redis(db: AsyncSession):
    """Get active languages with Redis cache."""
    cache_key = "languages:active"

    # Try cache
    cached = await redis_client.get(cache_key)
    if cached:
        return [LanguageResponse(**lang) for lang in json.loads(cached)]

    # Cache miss
    languages = await crud_translation.get_languages(db, only_active=True)
    languages_json = json.dumps([lang.model_dump() for lang in languages])

    # Store in cache (5 minutes TTL)
    await redis_client.setex(cache_key, 300, languages_json)

    return languages
```

### Invalidación de Cache

```python
@router.post("/languages")
async def create_language(...):
    # Create language
    language = await crud_translation.create_language(db, language_data)

    # Invalidar cache
    await redis_client.delete("languages:active")

    return language
```

### Database Indexing

```sql
-- Índices para optimizar queries comunes
CREATE INDEX idx_languages_code ON languages(code);
CREATE INDEX idx_languages_active_sort ON languages(is_active, sort_order, name);

-- Estadísticas
ANALYZE languages;
```

---

## Casos de Uso Empresariales

### Caso 1: Lanzamiento de Nuevo Mercado (Italiano)

**Escenario**: La organización decide expandirse a Italia.

```bash
#!/bin/bash
# deploy_italian_support.sh

API_BASE="https://api.example.com/v1"
TOKEN="<admin_token>"

echo "🇮🇹 Iniciando despliegue de soporte para italiano..."

# 1. Crear idioma
echo "1️⃣ Creando idioma italiano..."
ITALIAN_RESPONSE=$(curl -s -X POST "$API_BASE/translations/languages" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "it",
    "name": "Italian",
    "native_name": "Italiano",
    "sort_order": 6
  }')

ITALIAN_ID=$(echo $ITALIAN_RESPONSE | jq -r '.id')
echo "   Idioma italiano creado: ID=$ITALIAN_ID"

# 2. Obtener todos los idiomas activos
echo "2️⃣ Obteniendo lista de idiomas activos..."
ALL_LANGS=$(curl -s "$API_BASE/translations/languages?only_active=true" | jq '[.[].id]')

# 3. Actualizar todos los providers para soportar italiano
echo "3️⃣ Actualizando providers..."
for PROVIDER_ID in 1 2 3; do
  curl -s -X PUT "$API_BASE/translations/providers/$PROVIDER_ID" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"input_language_ids\": $ALL_LANGS,
      \"output_language_ids\": $ALL_LANGS
    }"
  echo "   Provider $PROVIDER_ID actualizado ✓"
done

# 4. Verificar
echo "4️⃣ Verificación final..."
curl -s "$API_BASE/translations/languages/$ITALIAN_ID" | jq '.'

echo "✅ Despliegue completado. Italiano ahora disponible en producción."
```

### Caso 2: Mantenimiento Programado de Idioma

**Escenario**: El modelo de traducción para ruso necesita actualización, se desactiva temporalmente.

```bash
#!/bin/bash
# maintenance_russian.sh

API_BASE="https://api.example.com/v1"
TOKEN="<admin_token>"
RUSSIAN_ID=9

echo "🛠️ Iniciando mantenimiento para ruso..."

# 1. Desactivar idioma
echo "1️⃣ Desactivando ruso..."
curl -X PATCH "$API_BASE/translations/languages/$RUSSIAN_ID/toggle?is_active=false" \
  -H "Authorization: Bearer $TOKEN"

echo "   ⏸️ Ruso desactivado. Los usuarios no pueden traducir a/desde ruso."

# 2. Actualizar modelo de traducción (fuera de este script)
echo "2️⃣ Ejecutar actualización de modelo..."
# ./update_russian_model.sh

# 3. Esperar confirmación manual
read -p "Presiona ENTER cuando el modelo esté actualizado..."

# 4. Reactivar idioma
echo "3️⃣ Reactivando ruso..."
curl -X PATCH "$API_BASE/translations/languages/$RUSSIAN_ID/toggle?is_active=true" \
  -H "Authorization: Bearer $TOKEN"

echo "✅ Mantenimiento completado. Ruso nuevamente disponible."
```

### Caso 3: Auditoría de Cumplimiento

**Escenario**: Auditoría requiere reporte de todos los cambios en idiomas en los últimos 90 días.

```sql
-- audit_report.sql

-- 1. Todos los idiomas creados en los últimos 90 días
SELECT
    l.id,
    l.code,
    l.name,
    l.native_name,
    l.is_active,
    l.created_at,
    u.username AS created_by,
    u.email AS creator_email
FROM languages l
LEFT JOIN audit_log al ON al.table_name = 'languages'
    AND al.record_id = l.id
    AND al.action = 'INSERT'
LEFT JOIN users u ON al.user_id = u.id
WHERE l.created_at >= NOW() - INTERVAL '90 days'
ORDER BY l.created_at DESC;

-- 2. Cambios de estado en los últimos 90 días
SELECT
    l.code,
    l.name,
    al.action,
    al.old_values,
    al.new_values,
    u.username AS modified_by,
    al.created_at AS modified_at
FROM audit_log al
JOIN languages l ON al.record_id = l.id
JOIN users u ON al.user_id = u.id
WHERE al.table_name = 'languages'
  AND al.created_at >= NOW() - INTERVAL '90 days'
ORDER BY al.created_at DESC;

-- 3. Idiomas eliminados (si se implementa soft delete)
SELECT
    al.record_id,
    al.old_values->>'code' AS code,
    al.old_values->>'name' AS name,
    u.username AS deleted_by,
    al.created_at AS deleted_at
FROM audit_log al
JOIN users u ON al.user_id = u.id
WHERE al.table_name = 'languages'
  AND al.action = 'DELETE'
  AND al.created_at >= NOW() - INTERVAL '90 days';
```

---

## Mejores Prácticas

### 1. Gestión de Configuración

#### ✅ Recomendado

```bash
# Usar variables de entorno para secretos
export JWT_SECRET_KEY=$(generate_secure_key)
export ENCRYPTION_KEY=$(generate_fernet_key)

# Separar configuración por entorno
cp .env.example .env.production
# Editar .env.production con valores de producción

# Validar configuración antes de deployment
python -c "from app.core.config import settings; print(settings.app_name)"
```

#### ❌ Evitar

```bash
# ❌ Hardcodear secretos en código
JWT_SECRET_KEY = "my-secret-123"

# ❌ Commitear archivos .env
git add .env  # NUNCA

# ❌ Usar la misma configuración en todos los entornos
```

### 2. Seguridad de Endpoints

#### ✅ Recomendado

```python
# Endpoints administrativos SIEMPRE protegidos
@router.post("/languages")
async def create_language(
    ...,
    current_user: Annotated[User, Depends(PermissionChecker(["translations:manage"]))],
):
    # Validar entrada
    if not language.code.isalpha():
        raise HTTPException(400, "Invalid language code")

    # Log de auditoría
    logger.info(f"Admin {current_user.username} creating language {language.code}")

    # ...
```

#### ❌ Evitar

```python
# ❌ Endpoints admin sin protección
@router.post("/languages")
async def create_language(language: LanguageCreate, db: AsyncSession):
    # Cualquiera puede crear idiomas ❌
```

### 3. Manejo de Idiomas

#### ✅ Recomendado

```bash
# Desactivar en lugar de eliminar
PATCH /languages/15/toggle?is_active=false

# Validar antes de activar
# - Verificar que los providers soporten el idioma
# - Probar traducciones en staging
# - Documentar el cambio
```

#### ❌ Evitar

```bash
# ❌ Eliminar idiomas con historial
DELETE /languages/15  # Causará errores si hay traducciones
```

### 4. Monitoreo

#### ✅ Recomendado

```python
# Logging estructurado para todos los cambios críticos
logger.info(
    "Language state changed",
    extra={
        "language_id": language.id,
        "language_code": language.code,
        "old_state": old_active,
        "new_state": new_active,
        "changed_by": current_user.username,
        "timestamp": datetime.utcnow().isoformat()
    }
)

# Alertas para cambios inesperados
if not current_user.is_superuser and critical_operation:
    send_alert(f"Non-superuser {current_user.username} performed critical operation")
```

### 5. Testing

```python
# test_languages.py
import pytest

async def test_create_language_requires_permission(client):
    """Test que crear idioma requiere permiso."""
    # Usuario sin permiso
    response = await client.post(
        "/v1/translations/languages",
        json={"code": "test", "name": "Test", "native_name": "Test"},
        headers={"Authorization": f"Bearer {regular_user_token}"}
    )
    assert response.status_code == 403

async def test_list_languages_is_public(client):
    """Test que listar idiomas es público."""
    response = await client.get("/v1/translations/languages")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

async def test_cannot_delete_language_with_translations(client, db):
    """Test que no se puede eliminar idioma con historial."""
    # Crear idioma y traducción
    lang = await create_test_language(db)
    await create_test_translation(db, source_language_id=lang.id)

    # Intentar eliminar
    response = await client.delete(
        f"/v1/translations/languages/{lang.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 500  # Integrity error
```

---

**Documento generado**: 2025-12-21

**Autor**: Claude Sonnet 4.5 (Anthropic)

**Versión del sistema**: core_bsctranslation v1.0
