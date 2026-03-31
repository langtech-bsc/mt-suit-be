# Sistema de Pares de Traducción por Proveedor

## Índice

1. [Descripción General](#descripción-general)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Modelo de Datos](#modelo-de-datos)
4. [Flujo de Validación](#flujo-de-validación)
5. [Configuración de Proveedores](#configuración-de-proveedores)
6. [API Endpoints](#api-endpoints)
7. [Validación en Traducción](#validación-en-traducción)
8. [Casos de Uso Prácticos](#casos-de-uso-prácticos)
9. [Gestión Avanzada](#gestión-avanzada)
10. [Mejores Prácticas](#mejores-prácticas)
11. [Troubleshooting](#troubleshooting)

---

## Descripción General

El **sistema de pares de traducción** permite definir con granularidad qué combinaciones de idiomas (origen → destino) soporta cada proveedor de traducción. Esto permite:

- **Control específico por proveedor**: Cada modelo/servicio declara sus capacidades lingüísticas reales
- **Validación previa**: Evita llamadas fallidas a la API verificando soporte antes de traducir
- **Optimización de costos**: Enruta traducciones solo a proveedores capaces de procesarlas
- **Flexibilidad multi-modelo**: Permite tener modelos especializados por pares lingüísticos

### Características Principales

- ✅ Listas separadas para idiomas de **entrada** (source) y **salida** (target)
- ✅ Validación automática en endpoints de traducción
- ✅ Configuración dinámica sin modificar código
- ✅ Soporte para modelos especializados (ej: solo catalán → castellano)
- ✅ Gestión centralizada vía API REST
- ✅ Auditoría completa de cambios

---

## Arquitectura del Sistema

### Componentes Clave

```
┌─────────────────────────────────────────────────────────────────┐
│                      CAPA DE API (FastAPI)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  POST /translate                                                │
│    ↓                                                            │
│  1. Validar source_language_code existe y está activo          │
│  2. Validar target_language_code existe y está activo          │
│  3. Obtener proveedor (específico o default)                   │
│  4. ✓ Verificar proveedor soporta par (source → target)        │
│  5. Ejecutar traducción                                         │
│  6. Guardar en historial                                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
         ↓                                     ↓
┌──────────────────────┐          ┌──────────────────────────────┐
│  TranslationProvider │          │         Language             │
├──────────────────────┤          ├──────────────────────────────┤
│ • input_language_ids │◄─────────┤ • id (PK)                    │
│ • output_language_ids│          │ • code (ISO 639-1)           │
│ • name               │          │ • name                       │
│ • provider_type      │          │ • is_active                  │
│ • endpoint           │          │ • sort_order                 │
│ • encrypted_api_key  │          └──────────────────────────────┘
└──────────────────────┘
```

### Relación Proveedor-Idiomas

```
Provider:
  input_language_ids:  [1, 2, 3, 5]     → IDs de idiomas que acepta como ORIGEN
  output_language_ids: [1, 2, 4, 6]     → IDs de idiomas que produce como DESTINO

Languages:
  1 → "es" (Español)
  2 → "ca" (Catalán)
  3 → "en" (Inglés)
  4 → "fr" (Francés)
  5 → "de" (Alemán)
  6 → "it" (Italiano)

Traducciones VÁLIDAS con este proveedor:
  ✓ es → es, es → ca, es → fr, es → it
  ✓ ca → es, ca → ca, ca → fr, ca → it
  ✓ en → es, en → ca, en → fr, en → it
  ✓ de → es, de → ca, de → fr, de → it

Traducciones INVÁLIDAS:
  ✗ fr → cualquiera (francés no está en input_language_ids)
  ✗ es → en (inglés no está en output_language_ids)
  ✗ es → de (alemán no está en output_language_ids)
```

---

## Modelo de Datos

### Tabla `translation_providers`

| Campo                  | Tipo         | Descripción                                    | Ejemplo                        |
|------------------------|--------------|------------------------------------------------|--------------------------------|
| `id`                   | BigInteger   | Identificador único                            | `7`                            |
| `name`                 | String(100)  | Nombre descriptivo del proveedor               | `"Salamandra 2B Multilingüe"`  |
| `provider_type`        | String(50)   | Tipo de proveedor                              | `"huggingface"`                |
| `endpoint`             | String(500)  | URL del endpoint de API                        | `"https://api-inference.hf..."`|
| `encrypted_api_key`    | Text         | API key cifrada con Fernet                     | `"gAAAAA..."`                  |
| `region`               | String(50)   | Región del servicio (opcional)                 | `"us-east-1"`                  |
| `is_active`            | Boolean      | Si el proveedor está activo                    | `true`                         |
| `is_default`           | Boolean      | Si es el proveedor por defecto                 | `true`                         |
| `configuration`        | JSON         | Configuración adicional                        | `{"max_tokens": 512}`          |
| **`input_language_ids`**  | **JSON**     | **Array de IDs de idiomas de entrada**         | **`[1, 2, 3, 5]`**             |
| **`output_language_ids`** | **JSON**     | **Array de IDs de idiomas de salida**          | **`[1, 2, 4, 6]`**             |
| `created_at`           | DateTime     | Fecha de creación                              | `2025-01-15 10:30:00`          |
| `updated_at`           | DateTime     | Última actualización                           | `2025-01-20 14:22:00`          |

### Tabla `languages`

| Campo         | Tipo         | Descripción                  | Ejemplo                |
|---------------|--------------|------------------------------|------------------------|
| `id`          | BigInteger   | Identificador único          | `1`                    |
| `code`        | String(10)   | Código ISO 639-1 (único)     | `"es"`                 |
| `name`        | String(100)  | Nombre en inglés             | `"Spanish"`            |
| `native_name` | String(100)  | Nombre nativo                | `"Español"`            |
| `is_active`   | Boolean      | Si está disponible           | `true`                 |
| `sort_order`  | Integer      | Orden de visualización       | `10`                   |
| `created_at`  | DateTime     | Fecha de creación            | `2025-01-10 08:00:00`  |
| `updated_at`  | DateTime     | Última actualización         | `2025-01-10 08:00:00`  |

### Esquema Pydantic

**`TranslationProviderCreate`** (app/schemas/translation.py:31-46)

```python
class TranslationProviderCreate(TranslationProviderBase):
    """Schema for creating a translation provider."""

    api_key: SecretStr = Field(..., description="API key (will be encrypted)")
    configuration: dict | None = Field(None, description="Additional configuration")
    is_active: bool = Field(True, description="Whether the provider is active")
    is_default: bool = Field(False, description="Whether this is the default provider")

    @field_validator("input_language_ids", "output_language_ids")
    @classmethod
    def validate_languages(cls, v: list[int]) -> list[int]:
        """Ensure at least one language ID is provided."""
        if not v:
            raise ValueError("At least one language ID is required")
        return v
```

**Validación**: Ambas listas `input_language_ids` y `output_language_ids` deben contener **al menos un ID** de idioma.

---

## Flujo de Validación

### 1. Al Crear un Proveedor

```
Cliente → POST /providers
{
  "name": "Salamandra Catalán",
  "provider_type": "huggingface",
  "endpoint": "https://api-inference.huggingface.co/models/projecte-aina/salamandra-2b",
  "api_key": "hf_xxxxx",
  "input_language_ids": [1, 2],    // es, ca
  "output_language_ids": [1, 2, 3] // es, ca, en
}
         ↓
FastAPI valida el esquema Pydantic
         ↓
¿input_language_ids tiene al menos 1 elemento? ✓
¿output_language_ids tiene al menos 1 elemento? ✓
         ↓
Se cifra la API key
         ↓
Se guarda en base de datos
         ↓
Respuesta 201 Created con provider_id=15
```

### 2. Al Realizar una Traducción

**Endpoint**: `POST /v1/translations/translate`

```
Cliente envía:
{
  "source_language_code": "ca",
  "target_language_code": "es",
  "text": "Bon dia, com estàs?",
  "provider_id": 15  // opcional, usa default si no se especifica
}
         ↓
┌─────────────────────────────────────────────────────┐
│ FASE 1: Validación de idiomas activos              │
└─────────────────────────────────────────────────────┘
1. Buscar Language con code="ca" → Language(id=2)
2. ¿Existe y is_active=true? ✓
3. Buscar Language con code="es" → Language(id=1)
4. ¿Existe y is_active=true? ✓

         ↓
┌─────────────────────────────────────────────────────┐
│ FASE 2: Obtención del proveedor                    │
└─────────────────────────────────────────────────────┘
Si provider_id=15:
  → get_provider(15) → TranslationProvider
Si provider_id=None:
  → get_default_provider() → TranslationProvider con is_default=true

         ↓
┌─────────────────────────────────────────────────────┐
│ FASE 3: Verificación de soporte (IMPLÍCITA)        │
└─────────────────────────────────────────────────────┘
⚠️ NOTA: Actualmente NO hay validación explícita de si el proveedor
soporta el par source→target en el código.

El sistema confía en que:
- El administrador configuró correctamente los language_ids
- El proveedor/modelo realmente soporta esos idiomas

         ↓
┌─────────────────────────────────────────────────────┐
│ FASE 4: Ejecución de la traducción                 │
└─────────────────────────────────────────────────────┘
service = TranslationServiceFactory.get_service(db, provider_id)
translated_text = await service.translate(
    text="Bon dia, com estàs?",
    source_language="ca",
    target_language="es"
)
         ↓
┌─────────────────────────────────────────────────────┐
│ FASE 5: Guardar en historial                       │
└─────────────────────────────────────────────────────┘
TranslationCreate(
    provider_id=15,
    source_language_id=2,  // ca
    target_language_id=1,  // es
    source_text="Bon dia, com estàs?",
    translated_text="Buenos días, ¿cómo estás?",
    character_count=20,
    user_id=current_user.id
)
         ↓
Respuesta 200 OK con traducción
```

**Código real** (app/api/translations.py:284-298):

```python
# Validate source language exists and is active
source_lang = await crud_translation.get_language_by_code(db, request.source_language_code)
if not source_lang or not source_lang.is_active:
    raise HTTPException(
        status_code=400,
        detail=f"Source language '{request.source_language_code}' not available"
    )

# Validate target language exists and is active
target_lang = await crud_translation.get_language_by_code(db, request.target_language_code)
if not target_lang or not target_lang.is_active:
    raise HTTPException(
        status_code=400,
        detail=f"Target language '{request.target_language_code}' not available"
    )
```

---

## Configuración de Proveedores

### Escenario 1: Proveedor Multilingüe Universal

**Caso**: Salamandra 7B soporta todos los idiomas activos en la plataforma

```bash
# Paso 1: Obtener IDs de todos los idiomas activos
curl -X GET "https://api.bsc-translation.com/v1/translations/languages?only_active=true" \
  -H "Authorization: Bearer $TOKEN"

# Respuesta (ejemplo):
# [
#   {"id": 1, "code": "es", "name": "Spanish"},
#   {"id": 2, "code": "ca", "name": "Catalan"},
#   {"id": 3, "code": "en", "name": "English"},
#   {"id": 4, "code": "fr", "name": "French"},
#   {"id": 5, "code": "de", "name": "German"}
# ]

# Paso 2: Crear proveedor con todos los IDs en ambas listas
curl -X POST "https://api.bsc-translation.com/v1/translations/providers" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Salamandra 7B Universal",
    "provider_type": "huggingface",
    "endpoint": "https://api-inference.huggingface.co/models/BSC-LT/salamandra-7b",
    "api_key": "hf_xxxxxxxxxxxxxxxxx",
    "input_language_ids": [1, 2, 3, 4, 5],
    "output_language_ids": [1, 2, 3, 4, 5],
    "is_active": true,
    "is_default": true,
    "configuration": {
      "max_new_tokens": 512,
      "temperature": 0.7
    }
  }'
```

**Resultado**: Este proveedor puede traducir **cualquier combinación** de los 5 idiomas (25 pares posibles: es→ca, es→en, ca→es, etc.)

---

### Escenario 2: Proveedor Especializado Regional

**Caso**: Modelo optimizado solo para lenguas ibéricas (Español ↔ Catalán)

```bash
# IDs relevantes:
# 1 → es (Español)
# 2 → ca (Catalán)

curl -X POST "https://api.bsc-translation.com/v1/translations/providers" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Salamandra Regional Ibérico",
    "provider_type": "huggingface",
    "endpoint": "https://custom-endpoint.bsc.es/salamandra-iberic",
    "api_key": "hf_regional_key",
    "input_language_ids": [1, 2],    // Solo acepta español y catalán como entrada
    "output_language_ids": [1, 2],   // Solo produce español y catalán como salida
    "is_active": true,
    "is_default": false
  }'
```

**Resultado**: Traducciones válidas limitadas a:
- ✅ `es → ca` (Español → Catalán)
- ✅ `ca → es` (Catalán → Español)
- ✅ `es → es` (refinamiento/post-edición)
- ✅ `ca → ca` (refinamiento/post-edición)

---

### Escenario 3: Proveedor Asimétrico

**Caso**: Modelo que traduce DE múltiples idiomas HACIA inglés (summarizer multilingüe → EN)

```bash
# IDs:
# 1 → es, 2 → ca, 3 → en, 4 → fr, 5 → de

curl -X POST "https://api.bsc-translation.com/v1/translations/providers" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Multi-to-English Converter",
    "provider_type": "huggingface",
    "endpoint": "https://api.hf.co/models/multi-to-en",
    "api_key": "hf_converter_key",
    "input_language_ids": [1, 2, 3, 4, 5],  // Acepta cualquier idioma
    "output_language_ids": [3],              // Solo produce inglés
    "is_active": true,
    "is_default": false
  }'
```

**Resultado**:
- ✅ `es → en` ✅ `ca → en` ✅ `fr → en` ✅ `de → en` ✅ `en → en`
- ✗ `es → fr` ✗ `en → es` (francés/español no están en output)

---

### Escenario 4: Pipeline de Múltiples Proveedores

**Estrategia**: Diferentes modelos para diferentes pares lingüísticos

```bash
# Provider 1: Salamandra para lenguas ibéricas
{
  "name": "Salamandra Ibérico",
  "input_language_ids": [1, 2, 6],  // es, ca, gl (gallego)
  "output_language_ids": [1, 2, 6],
  "is_default": true
}

# Provider 2: Modelo genérico para inglés-europeo
{
  "name": "Generic EU Translator",
  "input_language_ids": [3, 4, 5],  // en, fr, de
  "output_language_ids": [3, 4, 5],
  "is_default": false
}

# Provider 3: Bridge model para combinaciones no cubiertas
{
  "name": "Universal Bridge",
  "input_language_ids": [1, 2, 3, 4, 5, 6],
  "output_language_ids": [1, 2, 3, 4, 5, 6],
  "is_default": false
}
```

**Uso**:
```python
# Traducción es→ca: usa Provider 1 (default, especializado)
POST /translate {"source": "es", "target": "ca"}

# Traducción en→fr: usa Provider 2 (especificando provider_id)
POST /translate {"source": "en", "target": "fr", "provider_id": 2}

# Traducción es→de: usa Provider 3 (bridge, especificando provider_id)
POST /translate {"source": "es", "target": "de", "provider_id": 3}
```

---

## API Endpoints

### Crear Proveedor con Pares de Idiomas

**Endpoint**: `POST /v1/translations/providers`
**Permisos**: `translations:manage`
**Código fuente**: app/api/translations.py:129-137

#### Request

```json
{
  "name": "Salamandra 2B Multilingüe",
  "provider_type": "huggingface",
  "endpoint": "https://api-inference.huggingface.co/models/BSC-LT/salamandra-2b",
  "api_key": "hf_xxxxxxxxxxxxxxxxx",
  "region": null,
  "input_language_ids": [1, 2, 3, 5],
  "output_language_ids": [1, 2, 4, 6],
  "is_active": true,
  "is_default": false,
  "configuration": {
    "max_new_tokens": 512,
    "do_sample": false
  }
}
```

#### Response (201 Created)

```json
{
  "id": 15,
  "name": "Salamandra 2B Multilingüe",
  "provider_type": "huggingface",
  "endpoint": "https://api-inference.huggingface.co/models/BSC-LT/salamandra-2b",
  "region": null,
  "input_language_ids": [1, 2, 3, 5],
  "output_language_ids": [1, 2, 4, 6],
  "input_languages": [
    {"id": 1, "code": "es", "name": "Spanish", "native_name": "Español", "is_active": true, "sort_order": 10},
    {"id": 2, "code": "ca", "name": "Catalan", "native_name": "Català", "is_active": true, "sort_order": 20},
    {"id": 3, "code": "en", "name": "English", "native_name": "English", "is_active": true, "sort_order": 30},
    {"id": 5, "code": "de", "name": "German", "native_name": "Deutsch", "is_active": true, "sort_order": 50}
  ],
  "output_languages": [
    {"id": 1, "code": "es", "name": "Spanish", "native_name": "Español", "is_active": true, "sort_order": 10},
    {"id": 2, "code": "ca", "name": "Catalan", "native_name": "Català", "is_active": true, "sort_order": 20},
    {"id": 4, "code": "fr", "name": "French", "native_name": "Français", "is_active": true, "sort_order": 40},
    {"id": 6, "code": "it", "name": "Italian", "native_name": "Italiano", "is_active": true, "sort_order": 60}
  ],
  "api_key": null,
  "is_active": true,
  "is_default": false,
  "configuration": {"max_new_tokens": 512, "do_sample": false},
  "created_at": "2025-01-20T14:30:00Z",
  "updated_at": "2025-01-20T14:30:00Z"
}
```

**Nota**: `api_key` es `null` para usuarios no-admin. Solo superusers y rol `admin` ven la clave descifrada.

---

### Actualizar Pares de Idiomas

**Endpoint**: `PUT /v1/translations/providers/{provider_id}`
**Permisos**: `translations:manage`
**Código fuente**: app/api/translations.py:153-164

#### Request (ejemplo: agregar italiano como entrada)

```json
{
  "input_language_ids": [1, 2, 3, 5, 6]
}
```

#### Response (200 OK)

```json
{
  "id": 15,
  "input_language_ids": [1, 2, 3, 5, 6],
  "input_languages": [
    {"id": 1, "code": "es", ...},
    {"id": 2, "code": "ca", ...},
    {"id": 3, "code": "en", ...},
    {"id": 5, "code": "de", ...},
    {"id": 6, "code": "it", ...}
  ],
  "output_language_ids": [1, 2, 4, 6],
  "output_languages": [...],
  ...
}
```

---

### Listar Proveedores con Capacidades

**Endpoint**: `GET /v1/translations/providers`
**Permisos**: `translations:read` o `translations:translate`
**Código fuente**: app/api/translations.py:113-126

#### Response (200 OK)

```json
[
  {
    "id": 1,
    "name": "Salamandra 7B Default",
    "provider_type": "huggingface",
    "input_language_ids": [1, 2, 3, 4, 5],
    "output_language_ids": [1, 2, 3, 4, 5],
    "input_languages": [...],
    "output_languages": [...],
    "is_active": true,
    "is_default": true,
    ...
  },
  {
    "id": 2,
    "name": "Salamandra Regional",
    "provider_type": "huggingface",
    "input_language_ids": [1, 2],
    "output_language_ids": [1, 2],
    "input_languages": [
      {"id": 1, "code": "es", "name": "Spanish", ...},
      {"id": 2, "code": "ca", "name": "Catalan", ...}
    ],
    "output_languages": [
      {"id": 1, "code": "es", "name": "Spanish", ...},
      {"id": 2, "code": "ca", "name": "Catalan", ...}
    ],
    "is_active": true,
    "is_default": false,
    ...
  }
]
```

**Uso en UI**: Mostrar selector de proveedores con indicadores visuales:

```
┌─────────────────────────────────────────────────────┐
│ Selecciona proveedor para ca → es                  │
├─────────────────────────────────────────────────────┤
│ ● Salamandra 7B Default (Recomendado)              │
│   Soporta: es, ca, en, fr, de ↔ es, ca, en, fr, de │
│                                                     │
│ ● Salamandra Regional                               │
│   Soporta: es, ca ↔ es, ca (Especializado)         │
└─────────────────────────────────────────────────────┘
```

---

## Validación en Traducción

### Estado Actual (Implementado)

**Código**: app/api/translations.py:284-298

```python
@router.post("/translate", response_model=TranslationResponse)
async def translate_text(request: TranslationRequest, ...):
    # ✅ Validación 1: Idioma origen existe y está activo
    source_lang = await crud_translation.get_language_by_code(db, request.source_language_code)
    if not source_lang or not source_lang.is_active:
        raise HTTPException(status_code=400, detail=f"Source language '{request.source_language_code}' not available")

    # ✅ Validación 2: Idioma destino existe y está activo
    target_lang = await crud_translation.get_language_by_code(db, request.target_language_code)
    if not target_lang or not target_lang.is_active:
        raise HTTPException(status_code=400, detail=f"Target language '{request.target_language_code}' not available")

    # ⚠️ NO VALIDADO: Si el proveedor soporta el par source → target
    service = await TranslationServiceFactory.get_service(db, request.provider_id)
    translated_text = await service.translate(...)
```

**Limitación**: Actualmente NO se verifica si `source_lang.id` está en `provider.input_language_ids` y `target_lang.id` está en `provider.output_language_ids`.

---

### Propuesta de Validación Estricta

**Nueva función de validación**:

```python
# En app/crud/translation.py

async def validate_provider_language_pair(
    db: AsyncSession,
    provider: TranslationProvider,
    source_language_id: int,
    target_language_id: int
) -> tuple[bool, str]:
    """
    Validate if a provider supports a specific language pair.

    Returns:
        (is_valid, error_message)
    """
    # Check input language support
    if source_language_id not in (provider.input_language_ids or []):
        source_lang = await get_language(db, source_language_id)
        return False, f"Provider '{provider.name}' does not support '{source_lang.code}' as input language"

    # Check output language support
    if target_language_id not in (provider.output_language_ids or []):
        target_lang = await get_language(db, target_language_id)
        return False, f"Provider '{provider.name}' does not support '{target_lang.code}' as output language"

    return True, ""
```

**Integración en endpoint**:

```python
# En app/api/translations.py

@router.post("/translate", response_model=TranslationResponse)
async def translate_text(request: TranslationRequest, ...):
    # ... validaciones existentes de source_lang y target_lang ...

    # Obtener proveedor
    if request.provider_id:
        provider = await crud_translation.get_provider(db, request.provider_id)
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
    else:
        provider = await crud_translation.get_default_provider(db)
        if not provider:
            raise HTTPException(status_code=500, detail="No default provider configured")

    # ✅ NUEVA VALIDACIÓN: Verificar soporte del par lingüístico
    is_valid, error_msg = await crud_translation.validate_provider_language_pair(
        db, provider, source_lang.id, target_lang.id
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # Proceder con la traducción
    service = await TranslationServiceFactory.get_service(db, request.provider_id)
    ...
```

**Respuesta de error**:

```json
// Request
POST /v1/translations/translate
{
  "source_language_code": "fr",
  "target_language_code": "it",
  "text": "Bonjour le monde",
  "provider_id": 2  // Salamandra Regional (solo es, ca)
}

// Response 400 Bad Request
{
  "detail": "Provider 'Salamandra Regional' does not support 'fr' as input language"
}
```

---

## Casos de Uso Prácticos

### Caso 1: Configuración Inicial Multi-Idioma

**Objetivo**: Configurar Salamandra 2B para soportar 5 idiomas comunes

```python
#!/usr/bin/env python3
"""Script de configuración inicial de proveedor multi-idioma"""

import requests
import json

API_URL = "https://api.bsc-translation.com/v1/translations"
ADMIN_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

def get_active_languages():
    """Obtener todos los idiomas activos"""
    response = requests.get(
        f"{API_URL}/languages?only_active=true&limit=100",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
    )
    response.raise_for_status()
    return response.json()

def create_universal_provider(language_ids: list[int]):
    """Crear proveedor universal con todos los idiomas"""
    payload = {
        "name": "Salamandra 2B Universal",
        "provider_type": "huggingface",
        "endpoint": "https://api-inference.huggingface.co/models/BSC-LT/salamandra-2b",
        "api_key": "hf_xxxxxxxxxxxxxxxxxxxx",
        "input_language_ids": language_ids,
        "output_language_ids": language_ids,  # Mismo set para bidireccional
        "is_active": True,
        "is_default": True,
        "configuration": {
            "max_new_tokens": 512,
            "do_sample": False,
            "chunk_chars": 800
        }
    }

    response = requests.post(
        f"{API_URL}/providers",
        headers={
            "Authorization": f"Bearer {ADMIN_TOKEN}",
            "Content-Type": "application/json"
        },
        json=payload
    )
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    # Obtener idiomas activos
    languages = get_active_languages()
    print(f"✓ Encontrados {len(languages)} idiomas activos")

    # Extraer IDs
    language_ids = [lang["id"] for lang in languages]
    print(f"  IDs: {language_ids}")

    # Crear proveedor
    provider = create_universal_provider(language_ids)
    print(f"✓ Proveedor creado: {provider['name']} (ID: {provider['id']})")
    print(f"  Input languages: {len(provider['input_languages'])}")
    print(f"  Output languages: {len(provider['output_languages'])}")
    print(f"  Pares posibles: {len(language_ids) * len(language_ids)}")
```

**Salida**:

```
✓ Encontrados 5 idiomas activos
  IDs: [1, 2, 3, 4, 5]
✓ Proveedor creado: Salamandra 2B Universal (ID: 1)
  Input languages: 5
  Output languages: 5
  Pares posibles: 25
```

---

### Caso 2: Modelo Especializado para Lenguas Cooficiales

**Objetivo**: Crear proveedor optimizado solo para lenguas cooficiales de España

```bash
#!/bin/bash
# create_coofficial_provider.sh

API_URL="https://api.bsc-translation.com/v1/translations"
TOKEN="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Obtener IDs de lenguas cooficiales
LANGS=$(curl -s -X GET "${API_URL}/languages?only_active=true" -H "Authorization: $TOKEN")

# Filtrar solo: es, ca, gl, eu (Español, Catalán, Gallego, Euskera)
ES_ID=$(echo $LANGS | jq -r '.[] | select(.code=="es") | .id')
CA_ID=$(echo $LANGS | jq -r '.[] | select(.code=="ca") | .id')
GL_ID=$(echo $LANGS | jq -r '.[] | select(.code=="gl") | .id')
EU_ID=$(echo $LANGS | jq -r '.[] | select(.code=="eu") | .id')

# Crear proveedor especializado
curl -X POST "${API_URL}/providers" \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d @- <<EOF
{
  "name": "Salamandra Lenguas Cooficiales ES",
  "provider_type": "huggingface",
  "endpoint": "https://custom.bsc.es/salamandra-coofficial",
  "api_key": "hf_coofficial_key",
  "input_language_ids": [$ES_ID, $CA_ID, $GL_ID, $EU_ID],
  "output_language_ids": [$ES_ID, $CA_ID, $GL_ID, $EU_ID],
  "is_active": true,
  "is_default": false,
  "configuration": {
    "model": "salamandra-coofficial-7b",
    "max_new_tokens": 1024,
    "temperature": 0.3
  }
}
EOF
```

**Resultado**: Proveedor que solo maneja traducciones entre lenguas cooficiales (16 pares: es↔ca, es↔gl, es↔eu, ca↔gl, ca↔eu, gl↔eu)

---

### Caso 3: Migración de Proveedor con Expansión de Idiomas

**Escenario**: Actualizar proveedor existente para soportar nuevos idiomas añadidos a la plataforma

```python
#!/usr/bin/env python3
"""Expandir soporte de idiomas de un proveedor existente"""

import requests

API_URL = "https://api.bsc-translation.com/v1/translations"
ADMIN_TOKEN = "Bearer ..."
PROVIDER_ID = 1

def get_provider_current_languages(provider_id: int):
    """Obtener idiomas actuales del proveedor"""
    response = requests.get(
        f"{API_URL}/providers/{provider_id}",
        headers={"Authorization": ADMIN_TOKEN}
    )
    response.raise_for_status()
    provider = response.json()
    return (
        provider["input_language_ids"],
        provider["output_language_ids"],
        provider
    )

def get_all_active_languages():
    """Obtener todos los idiomas activos de la plataforma"""
    response = requests.get(
        f"{API_URL}/languages?only_active=true&limit=100",
        headers={"Authorization": ADMIN_TOKEN}
    )
    response.raise_for_status()
    return [lang["id"] for lang in response.json()]

def expand_provider_languages(provider_id: int, new_language_ids: list[int]):
    """Actualizar proveedor con nuevos idiomas"""
    response = requests.put(
        f"{API_URL}/providers/{provider_id}",
        headers={
            "Authorization": ADMIN_TOKEN,
            "Content-Type": "application/json"
        },
        json={
            "input_language_ids": new_language_ids,
            "output_language_ids": new_language_ids
        }
    )
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    # Estado actual
    current_input, current_output, provider = get_provider_current_languages(PROVIDER_ID)
    print(f"Proveedor: {provider['name']}")
    print(f"  Idiomas actuales (input): {len(current_input)}")
    print(f"  Idiomas actuales (output): {len(current_output)}")

    # Idiomas disponibles en plataforma
    all_languages = get_all_active_languages()
    print(f"\nIdiomas activos en plataforma: {len(all_languages)}")

    # Calcular nuevos idiomas
    new_input = set(current_input) | set(all_languages)
    new_output = set(current_output) | set(all_languages)

    added_input = new_input - set(current_input)
    added_output = new_output - set(current_output)

    if added_input or added_output:
        print(f"\n➜ Se añadirán {len(added_input)} idiomas de entrada")
        print(f"➜ Se añadirán {len(added_output)} idiomas de salida")

        # Confirmar
        confirm = input("\n¿Proceder con la actualización? (y/n): ")
        if confirm.lower() == 'y':
            updated = expand_provider_languages(PROVIDER_ID, list(new_input))
            print(f"\n✓ Proveedor actualizado")
            print(f"  Idiomas nuevos (input): {len(updated['input_language_ids'])}")
            print(f"  Idiomas nuevos (output): {len(updated['output_language_ids'])}")
        else:
            print("Cancelado")
    else:
        print("\n✓ El proveedor ya soporta todos los idiomas activos")
```

**Salida**:

```
Proveedor: Salamandra 2B Universal
  Idiomas actuales (input): 5
  Idiomas actuales (output): 5

Idiomas activos en plataforma: 7

➜ Se añadirán 2 idiomas de entrada
➜ Se añadirán 2 idiomas de salida

¿Proceder con la actualización? (y/n): y

✓ Proveedor actualizado
  Idiomas nuevos (input): 7
  Idiomas nuevos (output): 7
```

---

### Caso 4: Auditoría de Cobertura Lingüística

**Objetivo**: Generar reporte de qué pares lingüísticos están cubiertos por qué proveedores

```python
#!/usr/bin/env python3
"""Auditoría de cobertura de pares de traducción"""

import requests
from collections import defaultdict
from itertools import product

API_URL = "https://api.bsc-translation.com/v1/translations"
TOKEN = "Bearer ..."

def get_all_providers():
    response = requests.get(f"{API_URL}/providers", headers={"Authorization": TOKEN})
    response.raise_for_status()
    return response.json()

def get_all_languages():
    response = requests.get(f"{API_URL}/languages?only_active=true", headers={"Authorization": TOKEN})
    response.raise_for_status()
    return response.json()

def generate_coverage_report():
    providers = get_all_providers()
    languages = {lang["id"]: lang["code"] for lang in get_all_languages()}

    # Mapa de pares → proveedores que los soportan
    pair_coverage = defaultdict(list)

    for provider in providers:
        if not provider["is_active"]:
            continue

        input_ids = provider["input_language_ids"]
        output_ids = provider["output_language_ids"]

        # Generar todos los pares posibles para este proveedor
        for src_id, tgt_id in product(input_ids, output_ids):
            if src_id == tgt_id:
                continue  # Ignorar reflexivos

            src_code = languages.get(src_id, "???")
            tgt_code = languages.get(tgt_id, "???")
            pair = f"{src_code}→{tgt_code}"

            pair_coverage[pair].append(provider["name"])

    # Reporte
    print("=" * 80)
    print(" REPORTE DE COBERTURA DE PARES DE TRADUCCIÓN".center(80))
    print("=" * 80)

    # Pares con múltiples proveedores
    multi_coverage = {pair: provs for pair, provs in pair_coverage.items() if len(provs) > 1}
    print(f"\nPares con MÚLTIPLES proveedores ({len(multi_coverage)}):")
    for pair in sorted(multi_coverage.keys()):
        print(f"  {pair:10} → {', '.join(multi_coverage[pair])}")

    # Pares con un solo proveedor
    single_coverage = {pair: provs for pair, provs in pair_coverage.items() if len(provs) == 1}
    print(f"\nPares con UN SOLO proveedor ({len(single_coverage)}):")
    for pair in sorted(single_coverage.keys()):
        print(f"  {pair:10} → {single_coverage[pair][0]}")

    # Pares sin cobertura
    all_possible_pairs = set()
    for src_id, tgt_id in product(languages.keys(), repeat=2):
        if src_id != tgt_id:
            src_code = languages[src_id]
            tgt_code = languages[tgt_id]
            all_possible_pairs.add(f"{src_code}→{tgt_code}")

    covered_pairs = set(pair_coverage.keys())
    uncovered = all_possible_pairs - covered_pairs

    print(f"\nPares SIN cobertura ({len(uncovered)}):")
    for pair in sorted(uncovered):
        print(f"  {pair}")

    # Resumen
    print("\n" + "=" * 80)
    print(f"Total de idiomas activos: {len(languages)}")
    print(f"Total de pares posibles (sin reflexivos): {len(all_possible_pairs)}")
    print(f"Pares cubiertos: {len(covered_pairs)} ({len(covered_pairs)/len(all_possible_pairs)*100:.1f}%)")
    print(f"Pares sin cubrir: {len(uncovered)} ({len(uncovered)/len(all_possible_pairs)*100:.1f}%)")
    print("=" * 80)

if __name__ == "__main__":
    generate_coverage_report()
```

**Salida de ejemplo**:

```
================================================================================
              REPORTE DE COBERTURA DE PARES DE TRADUCCIÓN
================================================================================

Pares con MÚLTIPLES proveedores (12):
  ca→es      → Salamandra 7B Universal, Salamandra Regional
  es→ca      → Salamandra 7B Universal, Salamandra Regional
  en→es      → Salamandra 7B Universal, Multi-to-English Converter
  en→fr      → Salamandra 7B Universal, Generic EU Translator
  ...

Pares con UN SOLO proveedor (18):
  de→fr      → Generic EU Translator
  gl→ca      → Salamandra Lenguas Cooficiales ES
  eu→es      → Salamandra Lenguas Cooficiales ES
  ...

Pares SIN cobertura (6):
  eu→fr
  gl→de
  it→eu
  ...

================================================================================
Total de idiomas activos: 7
Total de pares posibles (sin reflexivos): 42
Pares cubiertos: 36 (85.7%)
Pares sin cubrir: 6 (14.3%)
================================================================================
```

---

## Gestión Avanzada

### Estrategia 1: Auto-Poblado en Migraciones

**Archivo**: migrations/versions/a1b2c3d4e5f6_007_populate_provider_language_ids.py

```python
"""007_populate_provider_language_ids

Populate existing providers with all available languages as both input and output.
"""
from alembic import op
import sqlalchemy as sa
import json

def upgrade() -> None:
    """Set input/output languages for existing providers to all active languages."""
    conn = op.get_bind()

    # Obtener todos los IDs de idiomas activos
    lang_rows = conn.execute(
        sa.text("SELECT id FROM languages WHERE is_active = true ORDER BY sort_order, name")
    ).fetchall()

    language_ids = [row[0] for row in lang_rows]
    languages_json = json.dumps(language_ids)

    # Actualizar todos los proveedores existentes
    conn.execute(
        sa.text(
            "UPDATE translation_providers "
            "SET input_language_ids = :langs, output_language_ids = :langs"
        ),
        {"langs": languages_json},
    )

def downgrade() -> None:
    """Clear input/output language lists on downgrade."""
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE translation_providers "
            "SET input_language_ids = '[]', output_language_ids = '[]'"
        )
    )
```

**Beneficio**: Al ejecutar `alembic upgrade head`, todos los proveedores existentes se configuran automáticamente con todos los idiomas activos.

---

### Estrategia 2: Endpoint de Validación Previa

**Propuesta**: Endpoint dedicado para verificar si un par es soportado

```python
# En app/api/translations.py

@router.get("/providers/{provider_id}/supports")
async def check_language_pair_support(
    provider_id: int,
    source_code: str = Query(..., description="Source language code"),
    target_code: str = Query(..., description="Target language code"),
    db: AsyncSession = Depends(get_session),
    _: User = Depends(PermissionChecker(["translations:read"])),
):
    """
    Check if a provider supports a specific language pair.

    Example: GET /providers/1/supports?source_code=ca&target_code=es
    """
    # Obtener proveedor
    provider = await crud_translation.get_provider(db, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Obtener idiomas
    source_lang = await crud_translation.get_language_by_code(db, source_code)
    target_lang = await crud_translation.get_language_by_code(db, target_code)

    if not source_lang or not target_lang:
        raise HTTPException(status_code=404, detail="Language not found")

    # Verificar soporte
    supports_input = source_lang.id in (provider.input_language_ids or [])
    supports_output = target_lang.id in (provider.output_language_ids or [])
    is_supported = supports_input and supports_output

    return {
        "provider_id": provider_id,
        "provider_name": provider.name,
        "source_language": {"code": source_code, "id": source_lang.id},
        "target_language": {"code": target_code, "id": target_lang.id},
        "is_supported": is_supported,
        "supports_as_input": supports_input,
        "supports_as_output": supports_output
    }
```

**Uso**:

```bash
curl -X GET "https://api.bsc.com/v1/translations/providers/2/supports?source_code=ca&target_code=es" \
  -H "Authorization: Bearer $TOKEN"

# Response
{
  "provider_id": 2,
  "provider_name": "Salamandra Regional",
  "source_language": {"code": "ca", "id": 2},
  "target_language": {"code": "es", "id": 1},
  "is_supported": true,
  "supports_as_input": true,
  "supports_as_output": true
}
```

---

### Estrategia 3: Selector de Proveedor Automático

**Concepto**: Función que encuentra el mejor proveedor para un par dado

```python
# En app/crud/translation.py

async def find_best_provider_for_pair(
    db: AsyncSession,
    source_language_id: int,
    target_language_id: int,
    prefer_specialized: bool = True
) -> TranslationProvider | None:
    """
    Find the best provider for a language pair.

    Args:
        prefer_specialized: If True, prefer providers with fewer language pairs (more specialized)

    Returns:
        Best provider or None if no provider supports the pair
    """
    # Obtener proveedores activos
    providers = await get_providers(db, only_active=True, limit=100)

    # Filtrar proveedores que soporten el par
    valid_providers = []
    for provider in providers:
        if (source_language_id in (provider.input_language_ids or []) and
            target_language_id in (provider.output_language_ids or [])):
            valid_providers.append(provider)

    if not valid_providers:
        return None

    # Estrategia de selección
    if prefer_specialized:
        # Preferir proveedores con menos idiomas (más especializados)
        valid_providers.sort(
            key=lambda p: len(p.input_language_ids or []) + len(p.output_language_ids or [])
        )
    else:
        # Preferir proveedores con más idiomas (más versátiles)
        valid_providers.sort(
            key=lambda p: len(p.input_language_ids or []) + len(p.output_language_ids or []),
            reverse=True
        )

    # Si hay un default en los válidos, priorizarlo
    default_provider = next((p for p in valid_providers if p.is_default), None)
    if default_provider:
        return default_provider

    # Retornar el primero según la estrategia
    return valid_providers[0]
```

**Uso en endpoint**:

```python
@router.post("/translate/auto")
async def translate_with_auto_provider(
    request: TranslationRequest,
    db: AsyncSession = Depends(get_session),
    ...
):
    """Translate using automatic provider selection."""
    source_lang = await crud_translation.get_language_by_code(db, request.source_language_code)
    target_lang = await crud_translation.get_language_by_code(db, request.target_language_code)

    # Encontrar mejor proveedor
    provider = await crud_translation.find_best_provider_for_pair(
        db, source_lang.id, target_lang.id, prefer_specialized=True
    )

    if not provider:
        raise HTTPException(
            status_code=400,
            detail=f"No provider available for {source_lang.code} → {target_lang.code}"
        )

    # Usar el proveedor seleccionado
    service = await TranslationServiceFactory.get_service(db, provider.id)
    ...
```

---

## Mejores Prácticas

### 1. Configuración de Idiomas

✅ **HACER**:
- Configurar `input_language_ids` y `output_language_ids` según las capacidades **reales** del modelo
- Probar pares lingüísticos antes de añadirlos a producción
- Mantener simetría (input=output) solo si el modelo realmente es bidireccional
- Documentar limitaciones específicas del modelo en `configuration`

❌ **EVITAR**:
- Configurar todos los idiomas sin verificar que el modelo los soporta
- Asumir que un modelo multilingüe soporta todas las combinaciones
- Dejar listas vacías (violará validación de esquema)
- Ignorar idiomas regionales que el modelo no distingue (ej: es-ES vs es-MX)

**Ejemplo**:

```json
// ❌ MAL: Asumir soporte universal sin verificar
{
  "name": "Modelo Desconocido",
  "input_language_ids": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
  "output_language_ids": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
}

// ✅ BIEN: Solo idiomas verificados con tests
{
  "name": "Salamandra 2B Testado",
  "input_language_ids": [1, 2, 3],  // es, ca, en confirmados
  "output_language_ids": [1, 2, 3],
  "configuration": {
    "tested_pairs": ["es→ca", "ca→es", "en→es", "es→en"],
    "quality_metrics": {
      "es→ca": {"bleu": 42.5, "comet": 0.78},
      "ca→es": {"bleu": 41.2, "comet": 0.76}
    }
  }
}
```

---

### 2. Validación y Testing

```python
# tests/test_language_pairs.py

import pytest
from app.schemas.translation import TranslationProviderCreate

def test_provider_requires_input_languages():
    """Provider creation must fail without input_language_ids"""
    with pytest.raises(ValueError, match="At least one language ID is required"):
        TranslationProviderCreate(
            name="Test",
            provider_type="huggingface",
            api_key="test_key",
            input_language_ids=[],  # ❌ Vacío
            output_language_ids=[1, 2]
        )

def test_provider_requires_output_languages():
    """Provider creation must fail without output_language_ids"""
    with pytest.raises(ValueError, match="At least one language ID is required"):
        TranslationProviderCreate(
            name="Test",
            provider_type="huggingface",
            api_key="test_key",
            input_language_ids=[1, 2],
            output_language_ids=[]  # ❌ Vacío
        )

@pytest.mark.asyncio
async def test_translation_with_unsupported_pair(async_client, admin_token):
    """Translation should fail if provider doesn't support the pair"""
    # Crear proveedor que solo soporta es, ca
    response = await async_client.post(
        "/v1/translations/providers",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Regional Only",
            "provider_type": "huggingface",
            "endpoint": "https://test.com",
            "api_key": "key",
            "input_language_ids": [1, 2],  # es, ca
            "output_language_ids": [1, 2]
        }
    )
    provider_id = response.json()["id"]

    # Intentar traducir de francés a alemán (no soportado)
    response = await async_client.post(
        "/v1/translations/translate",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "source_language_code": "fr",
            "target_language_code": "de",
            "text": "Bonjour",
            "provider_id": provider_id
        }
    )

    # Con validación estricta implementada, debería retornar 400
    assert response.status_code == 400
    assert "does not support" in response.json()["detail"]
```

---

### 3. Monitoreo y Observabilidad

**Métricas clave**:

```python
# app/api/translations.py (con instrumentación Prometheus)

from prometheus_client import Counter, Histogram

translation_requests = Counter(
    'translation_requests_total',
    'Total translation requests',
    ['provider', 'source_lang', 'target_lang', 'status']
)

unsupported_pairs = Counter(
    'unsupported_language_pairs_total',
    'Requests for unsupported language pairs',
    ['provider', 'source_lang', 'target_lang']
)

@router.post("/translate")
async def translate_text(...):
    try:
        # ... validaciones ...

        # Verificar soporte del par
        if source_lang.id not in (provider.input_language_ids or []):
            unsupported_pairs.labels(
                provider=provider.name,
                source_lang=request.source_language_code,
                target_lang=request.target_language_code
            ).inc()
            raise HTTPException(...)

        # Traducir
        translated_text = await service.translate(...)

        translation_requests.labels(
            provider=provider.name,
            source_lang=request.source_language_code,
            target_lang=request.target_language_code,
            status='success'
        ).inc()

        return translation_record

    except HTTPException as e:
        translation_requests.labels(
            provider=provider.name if provider else 'unknown',
            source_lang=request.source_language_code,
            target_lang=request.target_language_code,
            status='error'
        ).inc()
        raise
```

**Dashboard Grafana**:

```promql
# Panel 1: Top 10 pares de traducción más solicitados
topk(10, sum by (source_lang, target_lang) (
  rate(translation_requests_total[5m])
))

# Panel 2: Pares no soportados (requieren atención)
sum by (provider, source_lang, target_lang) (
  rate(unsupported_language_pairs_total[1h])
) > 0

# Panel 3: Tasa de éxito por proveedor
sum by (provider) (rate(translation_requests_total{status="success"}[5m]))
/
sum by (provider) (rate(translation_requests_total[5m]))
```

---

### 4. Documentación y Transparencia

**Exponer capacidades en UI**:

```typescript
// React component: ProviderSelector.tsx

interface Provider {
  id: number;
  name: string;
  input_languages: Language[];
  output_languages: Language[];
}

function ProviderSelector({ sourceLang, targetLang }: Props) {
  const { data: providers } = useQuery<Provider[]>('/providers');

  const compatibleProviders = providers?.filter(p =>
    p.input_languages.some(l => l.code === sourceLang) &&
    p.output_languages.some(l => l.code === targetLang)
  );

  return (
    <select>
      {compatibleProviders?.length === 0 && (
        <option disabled>
          ⚠️ Ningún proveedor soporta {sourceLang} → {targetLang}
        </option>
      )}

      {compatibleProviders?.map(provider => (
        <option key={provider.id} value={provider.id}>
          {provider.name}
          {provider.input_languages.length < 5 && " (Especializado)"}
        </option>
      ))}
    </select>
  );
}
```

---

## Troubleshooting

### Problema 1: "At least one language ID is required"

**Error**:

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "input_language_ids"],
      "msg": "At least one language ID is required"
    }
  ]
}
```

**Causa**: Intentar crear/actualizar proveedor con listas vacías

**Solución**:

```bash
# ❌ MAL
curl -X POST /providers -d '{"input_language_ids": [], ...}'

# ✅ BIEN
curl -X POST /providers -d '{"input_language_ids": [1, 2, 3], ...}'
```

---

### Problema 2: Traducción Funciona Pero con Calidad Baja

**Síntoma**: Endpoint retorna 200 OK pero la traducción es incorrecta/incompleta

**Causa posible**: El modelo NO soporta realmente el par, pero la validación no está implementada

**Diagnóstico**:

```python
# Verificar configuración del proveedor
GET /providers/{provider_id}

# Revisar logs del servicio de traducción
# Buscar errores silenciados en HuggingFaceTranslationService
```

**Solución**:
1. Implementar validación estricta (ver sección "Validación en Traducción")
2. Remover idiomas no soportados de `input_language_ids`/`output_language_ids`
3. Probar con modelos alternativos para ese par

---

### Problema 3: "Language ID list cannot be empty"

**Error** al actualizar:

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "output_language_ids"],
      "msg": "Language ID list cannot be empty"
    }
  ]
}
```

**Causa**: En `PUT /providers/{id}`, intentar vaciar una lista de idiomas

**Solución**:

```bash
# ❌ MAL: Actualizar a lista vacía
curl -X PUT /providers/1 -d '{"output_language_ids": []}'

# ✅ BIEN: Reducir a un mínimo de 1 idioma
curl -X PUT /providers/1 -d '{"output_language_ids": [1]}'

# ✅ ALTERNATIVA: No incluir el campo (no se actualizará)
curl -X PUT /providers/1 -d '{"name": "Nuevo Nombre"}'
```

---

### Problema 4: Pérdida de Datos en Migración

**Escenario**: Después de ejecutar migración 007, algunos proveedores tienen idiomas incorrectos

**Prevención**:

```python
# migrations/versions/a1b2c3d4e5f6_007_populate_provider_language_ids.py

def upgrade() -> None:
    conn = op.get_bind()

    # ✅ MEJOR: Solo actualizar proveedores SIN idiomas configurados
    conn.execute(
        sa.text(
            "UPDATE translation_providers "
            "SET input_language_ids = :langs, output_language_ids = :langs "
            "WHERE input_language_ids = '[]' OR output_language_ids = '[]'"
        ),
        {"langs": languages_json},
    )
```

**Rollback**:

```bash
# Revertir migración
alembic downgrade -1

# Configurar manualmente cada proveedor
curl -X PUT /providers/1 -d '{"input_language_ids": [1, 2], ...}'
```

---

### Problema 5: IDs de Idiomas Inconsistentes

**Síntoma**: Provider tiene `input_language_ids: [10, 20, 30]` pero esos IDs no existen en `languages`

**Diagnóstico**:

```sql
-- Encontrar IDs huérfanos
SELECT p.id, p.name, p.input_language_ids, p.output_language_ids
FROM translation_providers p
WHERE EXISTS (
  SELECT 1 FROM jsonb_array_elements_text(p.input_language_ids::jsonb) AS lang_id
  WHERE lang_id::int NOT IN (SELECT id FROM languages)
);
```

**Solución**:

```python
# Script de limpieza
import requests

API_URL = "https://api.bsc.com/v1/translations"
TOKEN = "Bearer ..."

def cleanup_invalid_language_ids():
    # Obtener IDs válidos
    languages = requests.get(f"{API_URL}/languages?only_active=true").json()
    valid_ids = {lang["id"] for lang in languages}

    # Obtener proveedores
    providers = requests.get(f"{API_URL}/providers", headers={"Authorization": TOKEN}).json()

    for provider in providers:
        input_ids = set(provider["input_language_ids"])
        output_ids = set(provider["output_language_ids"])

        # Filtrar solo IDs válidos
        clean_input = list(input_ids & valid_ids)
        clean_output = list(output_ids & valid_ids)

        if clean_input != provider["input_language_ids"] or clean_output != provider["output_language_ids"]:
            print(f"Limpiando proveedor {provider['id']}: {provider['name']}")
            requests.put(
                f"{API_URL}/providers/{provider['id']}",
                headers={"Authorization": TOKEN},
                json={
                    "input_language_ids": clean_input,
                    "output_language_ids": clean_output
                }
            )

cleanup_invalid_language_ids()
```

---

## Resumen Técnico

### Campos Clave

| Campo                  | Tipo  | Validación                                 | Propósito                                   |
|------------------------|-------|--------------------------------------------|---------------------------------------------|
| `input_language_ids`   | JSON  | Array no vacío de integers                 | IDs de idiomas que el proveedor acepta como **origen** |
| `output_language_ids`  | JSON  | Array no vacío de integers                 | IDs de idiomas que el proveedor produce como **destino** |

### Flujo de Validación

```
Request → Validar idiomas activos → Obtener proveedor → [⚠️ Validar par NO implementado] → Traducir → Guardar
```

### Archivos Relevantes

- **Modelo**: `app/models/translation.py:10-33` (TranslationProvider)
- **Esquemas**: `app/schemas/translation.py:12-68` (TranslationProviderCreate/Update)
- **CRUD**: `app/crud/translation.py:21-42` (create_provider)
- **API**: `app/api/translations.py:129-189` (endpoints de proveedores)
- **Migración**: `migrations/versions/9d5a9d7b12b0_006_add_provider_language_ids.py`

### Capacidades Actuales

✅ Configuración dinámica de idiomas por proveedor
✅ Validación de idiomas activos en plataforma
✅ Respuestas enriquecidas con objetos Language completos
✅ Migración automática para poblar idiomas
⚠️ **Falta**: Validación de soporte de par (source→target) antes de traducir

---

**Fecha de documentación**: 2025-01-20
**Versión del sistema**: core_bsctranslation v1.0
**Autor**: Equipo BSC Translation Platform
