# Sistema para Añadir Nuevos Idiomas Dinámicamente (con Bandera)

## Índice

1. [Descripción General](#descripción-general)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Modelo de Datos](#modelo-de-datos)
4. [Gestión de Idiomas](#gestión-de-idiomas)
5. [API Endpoints](#api-endpoints)
6. [Códigos ISO 639-1](#códigos-iso-639-1)
7. [Banderas de Idiomas](#banderas-de-idiomas)
8. [Ejemplos de Uso](#ejemplos-de-uso)
9. [Integración con Providers](#integración-con-providers)
10. [Mejores Prácticas](#mejores-prácticas)
11. [Troubleshooting](#troubleshooting)

---

## Descripción General

El sistema de **gestión dinámica de idiomas** permite añadir, modificar y gestionar idiomas soportados por la plataforma de traducción sin necesidad de modificar código ni desplegar nuevas versiones.

### Características Principales

- **Gestión sin código**: Añadir/modificar idiomas vía API REST
- **Códigos ISO estándar**: Soporte para códigos ISO 639-1 (2 letras) y extensiones
- **Activación dinámica**: Habilitar/deshabilitar idiomas sin eliminarlos
- **Ordenamiento personalizado**: Control del orden de visualización
- **Nombres nativos**: Almacenamiento de nombres en inglés y nombre nativo
- **Relación con Providers**: Cada provider define qué idiomas soporta
- **Endpoint público**: Lista de idiomas disponible sin autenticación

### Casos de Uso

1. **Expansión multiidioma**: Añadir soporte para nuevos idiomas según demanda
2. **A/B Testing**: Probar idiomas en beta antes de hacerlos públicos
3. **Mantenimiento**: Desactivar temporalmente idiomas con problemas
4. **Regionalización**: Soportar variantes regionales (es-ES, es-MX, etc.)
5. **Priorización**: Ordenar idiomas por popularidad o importancia comercial

---

## Arquitectura del Sistema

### Diagrama de Componentes

```
┌──────────────────────────────────────────────────────────────────┐
│                         Cliente (UI/API)                          │
│  - Selector de idiomas en interfaz                               │
│  - Gestión administrativa de idiomas                             │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                   API Endpoints (FastAPI)                         │
│  GET  /languages          → Lista idiomas activos (público)      │
│  POST /languages          → Crear idioma (admin)                 │
│  PUT  /languages/{id}     → Actualizar idioma (admin)            │
│  PATCH /languages/{id}/toggle → Activar/desactivar (admin)       │
│  DELETE /languages/{id}   → Eliminar idioma (admin)              │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                  CRUD Operations Layer                            │
│  app/crud/translation.py:144-228                                 │
│  - create_language()     - update_language()                     │
│  - get_language()        - delete_language()                     │
│  - get_languages()       - activate_language()                   │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Database (PostgreSQL)                          │
│  Tabla: languages                                                │
│  - id, code, name, native_name                                   │
│  - is_active, sort_order                                         │
│  - created_at, updated_at                                        │
└──────────────────────────────────────────────────────────────────┘
```

### Flujo de Datos

#### Flujo: Usuario Lista Idiomas

```
1. Cliente → GET /api/v1/translations/languages?only_active=true
              ↓
2. Endpoint (público, sin auth)
              ↓
3. crud_translation.get_languages(db, only_active=True)
              ↓
4. Query SQL: SELECT * FROM languages
              WHERE is_active = true
              ORDER BY sort_order, name
              ↓
5. Response: [
     {"id": 1, "code": "en", "name": "English", "native_name": "English", ...},
     {"id": 2, "code": "es", "name": "Spanish", "native_name": "Español", ...},
     ...
   ]
```

#### Flujo: Administrador Crea Nuevo Idioma

```
1. Admin → POST /api/v1/translations/languages
           Body: {"code": "ca", "name": "Catalan", "native_name": "Català", "sort_order": 10}
           Header: Authorization: Bearer <token_con_translations:manage>
              ↓
2. Validación de permisos: PermissionChecker(["translations:manage"])
              ↓
3. Validación de código único: get_language_by_code(db, "ca")
              ↓
4. Si existe → Error 400: "Language with code 'ca' already exists"
   Si no existe → Continúa
              ↓
5. crud_translation.create_language(db, language_data)
              ↓
6. INSERT INTO languages (code, name, native_name, sort_order, is_active)
   VALUES ('ca', 'Catalan', 'Català', 10, true)
              ↓
7. Response: {"id": 15, "code": "ca", "name": "Catalan", "native_name": "Català", ...}
```

#### Flujo: Traducción Valida Idiomas

```
1. Cliente → POST /api/v1/translations/translate
             Body: {"text": "Hello", "source_language_code": "en", "target_language_code": "es"}
              ↓
2. Validar idioma origen:
   source_lang = await get_language_by_code(db, "en")
   if not source_lang or not source_lang.is_active:
       → Error 400: "Source language 'en' not available"
              ↓
3. Validar idioma destino:
   target_lang = await get_language_by_code(db, "es")
   if not target_lang or not target_lang.is_active:
       → Error 400: "Target language 'es' not available"
              ↓
4. Si ambos válidos → Continúa con traducción
```

---

## Modelo de Datos

### Tabla: `languages`

**Ubicación del modelo**: `app/models/translation.py:36-63`

**Esquema SQL**:

```sql
CREATE TABLE languages (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,        -- Código ISO 639-1 (ej: "en", "es", "ca")
    name VARCHAR(100) NOT NULL,              -- Nombre en inglés (ej: "Spanish")
    native_name VARCHAR(100) NOT NULL,       -- Nombre nativo (ej: "Español")
    is_active BOOLEAN DEFAULT TRUE NOT NULL, -- Si el idioma está habilitado
    sort_order INTEGER DEFAULT 0 NOT NULL,   -- Orden de visualización
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_languages_code ON languages(code);
```

### Modelo SQLAlchemy

**Archivo**: `app/models/translation.py`

```python
class Language(Base):
    """Language model for translation."""

    __tablename__ = "languages"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    native_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relaciones
    source_translations = relationship(
        "Translation",
        foreign_keys="Translation.source_language_id",
        back_populates="source_language"
    )
    target_translations = relationship(
        "Translation",
        foreign_keys="Translation.target_language_id",
        back_populates="target_language"
    )
```

### Campos del Modelo

| Campo | Tipo | Nullable | Descripción | Ejemplo |
|-------|------|----------|-------------|---------|
| `id` | BigInteger | No | Identificador único | `1` |
| `code` | String(10) | No | Código ISO 639-1 (único, indexado) | `"en"`, `"es"`, `"ca"` |
| `name` | String(100) | No | Nombre del idioma en inglés | `"Spanish"` |
| `native_name` | String(100) | No | Nombre del idioma en su forma nativa | `"Español"` |
| `is_active` | Boolean | No | Si el idioma está activo (default: true) | `true`, `false` |
| `sort_order` | Integer | No | Orden de visualización (default: 0) | `0`, `10`, `20` |
| `created_at` | DateTime | No | Timestamp de creación | `2025-12-21 10:00:00` |
| `updated_at` | DateTime | No | Timestamp de última actualización | `2025-12-21 15:30:00` |

### Schemas Pydantic

**Archivo**: `app/schemas/translation.py:89-124`

#### LanguageBase

```python
class LanguageBase(BaseModel):
    """Base schema for language."""

    code: str = Field(..., min_length=2, max_length=10, description="ISO 639-1 language code")
    name: str = Field(..., min_length=1, max_length=100, description="Language name in English")
    native_name: str = Field(..., min_length=1, max_length=100, description="Language name in native script")
```

#### LanguageCreate

```python
class LanguageCreate(LanguageBase):
    """Schema for creating a language."""

    sort_order: int = Field(default=0, ge=0, description="Display sort order")
```

#### LanguageUpdate

```python
class LanguageUpdate(BaseModel):
    """Schema for updating a language."""

    name: str | None = Field(None, min_length=1, max_length=100)
    native_name: str | None = Field(None, min_length=1, max_length=100)
    is_active: bool | None = None
    sort_order: int | None = Field(None, ge=0)
```

#### LanguageResponse

```python
class LanguageResponse(LanguageBase):
    """Schema for language response."""

    id: int
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

---

## Gestión de Idiomas

### Operaciones CRUD

**Archivo**: `app/crud/translation.py:142-228`

#### Crear Idioma

```python
async def create_language(db: AsyncSession, language: LanguageCreate) -> Language:
    """Create a new language."""
    db_language = Language(**language.model_dump())
    db.add(db_language)
    await db.commit()
    await db.refresh(db_language)
    return db_language
```

#### Obtener Idioma por ID

```python
async def get_language(db: AsyncSession, language_id: int) -> Language | None:
    """Get language by ID."""
    result = await db.execute(
        select(Language).where(Language.id == language_id)
    )
    return result.scalar_one_or_none()
```

#### Obtener Idioma por Código

```python
async def get_language_by_code(db: AsyncSession, code: str) -> Language | None:
    """Get language by code."""
    result = await db.execute(
        select(Language).where(Language.code == code)
    )
    return result.scalar_one_or_none()
```

#### Listar Idiomas

```python
async def get_languages(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    only_active: bool = False
) -> list[Language]:
    """Get languages with optional active filter."""
    query = select(Language).order_by(Language.sort_order, Language.name)
    if only_active:
        query = query.where(Language.is_active == True)
    result = await db.execute(query.offset(skip).limit(limit))
    return list(result.scalars().all())
```

**Nota**: El ordenamiento es por `sort_order` primero, luego por `name` alfabéticamente.

#### Actualizar Idioma

```python
async def update_language(
    db: AsyncSession,
    language_id: int,
    language_update: LanguageUpdate
) -> Language | None:
    """Update a language."""
    language = await get_language(db, language_id)
    if not language:
        return None

    update_data = language_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(language, field, value)

    await db.commit()
    await db.refresh(language)
    return language
```

#### Activar/Desactivar Idioma

```python
async def activate_language(db: AsyncSession, language_id: int, is_active: bool) -> Language | None:
    """Activate or deactivate a language."""
    language = await get_language(db, language_id)
    if not language:
        return None

    language.is_active = is_active
    await db.commit()
    await db.refresh(language)
    return language
```

#### Eliminar Idioma

```python
async def delete_language(db: AsyncSession, language_id: int) -> bool:
    """Delete a language."""
    language = await get_language(db, language_id)
    if not language:
        return False

    await db.delete(language)
    await db.commit()
    return True
```

**Advertencia**: Eliminar un idioma con traducciones asociadas causará un error de restricción de clave foránea (CASCADE).

---

## API Endpoints

### Endpoints de Idiomas

**Ubicación**: `app/api/translations.py:191-272`

#### 1. Listar Idiomas (Público)

**GET** `/api/v1/translations/languages`

**Permisos**: Ninguno (endpoint público)

**Query Parameters**:

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `skip` | int | 0 | Número de registros a saltar |
| `limit` | int | 100 | Máximo de registros (max: 100) |
| `only_active` | bool | true | Mostrar solo idiomas activos |

**Ejemplo Request**:

```bash
curl "http://localhost:8000/api/v1/translations/languages?only_active=true&limit=50"
```

**Response** (200 OK):

```json
[
  {
    "id": 1,
    "code": "en",
    "name": "English",
    "native_name": "English",
    "is_active": true,
    "sort_order": 0,
    "created_at": "2025-12-20T00:00:00Z",
    "updated_at": "2025-12-20T00:00:00Z"
  },
  {
    "id": 2,
    "code": "es",
    "name": "Spanish",
    "native_name": "Español",
    "is_active": true,
    "sort_order": 1,
    "created_at": "2025-12-20T00:00:00Z",
    "updated_at": "2025-12-20T00:00:00Z"
  },
  {
    "id": 3,
    "code": "ca",
    "name": "Catalan",
    "native_name": "Català",
    "is_active": true,
    "sort_order": 2,
    "created_at": "2025-12-20T00:00:00Z",
    "updated_at": "2025-12-20T00:00:00Z"
  }
]
```

#### 2. Crear Idioma

**POST** `/api/v1/translations/languages`

**Permisos**: `translations:manage`

**Request Body**:

```json
{
  "code": "ca",
  "name": "Catalan",
  "native_name": "Català",
  "sort_order": 10
}
```

**Validaciones**:
- `code`: 2-10 caracteres, debe ser único
- `name`: 1-100 caracteres
- `native_name`: 1-100 caracteres
- `sort_order`: ≥ 0

**Ejemplo Request**:

```bash
curl -X POST "http://localhost:8000/api/v1/translations/languages" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "ca",
    "name": "Catalan",
    "native_name": "Català",
    "sort_order": 10
  }'
```

**Response** (201 Created):

```json
{
  "id": 15,
  "code": "ca",
  "name": "Catalan",
  "native_name": "Català",
  "is_active": true,
  "sort_order": 10,
  "created_at": "2025-12-21T12:30:00Z",
  "updated_at": "2025-12-21T12:30:00Z"
}
```

**Errores**:

- **400 Bad Request**: Código ya existe
  ```json
  {
    "detail": "Language with code 'ca' already exists"
  }
  ```

- **422 Unprocessable Entity**: Validación fallida
  ```json
  {
    "detail": [
      {
        "loc": ["body", "code"],
        "msg": "ensure this value has at least 2 characters",
        "type": "value_error.any_str.min_length"
      }
    ]
  }
  ```

#### 3. Obtener Idioma por ID

**GET** `/api/v1/translations/languages/{language_id}`

**Permisos**: Ninguno (público)

**Ejemplo Request**:

```bash
curl "http://localhost:8000/api/v1/translations/languages/2"
```

**Response** (200 OK):

```json
{
  "id": 2,
  "code": "es",
  "name": "Spanish",
  "native_name": "Español",
  "is_active": true,
  "sort_order": 1,
  "created_at": "2025-12-20T00:00:00Z",
  "updated_at": "2025-12-20T00:00:00Z"
}
```

**Errores**:

- **404 Not Found**: Idioma no existe
  ```json
  {
    "detail": "Language not found"
  }
  ```

#### 4. Actualizar Idioma

**PUT** `/api/v1/translations/languages/{language_id}`

**Permisos**: `translations:manage`

**Request Body** (todos los campos son opcionales):

```json
{
  "name": "Spanish (Spain)",
  "native_name": "Español (España)",
  "is_active": true,
  "sort_order": 5
}
```

**Ejemplo Request**:

```bash
curl -X PUT "http://localhost:8000/api/v1/translations/languages/2" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Spanish (Spain)",
    "sort_order": 5
  }'
```

**Response** (200 OK):

```json
{
  "id": 2,
  "code": "es",
  "name": "Spanish (Spain)",
  "native_name": "Español",
  "is_active": true,
  "sort_order": 5,
  "created_at": "2025-12-20T00:00:00Z",
  "updated_at": "2025-12-21T14:00:00Z"
}
```

**Nota**: El campo `code` NO se puede modificar después de creado.

#### 5. Activar/Desactivar Idioma

**PATCH** `/api/v1/translations/languages/{language_id}/toggle`

**Permisos**: `translations:manage`

**Query Parameters**:

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `is_active` | bool | Sí | Estado activo del idioma |

**Ejemplo Request** (Desactivar):

```bash
curl -X PATCH "http://localhost:8000/api/v1/translations/languages/15/toggle?is_active=false" \
  -H "Authorization: Bearer $TOKEN"
```

**Ejemplo Request** (Activar):

```bash
curl -X PATCH "http://localhost:8000/api/v1/translations/languages/15/toggle?is_active=true" \
  -H "Authorization: Bearer $TOKEN"
```

**Response** (200 OK):

```json
{
  "id": 15,
  "code": "ca",
  "name": "Catalan",
  "native_name": "Català",
  "is_active": false,
  "sort_order": 10,
  "created_at": "2025-12-21T12:30:00Z",
  "updated_at": "2025-12-21T14:30:00Z"
}
```

#### 6. Eliminar Idioma

**DELETE** `/api/v1/translations/languages/{language_id}`

**Permisos**: `translations:manage`

**Ejemplo Request**:

```bash
curl -X DELETE "http://localhost:8000/api/v1/translations/languages/15" \
  -H "Authorization: Bearer $TOKEN"
```

**Response** (204 No Content):

Sin cuerpo de respuesta.

**Errores**:

- **404 Not Found**: Idioma no existe
  ```json
  {
    "detail": "Language not found"
  }
  ```

- **500 Internal Server Error**: Idioma tiene traducciones asociadas (restricción de integridad)

---

## Códigos ISO 639-1

### Estándar Internacional

Los códigos de idioma siguen el estándar **ISO 639-1** (2 letras) y pueden extenderse con variantes regionales usando **ISO 3166-1** (ej: `es-ES`, `es-MX`).

### Idiomas Soportados por Salamandra

Lista de códigos ISO para los 35+ idiomas soportados por los modelos Salamandra:

| Código | Idioma (Inglés) | Idioma (Nativo) | Familia |
|--------|-----------------|-----------------|---------|
| `en` | English | English | Germánica |
| `es` | Spanish | Español | Románica |
| `ca` | Catalan | Català | Románica |
| `fr` | French | Français | Románica |
| `de` | German | Deutsch | Germánica |
| `it` | Italian | Italiano | Románica |
| `pt` | Portuguese | Português | Románica |
| `nl` | Dutch | Nederlands | Germánica |
| `pl` | Polish | Polski | Eslava |
| `ru` | Russian | Русский | Eslava |
| `uk` | Ukrainian | Українська | Eslava |
| `cs` | Czech | Čeština | Eslava |
| `ro` | Romanian | Română | Románica |
| `bg` | Bulgarian | Български | Eslava |
| `hu` | Hungarian | Magyar | Urálica |
| `el` | Greek | Ελληνικά | Griega |
| `fi` | Finnish | Suomi | Urálica |
| `sv` | Swedish | Svenska | Germánica |
| `da` | Danish | Dansk | Germánica |
| `no` | Norwegian | Norsk | Germánica |
| `gl` | Galician | Galego | Románica |
| `eu` | Basque | Euskara | Aislada |
| `hr` | Croatian | Hrvatski | Eslava |
| `sr` | Serbian | Српски | Eslava |
| `sk` | Slovak | Slovenčina | Eslava |
| `sl` | Slovenian | Slovenščina | Eslava |
| `et` | Estonian | Eesti | Urálica |
| `lv` | Latvian | Latviešu | Báltica |
| `lt` | Lithuanian | Lietuvių | Báltica |
| `ga` | Irish | Gaeilge | Celta |
| `cy` | Welsh | Cymraeg | Celta |
| `mt` | Maltese | Malti | Semítica |
| `an` | Aragonese | Aragonés | Románica |
| `ast` | Asturian | Asturianu | Románica |
| `oc` | Occitan | Occitan | Románica |

### Variantes Regionales

```
Español:
├─ es-ES: Español (España)
├─ es-MX: Español (México)
├─ es-AR: Español (Argentina)
└─ es-CO: Español (Colombia)

Inglés:
├─ en-US: English (United States)
├─ en-GB: English (United Kingdom)
├─ en-CA: English (Canada)
└─ en-AU: English (Australia)

Portugués:
├─ pt-BR: Português (Brasil)
└─ pt-PT: Português (Portugal)

Francés:
├─ fr-FR: Français (France)
├─ fr-CA: Français (Canada)
└─ fr-CH: Français (Suisse)

Noruego:
├─ nb: Norwegian Bokmål
└─ nn: Norwegian Nynorsk

Catalán:
├─ ca: Català
└─ ca-valencia: Valencià
```

---

## Banderas de Idiomas

### Implementación con Emojis Unicode

Aunque el modelo actual no incluye un campo para banderas, se pueden representar usando **emojis de banderas Unicode** basados en códigos de país (ISO 3166-1 alpha-2).

#### Mapeo Idioma → Bandera

```python
# Mapeo código de idioma ISO 639-1 → emoji de bandera
LANGUAGE_FLAGS = {
    "en": "🇬🇧",  # o 🇺🇸 para inglés americano
    "es": "🇪🇸",
    "ca": "🏴",    # Sin bandera oficial, usar genérica o catalana
    "fr": "🇫🇷",
    "de": "🇩🇪",
    "it": "🇮🇹",
    "pt": "🇵🇹",  # o 🇧🇷 para portugués brasileño
    "nl": "🇳🇱",
    "pl": "🇵🇱",
    "ru": "🇷🇺",
    "uk": "🇺🇦",
    "cs": "🇨🇿",
    "ro": "🇷🇴",
    "bg": "🇧🇬",
    "hu": "🇭🇺",
    "el": "🇬🇷",
    "fi": "🇫🇮",
    "sv": "🇸🇪",
    "da": "🇩🇰",
    "no": "🇳🇴",
    "gl": "🏴",    # Galicia
    "eu": "🏴",    # País Vasco
    "hr": "🇭🇷",
    "sr": "🇷🇸",
    "sk": "🇸🇰",
    "sl": "🇸🇮",
    "et": "🇪🇪",
    "lv": "🇱🇻",
    "lt": "🇱🇹",
    "ga": "🇮🇪",
    "cy": "🏴󠁧󠁢󠁷󠁬󠁳󠁿",  # Gales
    "mt": "🇲🇹",
}
```

#### Generación de Emoji de Bandera

Los emojis de banderas se forman con dos caracteres especiales Unicode (Regional Indicator Symbols) correspondientes a las letras del código de país ISO 3166-1:

```python
def country_code_to_flag_emoji(country_code: str) -> str:
    """
    Convierte un código de país ISO 3166-1 alpha-2 a emoji de bandera.

    Ejemplo:
        country_code_to_flag_emoji("ES") → "🇪🇸"
        country_code_to_flag_emoji("US") → "🇺🇸"
    """
    # Código base para Regional Indicator Symbol Letter A
    OFFSET = 127397

    country_code = country_code.upper()
    return chr(ord(country_code[0]) + OFFSET) + chr(ord(country_code[1]) + OFFSET)


# Ejemplos de uso
print(country_code_to_flag_emoji("ES"))  # 🇪🇸
print(country_code_to_flag_emoji("FR"))  # 🇫🇷
print(country_code_to_flag_emoji("DE"))  # 🇩🇪
```

### Extensión del Modelo (Propuesta)

Para añadir soporte nativo de banderas en el modelo, se podría agregar un campo `flag_emoji`:

#### Migración SQL Propuesta

```sql
-- Añadir columna para emoji de bandera
ALTER TABLE languages ADD COLUMN flag_emoji VARCHAR(10) DEFAULT NULL;

-- Poblar banderas para idiomas existentes
UPDATE languages SET flag_emoji = '🇬🇧' WHERE code = 'en';
UPDATE languages SET flag_emoji = '🇪🇸' WHERE code = 'es';
UPDATE languages SET flag_emoji = '🇫🇷' WHERE code = 'fr';
UPDATE languages SET flag_emoji = '🇩🇪' WHERE code = 'de';
UPDATE languages SET flag_emoji = '🇮🇹' WHERE code = 'it';
UPDATE languages SET flag_emoji = '🇵🇹' WHERE code = 'pt';
-- ... resto de idiomas
```

#### Modelo Actualizado (Propuesta)

```python
class Language(Base):
    """Language model for translation."""

    __tablename__ = "languages"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    native_name = Column(String(100), nullable=False)
    flag_emoji = Column(String(10), nullable=True)  # NUEVO CAMPO
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
```

#### Schema Pydantic Actualizado (Propuesta)

```python
class LanguageBase(BaseModel):
    """Base schema for language."""

    code: str = Field(..., min_length=2, max_length=10)
    name: str = Field(..., min_length=1, max_length=100)
    native_name: str = Field(..., min_length=1, max_length=100)
    flag_emoji: str | None = Field(None, max_length=10, description="Unicode flag emoji")


class LanguageCreate(LanguageBase):
    """Schema for creating a language."""

    sort_order: int = Field(default=0, ge=0)


class LanguageResponse(LanguageBase):
    """Schema for language response."""

    id: int
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

#### Ejemplo de Uso con Banderas

```bash
# Crear idioma con bandera
curl -X POST "$API_BASE/translations/languages" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "eu",
    "name": "Basque",
    "native_name": "Euskara",
    "flag_emoji": "🏴",
    "sort_order": 15
  }'
```

**Response**:

```json
{
  "id": 20,
  "code": "eu",
  "name": "Basque",
  "native_name": "Euskara",
  "flag_emoji": "🏴",
  "is_active": true,
  "sort_order": 15,
  "created_at": "2025-12-21T16:00:00Z",
  "updated_at": "2025-12-21T16:00:00Z"
}
```

### Implementación sin Modificar Modelo (Solución Actual)

**Opción 1**: Generación dinámica en el frontend

```javascript
// Frontend JavaScript
const LANGUAGE_FLAGS = {
  'en': '🇬🇧',
  'es': '🇪🇸',
  'ca': '🏴',
  'fr': '🇫🇷',
  'de': '🇩🇪',
  // ...
};

function getLanguageFlag(languageCode) {
  return LANGUAGE_FLAGS[languageCode] || '🌐';  // 🌐 como fallback
}

// Uso en selector de idiomas
languages.forEach(lang => {
  const flag = getLanguageFlag(lang.code);
  console.log(`${flag} ${lang.native_name}`);  // 🇪🇸 Español
});
```

**Opción 2**: Middleware de respuesta en backend

```python
# app/api/translations.py

def add_flag_emoji(language: LanguageResponse) -> dict:
    """Añade emoji de bandera a la respuesta del idioma."""
    LANGUAGE_FLAGS = {
        "en": "🇬🇧",
        "es": "🇪🇸",
        "ca": "🏴",
        "fr": "🇫🇷",
        # ...
    }

    response = language.model_dump()
    response["flag_emoji"] = LANGUAGE_FLAGS.get(language.code, "🌐")
    return response


@router.get("/languages", response_model=list[dict])
async def list_languages_with_flags(
    db: Annotated[AsyncSession, Depends(get_session)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    only_active: bool = Query(True),
):
    """List all languages with flag emojis added."""
    languages = await crud_translation.get_languages(db, skip=skip, limit=limit, only_active=only_active)
    return [add_flag_emoji(LanguageResponse.model_validate(lang)) for lang in languages]
```

---

## Ejemplos de Uso

### Caso 1: Poblar Idiomas Iniciales

**Script bash para crear múltiples idiomas**:

```bash
#!/bin/bash

API_BASE="http://localhost:8000/api/v1"
TOKEN="<token_con_permisos_translations:manage>"

# Array de idiomas: código|nombre_en_inglés|nombre_nativo|orden
LANGUAGES=(
  "en|English|English|0"
  "es|Spanish|Español|1"
  "ca|Catalan|Català|2"
  "fr|French|Français|3"
  "de|German|Deutsch|4"
  "it|Italian|Italiano|5"
  "pt|Portuguese|Português|6"
  "eu|Basque|Euskara|7"
  "gl|Galician|Galego|8"
  "ru|Russian|Русский|9"
  "uk|Ukrainian|Українська|10"
)

for lang_data in "${LANGUAGES[@]}"; do
  IFS='|' read -r code name native_name sort_order <<< "$lang_data"

  echo "📝 Creando idioma: $name ($native_name)..."

  curl -X POST "$API_BASE/translations/languages" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"code\": \"$code\",
      \"name\": \"$name\",
      \"native_name\": \"$native_name\",
      \"sort_order\": $sort_order
    }" \
    --silent --show-error | jq -r '.id // "ERROR"'

  if [ $? -eq 0 ]; then
    echo "✅ Idioma $code creado exitosamente"
  else
    echo "❌ Error al crear idioma $code"
  fi
  echo ""
done

echo "🎉 Proceso completado!"
```

### Caso 2: Selector de Idiomas en Frontend (React)

```jsx
import React, { useEffect, useState } from 'react';

const LANGUAGE_FLAGS = {
  'en': '🇬🇧',
  'es': '🇪🇸',
  'ca': '🏴',
  'fr': '🇫🇷',
  'de': '🇩🇪',
  'it': '🇮🇹',
  'pt': '🇵🇹',
  'eu': '🏴',
  'gl': '🏴',
  'ru': '🇷🇺',
  'uk': '🇺🇦',
};

const LanguageSelector = ({ value, onChange, type = 'source' }) => {
  const [languages, setLanguages] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch languages from API
    fetch('http://localhost:8000/api/v1/translations/languages?only_active=true')
      .then(res => res.json())
      .then(data => {
        setLanguages(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error loading languages:', err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <div>Loading languages...</div>;
  }

  return (
    <div className="language-selector">
      <label htmlFor={`lang-${type}`}>
        {type === 'source' ? 'Source Language:' : 'Target Language:'}
      </label>
      <select
        id={`lang-${type}`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="form-select"
      >
        <option value="">-- Select Language --</option>
        {languages.map(lang => (
          <option key={lang.id} value={lang.code}>
            {LANGUAGE_FLAGS[lang.code] || '🌐'} {lang.native_name} ({lang.name})
          </option>
        ))}
      </select>
    </div>
  );
};

export default LanguageSelector;
```

### Caso 3: Añadir Idioma Regional (es-MX)

```bash
#!/bin/bash

API_BASE="http://localhost:8000/api/v1"
TOKEN="<token_con_permisos_translations:manage>"

# Crear variante regional de español para México
curl -X POST "$API_BASE/translations/languages" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "es-MX",
    "name": "Spanish (Mexico)",
    "native_name": "Español (México)",
    "sort_order": 11
  }'
```

**Response**:

```json
{
  "id": 25,
  "code": "es-MX",
  "name": "Spanish (Mexico)",
  "native_name": "Español (México)",
  "is_active": true,
  "sort_order": 11,
  "created_at": "2025-12-21T17:00:00Z",
  "updated_at": "2025-12-21T17:00:00Z"
}
```

### Caso 4: Desactivar Idioma Temporalmente (Mantenimiento)

```bash
#!/bin/bash

API_BASE="http://localhost:8000/api/v1"
TOKEN="<token_con_permisos_translations:manage>"

LANGUAGE_ID=15

echo "⏸️  Desactivando idioma $LANGUAGE_ID..."

# Desactivar idioma
curl -X PATCH "$API_BASE/translations/languages/$LANGUAGE_ID/toggle?is_active=false" \
  -H "Authorization: Bearer $TOKEN"

echo ""
echo "✅ Idioma desactivado. Los usuarios ya no podrán seleccionarlo."
echo ""

# Esperar mientras se realiza mantenimiento...
sleep 300  # 5 minutos

echo "▶️  Reactivando idioma $LANGUAGE_ID..."

# Reactivar idioma
curl -X PATCH "$API_BASE/translations/languages/$LANGUAGE_ID/toggle?is_active=true" \
  -H "Authorization: Bearer $TOKEN"

echo ""
echo "✅ Idioma reactivado."
```

### Caso 5: Reordenar Idiomas por Popularidad

```python
import httpx
import asyncio

API_BASE = "http://localhost:8000/api/v1"
TOKEN = "your_token"

# Nuevo orden basado en volumen de uso
LANGUAGE_PRIORITY = {
    "en": 0,   # Más popular
    "es": 1,
    "fr": 2,
    "de": 3,
    "it": 4,
    "pt": 5,
    "ru": 6,
    "ca": 7,
    "eu": 8,
    "gl": 9,
}

async def reorder_languages():
    """Actualiza el orden de los idiomas según prioridad."""
    async with httpx.AsyncClient() as client:
        # 1. Obtener todos los idiomas
        response = await client.get(
            f"{API_BASE}/translations/languages?only_active=false&limit=100"
        )
        languages = response.json()

        # 2. Actualizar sort_order según prioridad
        for lang in languages:
            new_order = LANGUAGE_PRIORITY.get(lang["code"], 999)  # 999 para no priorizados

            if new_order != lang["sort_order"]:
                print(f"📝 Actualizando orden de {lang['code']}: {lang['sort_order']} → {new_order}")

                await client.put(
                    f"{API_BASE}/translations/languages/{lang['id']}",
                    headers={"Authorization": f"Bearer {TOKEN}"},
                    json={"sort_order": new_order}
                )

        print("✅ Reordenamiento completado!")

# Ejecutar
asyncio.run(reorder_languages())
```

### Caso 6: Migrar Idiomas desde CSV

```python
import csv
import httpx
import asyncio

API_BASE = "http://localhost:8000/api/v1"
TOKEN = "your_token"

async def import_languages_from_csv(csv_path: str):
    """
    Importa idiomas desde archivo CSV.

    Formato CSV esperado:
    code,name,native_name,sort_order
    en,English,English,0
    es,Spanish,Español,1
    """
    async with httpx.AsyncClient() as client:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                print(f"📝 Creando idioma: {row['code']} ({row['native_name']})...")

                try:
                    response = await client.post(
                        f"{API_BASE}/translations/languages",
                        headers={"Authorization": f"Bearer {TOKEN}"},
                        json={
                            "code": row["code"],
                            "name": row["name"],
                            "native_name": row["native_name"],
                            "sort_order": int(row["sort_order"])
                        },
                        timeout=10.0
                    )

                    if response.status_code == 201:
                        print(f"✅ Idioma {row['code']} creado: ID {response.json()['id']}")
                    elif response.status_code == 400:
                        print(f"⚠️ Idioma {row['code']} ya existe, saltando...")
                    else:
                        print(f"❌ Error al crear {row['code']}: {response.text}")

                except Exception as e:
                    print(f"❌ Excepción al crear {row['code']}: {e}")

# Uso
asyncio.run(import_languages_from_csv("languages.csv"))
```

**Ejemplo de archivo `languages.csv`**:

```csv
code,name,native_name,sort_order
en,English,English,0
es,Spanish,Español,1
ca,Catalan,Català,2
fr,French,Français,3
de,German,Deutsch,4
it,Italian,Italiano,5
pt,Portuguese,Português,6
eu,Basque,Euskara,7
gl,Galician,Galego,8
```

---

## Integración con Providers

### Relación Provider-Idiomas

Cada provider de traducción especifica qué idiomas acepta como entrada (`input_language_ids`) y cuáles soporta como salida (`output_language_ids`).

**Ubicación**: `app/models/translation.py:24-25`

```python
class TranslationProvider(Base):
    # ...
    input_language_ids = Column(JSON, default=list, nullable=False)
    output_language_ids = Column(JSON, default=list, nullable=False)
```

### Configurar Provider con Idiomas

```bash
#!/bin/bash

API_BASE="http://localhost:8000/api/v1"
TOKEN="<token_con_permisos_translations:manage>"

# 1. Obtener IDs de idiomas activos
LANGUAGE_IDS=$(curl -s "$API_BASE/translations/languages?only_active=true" | jq '[.[].id]')

echo "Idiomas activos: $LANGUAGE_IDS"

# 2. Crear provider con todos los idiomas
curl -X POST "$API_BASE/translations/providers" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Salamandra 2B Multilingüe\",
    \"provider_type\": \"huggingface\",
    \"endpoint\": \"https://api-inference.huggingface.co/models/BSC-LT/salamandraTA-2b-instruct\",
    \"api_key\": \"$HF_API_KEY\",
    \"is_active\": true,
    \"is_default\": true,
    \"configuration\": {
      \"model\": \"BSC-LT/salamandra-2b\",
      \"parameters\": {
        \"max_new_tokens\": 512,
        \"do_sample\": false,
        \"chunk_chars\": 800
      }
    },
    \"input_language_ids\": $LANGUAGE_IDS,
    \"output_language_ids\": $LANGUAGE_IDS
  }"
```

### Actualizar Idiomas de Provider

Cuando se añade un nuevo idioma, los providers existentes deben actualizarse para soportarlo:

```bash
#!/bin/bash

API_BASE="http://localhost:8000/api/v1"
TOKEN="<token_con_permisos_translations:manage>"
PROVIDER_ID=1

# Obtener IDs de todos los idiomas activos (incluyendo los nuevos)
LANGUAGE_IDS=$(curl -s "$API_BASE/translations/languages?only_active=true" | jq '[.[].id]')

# Actualizar provider para soportar todos los idiomas
curl -X PUT "$API_BASE/translations/providers/$PROVIDER_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"input_language_ids\": $LANGUAGE_IDS,
    \"output_language_ids\": $LANGUAGE_IDS
  }"
```

### Validación de Idiomas en Traducción

**Ubicación**: `app/api/translations.py:284-298`

Cuando se solicita una traducción, el sistema valida:

1. **Idioma de origen existe y está activo**:
   ```python
   source_lang = await crud_translation.get_language_by_code(db, "en")
   if not source_lang or not source_lang.is_active:
       raise HTTPException(400, "Source language 'en' not available")
   ```

2. **Idioma de destino existe y está activo**:
   ```python
   target_lang = await crud_translation.get_language_by_code(db, "es")
   if not target_lang or not target_lang.is_active:
       raise HTTPException(400, "Target language 'es' not available")
   ```

**Nota**: Actualmente NO se valida que el provider seleccionado soporte el par de idiomas específico. Esta es una mejora recomendada.

### Mejora Propuesta: Validación Provider-Idioma

```python
# Propuesta de validación adicional en app/api/translations.py

async def validate_provider_supports_languages(
    provider: TranslationProvider,
    source_lang_id: int,
    target_lang_id: int
) -> None:
    """Valida que el provider soporte los idiomas solicitados."""

    # Validar idioma de origen
    if source_lang_id not in provider.input_language_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{provider.name}' does not support source language"
        )

    # Validar idioma de destino
    if target_lang_id not in provider.output_language_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{provider.name}' does not support target language"
        )

# Uso en endpoint de traducción
@router.post("/translate", response_model=TranslationResponse)
async def translate_text(request: TranslationRequest, ...):
    # ... validaciones existentes ...

    # Obtener provider
    service = await TranslationServiceFactory.get_service(db, request.provider_id)
    provider = await crud_translation.get_provider(db, provider_id)

    # NUEVA VALIDACIÓN
    await validate_provider_supports_languages(
        provider,
        source_lang.id,
        target_lang.id
    )

    # Continuar con traducción...
```

---

## Mejores Prácticas

### 1. Nomenclatura de Códigos

#### ✅ Recomendaciones

**Usar códigos ISO 639-1 estándar** (2 letras):
```
en, es, fr, de, it, pt, ca, eu, gl
```

**Para variantes regionales**, usar guión + código de país ISO 3166-1:
```
es-ES (España)
es-MX (México)
en-US (EE.UU.)
en-GB (Reino Unido)
pt-BR (Brasil)
pt-PT (Portugal)
```

**Evitar códigos no estándar**:
```
❌ spanish
❌ eng
❌ ESP
✅ es
✅ en
```

### 2. Ordenamiento de Idiomas

#### Estrategias de Orden

**Por popularidad** (recomendado para producción):
```
0: en (English)
1: es (Spanish)
2: fr (French)
3: de (German)
4: it (Italian)
...
```

**Por orden alfabético** (nombre nativo):
```
0: ca (Català)
1: de (Deutsch)
2: en (English)
3: es (Español)
4: eu (Euskara)
...
```

**Por familias lingüísticas**:
```
# Románicas
0-10: es, ca, gl, fr, it, pt, ro...

# Germánicas
11-20: en, de, nl, sv, da, no...

# Eslavas
21-30: ru, uk, pl, cs, sk, hr, sr...
```

### 3. Gestión de Estados

#### Usar `is_active` para Control

**Desactivar en lugar de eliminar**:

```bash
# ❌ Eliminar (pierde historial)
curl -X DELETE "$API_BASE/translations/languages/15"

# ✅ Desactivar (preserva datos)
curl -X PATCH "$API_BASE/translations/languages/15/toggle?is_active=false"
```

**Casos de uso para desactivar**:
- Idioma en mantenimiento
- Testing/beta antes de lanzamiento público
- Problemas de calidad temporal
- Bajo volumen de uso (ocultar sin eliminar)

### 4. Migración de Datos

#### Script de Respaldo antes de Cambios

```bash
#!/bin/bash

# Backup de idiomas antes de modificaciones
curl -s "http://localhost:8000/api/v1/translations/languages?only_active=false&limit=200" \
  | jq '.' > languages_backup_$(date +%Y%m%d_%H%M%S).json

echo "✅ Backup creado: languages_backup_$(date +%Y%m%d_%H%M%S).json"
```

#### Restauración desde Backup

```python
import json
import httpx
import asyncio

async def restore_languages_from_backup(backup_file: str, token: str):
    """Restaura idiomas desde archivo de backup."""

    with open(backup_file, 'r') as f:
        languages = json.load(f)

    async with httpx.AsyncClient() as client:
        for lang in languages:
            # Intentar crear idioma (ignorar si ya existe)
            try:
                response = await client.post(
                    "http://localhost:8000/api/v1/translations/languages",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "code": lang["code"],
                        "name": lang["name"],
                        "native_name": lang["native_name"],
                        "sort_order": lang["sort_order"]
                    }
                )
                print(f"✅ Restaurado: {lang['code']}")
            except Exception as e:
                print(f"⚠️ Error con {lang['code']}: {e}")

# Uso
asyncio.run(restore_languages_from_backup("languages_backup_20251221_120000.json", "your_token"))
```

### 5. Monitoreo y Auditoría

#### Queries de Análisis

```sql
-- 1. Idiomas más usados como origen
SELECT
    l.code,
    l.native_name,
    COUNT(*) AS times_used_as_source,
    SUM(t.character_count) AS total_chars_translated
FROM translations t
JOIN languages l ON t.source_language_id = l.id
WHERE t.created_at > NOW() - INTERVAL '30 days'
GROUP BY l.id, l.code, l.native_name
ORDER BY times_used_as_source DESC
LIMIT 10;

-- 2. Idiomas más usados como destino
SELECT
    l.code,
    l.native_name,
    COUNT(*) AS times_used_as_target
FROM translations t
JOIN languages l ON t.target_language_id = l.id
WHERE t.created_at > NOW() - INTERVAL '30 days'
GROUP BY l.id, l.code, l.native_name
ORDER BY times_used_as_target DESC
LIMIT 10;

-- 3. Pares de idiomas más frecuentes
SELECT
    sl.code AS source,
    tl.code AS target,
    COUNT(*) AS translation_count
FROM translations t
JOIN languages sl ON t.source_language_id = sl.id
JOIN languages tl ON t.target_language_id = tl.id
WHERE t.created_at > NOW() - INTERVAL '30 days'
GROUP BY sl.code, tl.code
ORDER BY translation_count DESC
LIMIT 20;

-- 4. Idiomas activos sin uso reciente
SELECT
    l.code,
    l.name,
    l.is_active,
    MAX(t.created_at) AS last_used
FROM languages l
LEFT JOIN translations t ON l.id IN (t.source_language_id, t.target_language_id)
WHERE l.is_active = true
GROUP BY l.id, l.code, l.name, l.is_active
HAVING MAX(t.created_at) < NOW() - INTERVAL '60 days' OR MAX(t.created_at) IS NULL
ORDER BY last_used DESC NULLS LAST;
```

---

## Troubleshooting

### Problema 1: "Language with code 'xx' already exists"

**Error**:
```json
{
  "detail": "Language with code 'ca' already exists"
}
```

**Causa**: Ya existe un idioma con ese código en la base de datos

**Solución**:

```bash
# Verificar si el idioma existe
curl "$API_BASE/translations/languages" | jq '.[] | select(.code == "ca")'

# Si existe pero está desactivado, activarlo
curl -X PATCH "$API_BASE/translations/languages/{id}/toggle?is_active=true" \
  -H "Authorization: Bearer $TOKEN"

# Si quieres actualizar sus datos
curl -X PUT "$API_BASE/translations/languages/{id}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Catalan (Updated)",
    "native_name": "Català",
    "sort_order": 5
  }'
```

### Problema 2: "Source language 'xx' not available"

**Error**:
```json
{
  "detail": "Source language 'en' not available"
}
```

**Causa**: El idioma no existe o está desactivado

**Solución**:

```bash
# 1. Verificar si existe
curl "$API_BASE/translations/languages?only_active=false" | jq '.[] | select(.code == "en")'

# 2a. Si existe pero está inactivo, activarlo
curl -X PATCH "$API_BASE/translations/languages/{id}/toggle?is_active=true" \
  -H "Authorization: Bearer $TOKEN"

# 2b. Si no existe, crearlo
curl -X POST "$API_BASE/translations/languages" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "en",
    "name": "English",
    "native_name": "English",
    "sort_order": 0
  }'
```

### Problema 3: No se puede eliminar idioma (Foreign Key Constraint)

**Error**:
```
500 Internal Server Error
sqlalchemy.exc.IntegrityError: ... violates foreign key constraint ...
```

**Causa**: El idioma tiene traducciones asociadas en la tabla `translations`

**Solución**:

**Opción 1**: Desactivar en lugar de eliminar (recomendado)

```bash
curl -X PATCH "$API_BASE/translations/languages/15/toggle?is_active=false" \
  -H "Authorization: Bearer $TOKEN"
```

**Opción 2**: Eliminar traducciones primero (¡PELIGROSO!)

```sql
-- ⚠️ ADVERTENCIA: Esto eliminará datos permanentemente
DELETE FROM translations WHERE source_language_id = 15 OR target_language_id = 15;
```

Luego eliminar el idioma:

```bash
curl -X DELETE "$API_BASE/translations/languages/15" \
  -H "Authorization: Bearer $TOKEN"
```

### Problema 4: Orden de idiomas no se aplica

**Síntoma**: Los idiomas no aparecen en el orden esperado según `sort_order`

**Causa**: El frontend está ordenando por otro campo o ignorando `sort_order`

**Solución**:

**Backend**: Verificar query en `crud_translation.get_languages()` (`app/crud/translation.py:186`):

```python
# DEBE ordenar por sort_order primero
query = select(Language).order_by(Language.sort_order, Language.name)
```

**Frontend**: Respetar el orden del API

```javascript
// ✅ Correcto: usar el orden que viene del API
fetch('/api/v1/translations/languages')
  .then(res => res.json())
  .then(languages => {
    // NO reordenar, usar tal como viene
    setLanguages(languages);
  });

// ❌ Incorrecto: reordenar en frontend
fetch('/api/v1/translations/languages')
  .then(res => res.json())
  .then(languages => {
    // Esto ignora el sort_order del backend
    const sorted = languages.sort((a, b) => a.name.localeCompare(b.name));
    setLanguages(sorted);
  });
```

### Problema 5: Validación de código ISO falla

**Error**:
```json
{
  "detail": [
    {
      "loc": ["body", "code"],
      "msg": "ensure this value has at least 2 characters",
      "type": "value_error.any_str.min_length"
    }
  ]
}
```

**Causa**: El código proporcionado tiene menos de 2 caracteres o más de 10

**Solución**:

Usar códigos válidos según ISO 639-1 (2 letras) o extensiones (ej: `es-MX`):

```bash
# ✅ Válido
curl -X POST "$API_BASE/translations/languages" \
  -d '{"code": "en", ...}'       # 2 letras

curl -X POST "$API_BASE/translations/languages" \
  -d '{"code": "es-MX", ...}'    # 2 letras + región

# ❌ Inválido
curl -X POST "$API_BASE/translations/languages" \
  -d '{"code": "e", ...}'        # 1 letra (muy corto)

curl -X POST "$API_BASE/translations/languages" \
  -d '{"code": "spanish", ...}'  # No es código ISO
```

### Problema 6: Emoji de bandera no se muestra correctamente

**Síntoma**: La bandera aparece como `[?]`, cuadrados o caracteres extraños

**Causa**: El sistema no soporta emojis Unicode complejos

**Soluciones**:

**Opción 1**: Usar imágenes SVG en lugar de emojis

```html
<!-- En lugar de emoji Unicode -->
<span class="flag">🇪🇸</span>

<!-- Usar imagen SVG -->
<img src="/flags/es.svg" alt="Spanish" class="flag-icon" />
```

**Opción 2**: Incluir fuente con soporte de emojis

```html
<!-- En el HTML -->
<link href="https://fonts.googleapis.com/css2?family=Noto+Color+Emoji&display=swap" rel="stylesheet">

<style>
.flag {
  font-family: 'Noto Color Emoji', sans-serif;
}
</style>
```

**Opción 3**: Usar librería de iconos de banderas

```bash
npm install flag-icons
```

```jsx
import 'flag-icons/css/flag-icons.min.css';

// Componente React
const Flag = ({ countryCode }) => (
  <span className={`fi fi-${countryCode.toLowerCase()}`}></span>
);

// Uso
<Flag countryCode="ES" />  // Bandera de España
```

---

## Referencias

### Archivos del Código Fuente

| Archivo | Descripción | Líneas Clave |
|---------|-------------|--------------|
| `app/models/translation.py` | Modelo de datos Language | 36-63 |
| `app/schemas/translation.py` | Schemas Pydantic para Language | 89-124 |
| `app/crud/translation.py` | Operaciones CRUD para languages | 142-228 |
| `app/api/translations.py` | Endpoints de gestión de idiomas | 191-272 |

### Estándares y Especificaciones

- **ISO 639-1**: Códigos de idioma de 2 letras - https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
- **ISO 3166-1**: Códigos de país para variantes regionales - https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2
- **Unicode Flag Emojis**: Regional Indicator Symbols - https://unicode.org/emoji/charts/emoji-list.html#flags

### Librerías Útiles

- **flag-icons**: CSS para banderas de países - https://github.com/lipis/flag-icons
- **country-flag-emoji**: Generador de emojis de banderas - https://www.npmjs.com/package/country-flag-emoji
- **i18n-iso-countries**: Mapeo de códigos ISO - https://github.com/michaelwittig/node-i18n-iso-countries

### Documentación Relacionada

- **Selección dinámica de modelos**: `docs/SELECCION_DINAMICA_MODELOS_SALAMANDRA.md`
- **Servicios de traducción**: `docs/SERVICIOS_TRADUCCION.md`
- **Gestión de usuarios**: `docs/LOGIN_Y_GESTION_USUARIOS.md`

---

**Documento generado**: 2025-12-21

**Autor**: Claude Sonnet 4.5 (Anthropic)

**Versión del sistema**: core_bsctranslation v1.0
