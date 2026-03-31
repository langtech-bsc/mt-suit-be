# Selección Dinámica de Modelos Salamandra para Traducción

## Índice

1. [Descripción General](#descripción-general)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Modelos Salamandra Disponibles](#modelos-salamandra-disponibles)
4. [Sistema de Providers](#sistema-de-providers)
5. [Configuración de Providers](#configuración-de-providers)
6. [Selección Dinámica de Modelos](#selección-dinámica-de-modelos)
7. [API Endpoints](#api-endpoints)
8. [Ejemplos de Uso](#ejemplos-de-uso)
9. [Gestión de Idiomas](#gestión-de-idiomas)
10. [Mejores Prácticas](#mejores-prácticas)
11. [Troubleshooting](#troubleshooting)

---

## Descripción General

El sistema de **selección dinámica de modelos Salamandra** permite configurar y utilizar diferentes variantes de los modelos de traducción de BSC (Barcelona Supercomputing Center) de forma flexible y escalable.

### Características Principales

- **Múltiples Providers**: Soporte para diferentes endpoints y configuraciones de Hugging Face
- **Selección Flexible**: Permite elegir el provider específico por solicitud o usar el predeterminado
- **Gestión de Idiomas**: Control granular sobre idiomas de entrada y salida soportados por cada provider
- **Configuración Persistente**: Almacenamiento en base de datos con encriptación de API keys
- **Factory Pattern**: Inicialización automática de servicios según el provider seleccionado

### Casos de Uso

1. **Optimización de Costos**: Usar modelos pequeños (2B) para textos cortos, modelos grandes (7B) para traducciones complejas
2. **Balance Calidad/Velocidad**: Alternar entre modelos según requisitos de latencia
3. **Testing A/B**: Comparar resultados de diferentes modelos o configuraciones
4. **Failover**: Cambiar automáticamente a providers de respaldo en caso de fallos
5. **Multi-región**: Distribuir carga entre diferentes endpoints regionales

---

## Arquitectura del Sistema

### Diagrama de Componentes

```
┌──────────────────────────────────────────────────────────────────┐
│                         Cliente API                               │
│         /translate?provider_id=1  o  /translate (default)        │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                   API Endpoint (FastAPI)                          │
│  app/api/translations.py:276-327                                 │
│  - Valida idiomas de origen/destino                              │
│  - Resuelve provider_id → Provider específico o default          │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│              TranslationServiceFactory                            │
│  app/services/translation_service.py:496-559                     │
│  - Obtiene provider desde DB (por ID o default)                  │
│  - Valida que esté activo                                        │
│  - Desencripta API key                                           │
│  - Extrae configuración (model, parameters)                      │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│         HuggingFaceTranslationService Instance                    │
│  app/services/translation_service.py:21-493                      │
│  - Inicializado con: api_key, endpoint, model, parameters        │
│  - Utiliza InferenceClient de Hugging Face                       │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│           Hugging Face Inference Endpoint                         │
│  Endpoint específico configurado en el provider                   │
│  Ejemplo: https://api-inference.huggingface.co/models/...        │
└──────────────────────────────────────────────────────────────────┘
```

### Flujo de Datos

```
1. Request → Endpoint /translate
              ├─ provider_id=3 (específico)
              └─ Sin provider_id (usa default)

2. Endpoint valida:
   ├─ source_language_code existe y está activo
   └─ target_language_code existe y está activo

3. Factory resuelve provider:
   ├─ Si provider_id: busca por ID
   └─ Si no: obtiene default (is_default=True, is_active=True)

4. Factory valida provider:
   ├─ Existe en DB
   ├─ is_active = True
   ├─ provider_type = "huggingface"
   └─ endpoint no es NULL

5. Factory inicializa servicio:
   ├─ Desencripta API key
   ├─ Extrae model de configuration.model
   ├─ Extrae parameters de configuration.parameters
   └─ Crea HuggingFaceTranslationService

6. Servicio ejecuta traducción:
   ├─ Divide texto en chunks (800 chars por defecto)
   ├─ Construye prompts optimizados
   ├─ Llama a Hugging Face API
   ├─ Limpia output (remove markers, metadata)
   └─ Retorna texto traducido

7. Endpoint guarda en historial:
   ├─ provider_id
   ├─ source_language_id
   ├─ target_language_id
   ├─ source_text
   ├─ translated_text
   ├─ character_count
   └─ user_id
```

---

## Modelos Salamandra Disponibles

### Familia SalamandraTA

**SalamandraTA** es una familia de modelos de lenguaje multilingües ajustados para traducción y tareas tecnológicas relacionadas con el lenguaje desarrollados por BSC.

#### Soporte Multiidioma

**35 idiomas principales** (y 3 variedades):
- **Lenguas Ibéricas**: Español, Catalán (Valenciano), Gallego, Vasco, Occitano (Aranés), Aragonés, Asturiano
- **Lenguas Románicas**: Francés, Italiano, Portugués, Rumano
- **Lenguas Germánicas**: Inglés, Alemán, Neerlandés, Sueco, Danés, Noruego (Bokmål, Nynorsk)
- **Lenguas Eslavas**: Ruso, Ucraniano, Polaco, Checo, Eslovaco, Esloveno, Búlgaro, Croata, Serbio
- **Lenguas Bálticas**: Letón, Lituano
- **Otras**: Griego, Húngaro, Finlandés, Estonio, Irlandés, Galés, Maltés

### salamandraTA-2b-instruct

**Ubicación**: [BSC-LT/salamandra-2b](https://huggingface.co/BSC-LT/salamandraTA-2b-instruct)

#### Especificaciones Técnicas

| Característica | Valor |
|----------------|-------|
| **Parámetros totales** | 2,253,490,176 (~2.25B) |
| **Parámetros de embedding** | 524,288,000 |
| **Capas** | 24 |
| **Tamaño oculto** | 2,048 |
| **Cabezales de atención** | 16 |
| **Longitud de contexto** | 8,192 tokens |
| **Tamaño del vocabulario** | 256,000 |
| **Precisión** | bfloat16 |
| **Tipo de embedding** | RoPE |
| **Función de activación** | SwiGLU |
| **Normalización de capas** | RMS Norm |
| **Grouped query attention** | ❌ No |
| **Flash attention** | ✅ Sí |

#### Requisitos de Recursos

**Modelo completo (bf16)**:
- **Pesos**: ~4.5 GB
- **KV cache** (8192 ctx): ~1.6 GB
- **Total mínimo**: ~6.1 GB
- **VRAM recomendada**: ≥12 GB
- **FLOPs/token**: ~4.5B

**Modelo cuantizado (Q4/GGUF)**:
- **Pesos**: ~2.7 GB
- **KV cache**: ~1.6 GB
- **Total mínimo**: ~4.3 GB
- **VRAM recomendada**: ≥8 GB
- **FLOPs/token**: ~2.2B

#### Ventajas

- ✅ **Rápido**: Latencia baja, ideal para aplicaciones en tiempo real
- ✅ **Eficiente**: Menor consumo de recursos computacionales
- ✅ **Escalable**: Permite mayor throughput en hardware limitado
- ✅ **Costo-efectivo**: Reduce costos de inferencia

#### Casos de Uso Recomendados

- Traducciones simples (oraciones cortas)
- Aplicaciones web con alta concurrencia
- Chatbots y asistentes virtuales
- Dispositivos edge con GPU limitada
- Prototipos y desarrollo

---

### salamandraTA-7b-instruct

**Ubicación**: [BSC-LT/salamandra-7b](https://huggingface.co/BSC-LT/salamandraTA-7b-instruct)

#### Especificaciones Técnicas

| Característica | Valor |
|----------------|-------|
| **Parámetros totales** | 7,768,117,248 (~7.77B) |
| **Parámetros de embedding** | 1,048,576,000 |
| **Capas** | 32 |
| **Tamaño oculto** | 4,096 |
| **Cabezales de atención** | 32 |
| **Longitud de contexto** | 8,192 tokens |
| **Tamaño del vocabulario** | 256,000 |
| **Precisión** | bfloat16 |
| **Tipo de embedding** | RoPE |
| **Función de activación** | SwiGLU |
| **Normalización de capas** | RMS Norm |
| **Grouped query attention** | ✅ Sí |
| **Flash attention** | ✅ Sí |
| **Num. query groups** | 8 |

#### Requisitos de Recursos

**Modelo completo (bf16)**:
- **Pesos**: ~15.5 GB
- **KV cache** (8192 ctx): ~4.3 GB
- **Total mínimo**: ~19.8 GB
- **VRAM recomendada**: ≥24 GB
- **FLOPs/token**: ~15.5B (3.45× más pesado que 2B)

**Modelo cuantizado (Q4/GGUF)**:
- **Pesos**: ~8.6 GB
- **KV cache**: ~5 GB
- **Total mínimo**: ~13.6 GB
- **VRAM recomendada**: ≥16 GB
- **FLOPs/token**: ~6.7B

#### Ventajas

- ✅ **Mayor calidad**: Traducciones más precisas y naturales
- ✅ **Contexto complejo**: Mejor manejo de documentos largos
- ✅ **Terminología especializada**: Ideal para dominios técnicos
- ✅ **Matices idiomáticos**: Captura mejor expresiones idiomáticas

#### Casos de Uso Recomendados

- Traducción de documentos técnicos/legales
- Contenido literario o marketing
- Textos largos (párrafos, documentos)
- Traducciones que requieren alta fidelidad
- Producción profesional

---

## Sistema de Providers

### Modelo de Datos

**Tabla**: `translation_providers`

**Ubicación del modelo**: `app/models/translation.py:10-33`

```python
class TranslationProvider(Base):
    __tablename__ = "translation_providers"

    id: int                            # Primary key
    name: str                          # Ej: "Salamandra 2B Production"
    provider_type: str                 # "huggingface" (única soportada actualmente)
    endpoint: str                      # URL del endpoint de Hugging Face
    encrypted_api_key: str             # API key encriptada con AES
    region: str | None                 # Región del endpoint (opcional)
    is_active: bool                    # Si el provider está activo
    is_default: bool                   # Si es el provider por defecto
    configuration: dict | None         # JSON con model, parameters, etc.
    input_language_ids: list[int]      # IDs de idiomas aceptados como origen
    output_language_ids: list[int]     # IDs de idiomas soportados como destino
    created_at: datetime
    updated_at: datetime
```

### Campo `configuration`

**Estructura JSON**:

```json
{
  "model": "BSC-LT/salamandra-2b",
  "parameters": {
    "max_new_tokens": 512,
    "temperature": 0.2,
    "do_sample": false,
    "chunk_chars": 800
  }
}
```

**Parámetros soportados**:

| Parámetro | Tipo | Descripción | Valor Predeterminado |
|-----------|------|-------------|---------------------|
| `model` | string | ID del modelo en Hugging Face | `"BSC-LT/salamandra-2b"` |
| `max_new_tokens` | int | Máximo de tokens a generar | `512` |
| `temperature` | float | Aleatoriedad en generación (0-1) | `0.2` |
| `do_sample` | bool | Usar muestreo vs greedy decoding | `false` |
| `chunk_chars` | int | Tamaño de chunks para textos largos | `800` |
| `top_p` | float | Nucleus sampling threshold | N/A |
| `top_k` | int | Top-K sampling | N/A |
| `repetition_penalty` | float | Penalización por repetición | N/A |

**Notas importantes**:

- `chunk_chars` no se envía al endpoint de HF, solo controla la división de texto localmente
- Parámetros no soportados se filtran automáticamente antes del request
- `do_sample=false` activa **greedy decoding** (más rápido, determinista)
- `temperature` solo aplica si `do_sample=true`

### Encriptación de API Keys

**Ubicación**: `app/core/encryption.py`

Las API keys se encriptan usando **AES-256-CBC** con la clave configurada en `settings.encryption_key`.

**Proceso**:
1. Provider creado → API key encriptada con `EncryptionService.encrypt()`
2. Almacenada en `encrypted_api_key`
3. Al usar el provider → Desencriptada con `EncryptionService.decrypt()`
4. Pasada al `HuggingFaceTranslationService`

**Seguridad**:
- Solo **superusers** y usuarios con rol **admin** pueden ver API keys desencriptadas
- La clave de encriptación debe estar en variable de entorno segura
- Nunca se expone la API key en logs o respuestas API

---

## Configuración de Providers

### Crear un Provider (POST /providers)

**Endpoint**: `POST /api/v1/translations/providers`

**Permisos**: `translations:manage`

**Request Body**:

```json
{
  "name": "Salamandra 2B - Producción",
  "provider_type": "huggingface",
  "endpoint": "https://api-inference.huggingface.co/models/BSC-LT/salamandraTA-2b-instruct",
  "api_key": "hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "region": null,
  "is_active": true,
  "is_default": true,
  "configuration": {
    "model": "BSC-LT/salamandra-2b",
    "parameters": {
      "max_new_tokens": 512,
      "do_sample": false,
      "chunk_chars": 800
    }
  },
  "input_language_ids": [1, 2, 3, 4, 5],
  "output_language_ids": [1, 2, 3, 4, 5]
}
```

**Response** (201 Created):

```json
{
  "id": 1,
  "name": "Salamandra 2B - Producción",
  "provider_type": "huggingface",
  "endpoint": "https://api-inference.huggingface.co/models/BSC-LT/salamandraTA-2b-instruct",
  "region": null,
  "api_key": "hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "is_active": true,
  "is_default": true,
  "configuration": {
    "model": "BSC-LT/salamandra-2b",
    "parameters": {
      "max_new_tokens": 512,
      "do_sample": false,
      "chunk_chars": 800
    }
  },
  "input_language_ids": [1, 2, 3, 4, 5],
  "output_language_ids": [1, 2, 3, 4, 5],
  "input_languages": [
    {"id": 1, "code": "en", "name": "English", "native_name": "English", ...},
    {"id": 2, "code": "es", "name": "Spanish", "native_name": "Español", ...},
    ...
  ],
  "output_languages": [
    {"id": 1, "code": "en", "name": "English", "native_name": "English", ...},
    ...
  ],
  "created_at": "2025-12-21T10:30:00Z",
  "updated_at": "2025-12-21T10:30:00Z"
}
```

### Ejemplo: Configurar Salamandra 2B

```bash
#!/bin/bash

API_BASE="http://localhost:8000/api/v1"
TOKEN="<tu_token_con_permisos_translations:manage>"

# 1. Obtener todos los idiomas activos
LANGUAGE_IDS=$(curl -s "$API_BASE/translations/languages?only_active=true" | jq '[.[].id]')

# 2. Crear provider para Salamandra 2B
curl -X POST "$API_BASE/translations/providers" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Salamandra 2B Fast\",
    \"provider_type\": \"huggingface\",
    \"endpoint\": \"https://api-inference.huggingface.co/models/BSC-LT/salamandraTA-2b-instruct\",
    \"api_key\": \"$HUGGINGFACE_API_KEY\",
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

### Ejemplo: Configurar Salamandra 7B

```bash
#!/bin/bash

API_BASE="http://localhost:8000/api/v1"
TOKEN="<tu_token_con_permisos_translations:manage>"

LANGUAGE_IDS=$(curl -s "$API_BASE/translations/languages?only_active=true" | jq '[.[].id]')

curl -X POST "$API_BASE/translations/providers" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Salamandra 7B Premium\",
    \"provider_type\": \"huggingface\",
    \"endpoint\": \"https://api-inference.huggingface.co/models/BSC-LT/salamandraTA-7b-instruct\",
    \"api_key\": \"$HUGGINGFACE_API_KEY\",
    \"is_active\": true,
    \"is_default\": false,
    \"configuration\": {
      \"model\": \"BSC-LT/salamandra-7b\",
      \"parameters\": {
        \"max_new_tokens\": 768,
        \"do_sample\": false,
        \"chunk_chars\": 1200
      }
    },
    \"input_language_ids\": $LANGUAGE_IDS,
    \"output_language_ids\": $LANGUAGE_IDS
  }"
```

### Actualizar un Provider (PUT /providers/{id})

**Endpoint**: `PUT /api/v1/translations/providers/1`

**Permisos**: `translations:manage`

**Request Body** (todos los campos son opcionales):

```json
{
  "name": "Salamandra 2B - Actualizado",
  "is_active": false,
  "configuration": {
    "model": "BSC-LT/salamandra-2b",
    "parameters": {
      "max_new_tokens": 1024,
      "chunk_chars": 1000
    }
  }
}
```

### Establecer Provider Predeterminado

**Endpoint**: `POST /api/v1/translations/providers/{provider_id}/default`

**Permisos**: `translations:manage`

```bash
curl -X POST "$API_BASE/translations/providers/2/default" \
  -H "Authorization: Bearer $TOKEN"
```

**Efecto**:
- El provider especificado se marca como `is_default=true`
- Todos los demás providers se marcan como `is_default=false`
- Solicitudes sin `provider_id` usarán este provider

### Desactivar un Provider

```bash
curl -X PUT "$API_BASE/translations/providers/1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```

### Eliminar un Provider

**Endpoint**: `DELETE /api/v1/translations/providers/{provider_id}`

**Permisos**: `translations:manage`

```bash
curl -X DELETE "$API_BASE/translations/providers/1" \
  -H "Authorization: Bearer $TOKEN"
```

**Nota**: Cascada → elimina también registros en `translations` que usen este provider.

---

## Selección Dinámica de Modelos

### Estrategias de Selección

#### 1. Provider Predeterminado (Recomendado)

**Uso**: No especificar `provider_id` en el request

```bash
curl -X POST "$API_BASE/translations/translate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello world",
    "source_language_code": "en",
    "target_language_code": "es"
  }'
```

**Proceso**:
1. `TranslationServiceFactory.get_service(db, provider_id=None)` → `app/services/translation_service.py:524`
2. Ejecuta `crud_translation.get_default_provider(db)` → `app/crud/translation.py:66-73`
3. Query: `SELECT * FROM translation_providers WHERE is_default=True AND is_active=True`
4. Si no hay default → Error 500: "No default translation provider configured"

**Ventajas**:
- ✅ Simplifica código cliente
- ✅ Permite cambios centralizados sin modificar clientes
- ✅ Ideal para aplicaciones con un solo modelo en producción

#### 2. Provider Específico

**Uso**: Especificar `provider_id` en el request

```bash
curl -X POST "$API_BASE/translations/translate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Este es un documento técnico muy complejo",
    "source_language_code": "es",
    "target_language_code": "en",
    "provider_id": 2
  }'
```

**Proceso**:
1. `TranslationServiceFactory.get_service(db, provider_id=2)` → `app/services/translation_service.py:516`
2. Ejecuta `crud_translation.get_provider(db, 2)` → `app/crud/translation.py:44-49`
3. Query: `SELECT * FROM translation_providers WHERE id=2`
4. Si no existe → Error 404: "Translation provider not found"
5. Si `is_active=False` → Error 400: "Translation provider is not active"

**Ventajas**:
- ✅ Control granular por request
- ✅ Permite A/B testing
- ✅ Optimización basada en características del texto

#### 3. Selección Automática Basada en Reglas (Implementación Personalizada)

**Ejemplo**: Lógica en cliente para elegir provider según longitud del texto

```python
import httpx

async def translate_with_auto_selection(text: str, source: str, target: str, token: str):
    """Selecciona automáticamente el mejor provider según longitud del texto."""

    # Regla: textos >500 chars usan modelo 7B, el resto modelo 2B
    provider_id = 2 if len(text) > 500 else 1

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/translations/translate",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "text": text,
                "source_language_code": source,
                "target_language_code": target,
                "provider_id": provider_id
            }
        )
        response.raise_for_status()
        return response.json()

# Uso
result = await translate_with_auto_selection(
    text="Short text",
    source="en",
    target="es",
    token="your_token"
)
print(result["translated_text"])
```

#### 4. Round-Robin / Load Balancing (Implementación Personalizada)

**Ejemplo**: Distribuir carga entre múltiples providers

```python
import itertools
import httpx

class LoadBalancedTranslator:
    def __init__(self, provider_ids: list[int], token: str):
        self.provider_cycle = itertools.cycle(provider_ids)
        self.token = token
        self.base_url = "http://localhost:8000/api/v1/translations/translate"

    async def translate(self, text: str, source: str, target: str):
        provider_id = next(self.provider_cycle)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "text": text,
                    "source_language_code": source,
                    "target_language_code": target,
                    "provider_id": provider_id
                }
            )
            response.raise_for_status()
            return response.json()

# Uso: distribuir entre 3 providers
translator = LoadBalancedTranslator(provider_ids=[1, 2, 3], token="your_token")

for i in range(10):
    result = await translator.translate(f"Text {i}", "en", "es")
    print(f"Traducción {i}: {result['translated_text']}")
```

### Validaciones del Sistema

**En `TranslationServiceFactory.get_service()`** (`app/services/translation_service.py:500-559`):

```python
# 1. Provider existe
if not provider:
    raise HTTPException(404, "Translation provider not found")

# 2. Provider está activo
if not provider.is_active:
    raise HTTPException(400, "Translation provider is not active")

# 3. Provider es de tipo Hugging Face
if provider.provider_type != "huggingface":
    raise HTTPException(400, "Only Hugging Face translation provider is supported")

# 4. Provider tiene endpoint configurado
if not provider.endpoint:
    raise HTTPException(500, "Hugging Face provider requires an endpoint URL")

# 5. API key se puede desencriptar
api_key = await crud_translation.get_decrypted_api_key(db, provider.id)
```

---

## API Endpoints

### Gestión de Providers

#### Listar Providers

**GET** `/api/v1/translations/providers`

**Permisos**: `translations:read` o `translations:translate`

**Query Params**:
- `skip` (int, default=0): Número de registros a saltar
- `limit` (int, default=100, max=100): Máximo de registros a retornar

**Response**:

```json
[
  {
    "id": 1,
    "name": "Salamandra 2B Fast",
    "provider_type": "huggingface",
    "endpoint": "https://api-inference.huggingface.co/models/BSC-LT/salamandraTA-2b-instruct",
    "region": null,
    "api_key": "hf_xxxx...",  // Solo visible para superusers/admin
    "is_active": true,
    "is_default": true,
    "configuration": {...},
    "input_language_ids": [1, 2, 3],
    "output_language_ids": [1, 2, 3],
    "input_languages": [...],
    "output_languages": [...],
    "created_at": "2025-12-21T10:00:00Z",
    "updated_at": "2025-12-21T10:00:00Z"
  },
  {
    "id": 2,
    "name": "Salamandra 7B Premium",
    "is_default": false,
    ...
  }
]
```

#### Obtener Provider por ID

**GET** `/api/v1/translations/providers/{provider_id}`

**Permisos**: `translations:read` o `translations:translate`

**Response**: Mismo formato que elemento individual en lista

#### Crear Provider

**POST** `/api/v1/translations/providers`

**Permisos**: `translations:manage`

**Request**: Ver [Configuración de Providers](#configuración-de-providers)

#### Actualizar Provider

**PUT** `/api/v1/translations/providers/{provider_id}`

**Permisos**: `translations:manage`

**Request**: Campos opcionales de `TranslationProviderUpdate`

#### Eliminar Provider

**DELETE** `/api/v1/translations/providers/{provider_id}`

**Permisos**: `translations:manage`

**Response**: 204 No Content

#### Establecer Provider Predeterminado

**POST** `/api/v1/translations/providers/{provider_id}/default`

**Permisos**: `translations:manage`

**Response**: Provider actualizado con `is_default=true`

### Traducción con Selección de Modelo

#### Traducir (Standard)

**POST** `/api/v1/translations/translate`

**Permisos**: `translations:translate`

**Request**:

```json
{
  "text": "Hello, how are you?",
  "source_language_code": "en",
  "target_language_code": "es",
  "provider_id": 2  // Opcional: usa default si se omite
}
```

**Response**:

```json
{
  "translated_text": "Hola, ¿cómo estás?",
  "source_language": {
    "id": 1,
    "code": "en",
    "name": "English",
    "native_name": "English",
    "is_active": true,
    "sort_order": 0,
    "created_at": "2025-12-20T00:00:00Z",
    "updated_at": "2025-12-20T00:00:00Z"
  },
  "target_language": {
    "id": 2,
    "code": "es",
    "name": "Spanish",
    "native_name": "Español",
    ...
  },
  "character_count": 19,
  "created_at": "2025-12-21T12:00:00Z"
}
```

#### Traducir (Streaming)

**POST** `/api/v1/translations/translate/stream`

**Permisos**: `translations:translate`

**Request**: Mismo formato que traducción standard

**Response**: `StreamingResponse` con tokens generados en tiempo real

**Ejemplo de consumo (Python)**:

```python
import httpx

async def translate_stream(text: str, source: str, target: str, provider_id: int | None = None):
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            "http://localhost:8000/api/v1/translations/translate/stream",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "text": text,
                "source_language_code": source,
                "target_language_code": target,
                "provider_id": provider_id
            }
        ) as response:
            response.raise_for_status()
            async for chunk in response.aiter_text():
                print(chunk, end="", flush=True)
            print()  # Nueva línea al final

# Uso con provider específico
await translate_stream(
    text="This is a long document that needs translation...",
    source="en",
    target="es",
    provider_id=2  # Usar Salamandra 7B
)
```

---

## Ejemplos de Uso

### Caso 1: Testing de Calidad - Comparar Modelos

**Objetivo**: Comparar la calidad de traducción entre Salamandra 2B y 7B

```python
import httpx
import asyncio

async def compare_models(text: str, source: str, target: str, token: str):
    """Compara resultados de traducción entre diferentes modelos."""

    providers = {
        "Salamandra 2B": 1,
        "Salamandra 7B": 2
    }

    results = {}

    async with httpx.AsyncClient() as client:
        for name, provider_id in providers.items():
            print(f"\n🔄 Traduciendo con {name}...")

            response = await client.post(
                "http://localhost:8000/api/v1/translations/translate",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "text": text,
                    "source_language_code": source,
                    "target_language_code": target,
                    "provider_id": provider_id
                }
            )

            if response.status_code == 200:
                data = response.json()
                results[name] = data["translated_text"]
                print(f"✅ {name}: {data['translated_text']}")
            else:
                print(f"❌ {name}: Error {response.status_code}")

    return results

# Uso
text_original = "The quick brown fox jumps over the lazy dog"
resultados = await compare_models(text_original, "en", "es", "your_token")

print("\n📊 COMPARACIÓN:")
print(f"Original: {text_original}")
for modelo, traduccion in resultados.items():
    print(f"{modelo}: {traduccion}")
```

### Caso 2: Optimización de Costos - Modelo según Longitud

**Objetivo**: Usar modelo ligero para textos cortos, modelo premium para textos largos

```python
import httpx

class CostOptimizedTranslator:
    """Traductor que optimiza costos seleccionando modelo según longitud."""

    def __init__(self, token: str, light_provider_id: int, premium_provider_id: int, threshold: int = 500):
        self.token = token
        self.light_provider_id = light_provider_id
        self.premium_provider_id = premium_provider_id
        self.threshold = threshold
        self.base_url = "http://localhost:8000/api/v1/translations/translate"

    async def translate(self, text: str, source: str, target: str):
        # Selección automática
        provider_id = self.premium_provider_id if len(text) > self.threshold else self.light_provider_id
        model_type = "Premium (7B)" if len(text) > self.threshold else "Light (2B)"

        print(f"📝 Longitud: {len(text)} chars → Usando modelo {model_type}")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "text": text,
                    "source_language_code": source,
                    "target_language_code": target,
                    "provider_id": provider_id
                },
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()

# Uso
translator = CostOptimizedTranslator(
    token="your_token",
    light_provider_id=1,   # Salamandra 2B
    premium_provider_id=2, # Salamandra 7B
    threshold=500
)

# Texto corto → usará Salamandra 2B
short_result = await translator.translate(
    text="Hello world",
    source="en",
    target="es"
)

# Texto largo → usará Salamandra 7B
long_text = """
In the realm of artificial intelligence and machine learning,
the development of large language models has revolutionized
natural language processing tasks...
""" * 5

long_result = await translator.translate(
    text=long_text,
    source="en",
    target="es"
)
```

### Caso 3: Failover Automático

**Objetivo**: Intentar con provider principal, cambiar a backup si falla

```python
import httpx
from typing import Optional

class FailoverTranslator:
    """Traductor con failover automático a provider de respaldo."""

    def __init__(self, token: str, primary_provider_id: int, fallback_provider_id: int):
        self.token = token
        self.primary_provider_id = primary_provider_id
        self.fallback_provider_id = fallback_provider_id
        self.base_url = "http://localhost:8000/api/v1/translations/translate"

    async def translate(self, text: str, source: str, target: str) -> dict:
        # Intentar con provider principal
        try:
            print(f"🔄 Intentando con provider principal (ID={self.primary_provider_id})...")
            result = await self._translate_with_provider(text, source, target, self.primary_provider_id)
            print("✅ Traducción exitosa con provider principal")
            return result
        except Exception as e:
            print(f"⚠️ Provider principal falló: {e}")
            print(f"🔄 Cambiando a provider de respaldo (ID={self.fallback_provider_id})...")

            try:
                result = await self._translate_with_provider(text, source, target, self.fallback_provider_id)
                print("✅ Traducción exitosa con provider de respaldo")
                return result
            except Exception as e2:
                print(f"❌ Provider de respaldo también falló: {e2}")
                raise

    async def _translate_with_provider(self, text: str, source: str, target: str, provider_id: int) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "text": text,
                    "source_language_code": source,
                    "target_language_code": target,
                    "provider_id": provider_id
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

# Uso
translator = FailoverTranslator(
    token="your_token",
    primary_provider_id=2,   # Salamandra 7B (principal)
    fallback_provider_id=1   # Salamandra 2B (respaldo)
)

result = await translator.translate("Hello world", "en", "es")
print(f"Traducción final: {result['translated_text']}")
```

### Caso 4: Batch Translation con Diferentes Modelos

**Objetivo**: Procesar lote de traducciones usando el modelo óptimo para cada una

```python
import httpx
import asyncio
from typing import List, Dict

class BatchTranslator:
    """Procesador de lotes con selección inteligente de modelo."""

    def __init__(self, token: str):
        self.token = token
        self.base_url = "http://localhost:8000/api/v1/translations/translate"

    def select_provider(self, text: str) -> int:
        """Lógica de selección de provider."""
        # Ejemplo: textos técnicos (con muchos números) usan 7B
        if any(char.isdigit() for char in text):
            return 2  # Salamandra 7B
        # Textos normales usan 2B
        return 1  # Salamandra 2B

    async def translate_batch(
        self,
        items: List[Dict[str, str]]  # [{"text": "...", "source": "en", "target": "es"}, ...]
    ) -> List[dict]:
        """Traduce un lote de textos en paralelo."""

        async with httpx.AsyncClient() as client:
            tasks = []

            for item in items:
                provider_id = self.select_provider(item["text"])

                task = client.post(
                    self.base_url,
                    headers={"Authorization": f"Bearer {self.token}"},
                    json={
                        "text": item["text"],
                        "source_language_code": item["source"],
                        "target_language_code": item["target"],
                        "provider_id": provider_id
                    },
                    timeout=60.0
                )
                tasks.append(task)

            # Ejecutar todas las traducciones en paralelo
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            results = []
            for i, response in enumerate(responses):
                if isinstance(response, Exception):
                    results.append({
                        "original": items[i]["text"],
                        "translated": None,
                        "error": str(response)
                    })
                else:
                    data = response.json()
                    results.append({
                        "original": items[i]["text"],
                        "translated": data["translated_text"],
                        "error": None
                    })

            return results

# Uso
translator = BatchTranslator(token="your_token")

batch = [
    {"text": "Hello world", "source": "en", "target": "es"},
    {"text": "The temperature is 25.5°C", "source": "en", "target": "es"},
    {"text": "Good morning", "source": "en", "target": "fr"},
    {"text": "Invoice #12345", "source": "en", "target": "de"}
]

results = await translator.translate_batch(batch)

for i, result in enumerate(results):
    if result["error"]:
        print(f"{i+1}. ❌ Error: {result['error']}")
    else:
        print(f"{i+1}. ✅ {result['original']} → {result['translated']}")
```

---

## Gestión de Idiomas

### Modelo de Datos

**Tabla**: `languages`

**Ubicación del modelo**: `app/models/translation.py:36-63`

```python
class Language(Base):
    __tablename__ = "languages"

    id: int
    code: str              # Código ISO 639-1 (ej: "en", "es", "ca")
    name: str              # Nombre en inglés (ej: "Spanish")
    native_name: str       # Nombre nativo (ej: "Español")
    is_active: bool        # Si el idioma está habilitado
    sort_order: int        # Orden de visualización
    created_at: datetime
    updated_at: datetime
```

### Endpoints de Gestión

#### Listar Idiomas

**GET** `/api/v1/translations/languages`

**Permisos**: Público (sin autenticación)

**Query Params**:
- `only_active` (bool, default=true): Mostrar solo idiomas activos
- `skip` (int, default=0)
- `limit` (int, default=100)

**Response**:

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
    ...
  }
]
```

#### Crear Idioma

**POST** `/api/v1/translations/languages`

**Permisos**: `translations:manage`

**Request**:

```json
{
  "code": "eu",
  "name": "Basque",
  "native_name": "Euskara",
  "sort_order": 10
}
```

#### Activar/Desactivar Idioma

**PATCH** `/api/v1/translations/languages/{language_id}/toggle?is_active=true`

**Permisos**: `translations:manage`

### Relación Provider-Idiomas

Cada provider puede tener restricciones sobre qué idiomas acepta como entrada y salida:

```json
{
  "input_language_ids": [1, 2, 3],    // Acepta en, es, ca como origen
  "output_language_ids": [1, 2, 4, 5] // Soporta en, es, fr, de como destino
}
```

**Validación en Endpoints**:

```python
# app/api/translations.py:284-298

# 1. Validar idioma de origen existe y está activo
source_lang = await crud_translation.get_language_by_code(db, request.source_language_code)
if not source_lang or not source_lang.is_active:
    raise HTTPException(400, f"Source language '{request.source_language_code}' not available")

# 2. Validar idioma de destino existe y está activo
target_lang = await crud_translation.get_language_by_code(db, request.target_language_code)
if not target_lang or not target_lang.is_active:
    raise HTTPException(400, f"Target language '{request.target_language_code}' not available")
```

**Nota**: Actualmente el sistema valida que los idiomas existan y estén activos, pero NO valida que el provider seleccionado soporte esos idiomas específicos. Esto es una mejora futura recomendada.

---

## Mejores Prácticas

### 1. Configuración de Providers

#### ✅ Recomendaciones

**Nombres descriptivos**:
```json
{
  "name": "Salamandra 2B - Producción EU-West"
}
```
No:
```json
{
  "name": "Provider 1"
}
```

**Siempre especificar configuración explícita**:
```json
{
  "configuration": {
    "model": "BSC-LT/salamandra-2b",
    "parameters": {
      "max_new_tokens": 512,
      "do_sample": false,
      "chunk_chars": 800
    }
  }
}
```

**Mantener un solo provider como default**:
- Solo un provider debe tener `is_default=true`
- El sistema lo garantiza automáticamente al crear/actualizar

**Usar `is_active` para mantenimiento**:
```bash
# Desactivar temporalmente sin eliminar
curl -X PUT "$API_BASE/translations/providers/1" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"is_active": false}'
```

### 2. Selección de Modelos

#### Matriz de Decisión

| Característica del Texto | Modelo Recomendado | Razón |
|---------------------------|-------------------|-------|
| Longitud < 100 caracteres | Salamandra 2B | Velocidad, bajo costo |
| Longitud 100-500 caracteres | Salamandra 2B | Balance óptimo |
| Longitud > 500 caracteres | Salamandra 7B | Mejor coherencia en contextos largos |
| Texto técnico/legal | Salamandra 7B | Mayor precisión terminológica |
| Chat en tiempo real | Salamandra 2B | Latencia mínima |
| Traducción literaria | Salamandra 7B | Preservación de matices |
| Alta concurrencia | Salamandra 2B | Mayor throughput |
| Producción crítica | Salamandra 7B | Mayor calidad garantizada |

### 3. Gestión de Configuración

#### Parámetros Recomendados por Caso de Uso

**Traducción Rápida (Chat, UI)**:
```json
{
  "model": "BSC-LT/salamandra-2b",
  "parameters": {
    "max_new_tokens": 256,
    "do_sample": false,
    "chunk_chars": 500
  }
}
```

**Traducción Balanceada (General)**:
```json
{
  "model": "BSC-LT/salamandra-2b",
  "parameters": {
    "max_new_tokens": 512,
    "do_sample": false,
    "chunk_chars": 800
  }
}
```

**Traducción Premium (Documentos)**:
```json
{
  "model": "BSC-LT/salamandra-7b",
  "parameters": {
    "max_new_tokens": 1024,
    "do_sample": false,
    "chunk_chars": 1200
  }
}
```

**Traducción Creativa (Marketing)**:
```json
{
  "model": "BSC-LT/salamandra-7b",
  "parameters": {
    "max_new_tokens": 768,
    "do_sample": true,
    "temperature": 0.3,
    "chunk_chars": 1000
  }
}
```

### 4. Seguridad

#### ✅ Recomendaciones

**Protección de API Keys**:
- Nunca commitear API keys en código
- Usar variables de entorno
- Rotar keys periódicamente
- Auditar acceso a endpoints de providers

**Control de Acceso**:
```python
# Solo superusers/admin pueden ver API keys
# app/api/translations.py:72-76

def _resolve_api_key(provider: TranslationProvider, current_user: User) -> str | None:
    if not (current_user.is_superuser or current_user.has_role("admin")):
        return None
    return _decrypt_provider_api_key(provider)
```

**Auditoría**:
```sql
-- Consultar quién está usando qué providers
SELECT
    u.username,
    tp.name AS provider,
    COUNT(*) AS translations,
    SUM(t.character_count) AS total_chars
FROM translations t
JOIN users u ON t.user_id = u.id
JOIN translation_providers tp ON t.provider_id = tp.id
WHERE t.created_at > NOW() - INTERVAL '7 days'
GROUP BY u.username, tp.name
ORDER BY total_chars DESC;
```

### 5. Monitoreo y Optimización

#### Métricas a Rastrear

```sql
-- 1. Uso por provider
SELECT
    tp.name,
    COUNT(*) AS total_translations,
    AVG(t.character_count) AS avg_chars,
    MAX(t.created_at) AS last_used
FROM translation_providers tp
LEFT JOIN translations t ON tp.id = t.provider_id
GROUP BY tp.id, tp.name
ORDER BY total_translations DESC;

-- 2. Idiomas más traducidos
SELECT
    sl.code AS source,
    tl.code AS target,
    COUNT(*) AS count
FROM translations t
JOIN languages sl ON t.source_language_id = sl.id
JOIN languages tl ON t.target_language_id = tl.id
GROUP BY sl.code, tl.code
ORDER BY count DESC
LIMIT 10;

-- 3. Volumen de caracteres por usuario
SELECT
    u.username,
    SUM(t.character_count) AS total_chars,
    COUNT(*) AS num_translations
FROM translations t
JOIN users u ON t.user_id = u.id
WHERE t.created_at > NOW() - INTERVAL '30 days'
GROUP BY u.username
ORDER BY total_chars DESC;
```

---

## Troubleshooting

### Problema 1: "No default translation provider configured"

**Error**:
```json
{
  "detail": "No default translation provider configured"
}
```

**Causa**: No hay ningún provider con `is_default=true` y `is_active=true`

**Solución**:

```bash
# Verificar providers
curl "$API_BASE/translations/providers" \
  -H "Authorization: Bearer $TOKEN"

# Establecer un provider como default
curl -X POST "$API_BASE/translations/providers/1/default" \
  -H "Authorization: Bearer $TOKEN"
```

### Problema 2: "Translation provider not found"

**Error**:
```json
{
  "detail": "Translation provider not found"
}
```

**Causa**: El `provider_id` especificado no existe

**Solución**:

```bash
# Listar providers disponibles
curl "$API_BASE/translations/providers" \
  -H "Authorization: Bearer $TOKEN" | jq '.[].id'

# Usar un ID válido o omitir provider_id para usar el default
```

### Problema 3: "Translation provider is not active"

**Error**:
```json
{
  "detail": "Translation provider is not active"
}
```

**Causa**: El provider existe pero está desactivado (`is_active=false`)

**Solución**:

```bash
# Activar el provider
curl -X PUT "$API_BASE/translations/providers/1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_active": true}'
```

### Problema 4: "Source language 'xx' not available"

**Error**:
```json
{
  "detail": "Source language 'en' not available"
}
```

**Causa**: El código de idioma no existe o está desactivado

**Solución**:

```bash
# Listar idiomas activos
curl "$API_BASE/translations/languages?only_active=true"

# Activar el idioma si existe
curl -X PATCH "$API_BASE/translations/languages/1/toggle?is_active=true" \
  -H "Authorization: Bearer $TOKEN"

# Crear el idioma si no existe
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

### Problema 5: "Failed to decrypt provider API key"

**Error**:
```json
{
  "detail": "Failed to decrypt provider API key"
}
```

**Causa**: La clave de encriptación cambió o está corrupta

**Solución**:

1. **Verificar variable de entorno**:
```bash
echo $ENCRYPTION_KEY
```

2. **Recrear el provider** si la clave cambió:
```bash
# Eliminar provider existente
curl -X DELETE "$API_BASE/translations/providers/1" \
  -H "Authorization: Bearer $TOKEN"

# Crear nuevo con API key válida
curl -X POST "$API_BASE/translations/providers" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Salamandra 2B",
    "provider_type": "huggingface",
    "endpoint": "https://...",
    "api_key": "hf_xxxxxxxxxxxx",
    ...
  }'
```

### Problema 6: "Only Hugging Face translation provider is supported"

**Error**:
```json
{
  "detail": "Only Hugging Face translation provider is supported"
}
```

**Causa**: El provider tiene `provider_type` diferente a `"huggingface"`

**Solución**:

Actualmente solo se soporta Hugging Face. Verificar que el provider esté configurado correctamente:

```bash
curl "$API_BASE/translations/providers/1" \
  -H "Authorization: Bearer $TOKEN" | jq '.provider_type'

# Debe retornar: "huggingface"
```

### Problema 7: Respuesta vacía o con metadata

**Síntoma**: La traducción contiene marcadores como `"Output:"` o `"[es]"`

**Causa**: El modelo está generando metadata que no se limpió correctamente

**Solución**:

El sistema tiene limpieza automática en `_clean_output()` (`app/services/translation_service.py:94-157`).

Si persiste, ajustar parámetros:

```json
{
  "configuration": {
    "model": "BSC-LT/salamandra-2b",
    "parameters": {
      "max_new_tokens": 512,
      "do_sample": false,
      "temperature": 0.0  // Más determinista
    }
  }
}
```

### Problema 8: Timeout en traducciones largas

**Error**: Request timeout

**Causa**: Textos muy largos exceden el timeout del cliente

**Solución**:

**Opción 1**: Usar endpoint streaming

```python
async with httpx.AsyncClient(timeout=120.0) as client:
    async with client.stream(
        "POST",
        f"{API_BASE}/translations/translate/stream",
        ...
    ) as response:
        async for chunk in response.aiter_text():
            print(chunk, end="")
```

**Opción 2**: Dividir el texto en chunks manualmente

```python
def split_text(text: str, max_chars: int = 1000) -> list[str]:
    """Divide texto en chunks preservando párrafos."""
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) > max_chars:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = para
        else:
            current_chunk += "\n\n" + para if current_chunk else para

    if current_chunk:
        chunks.append(current_chunk)

    return chunks

# Uso
chunks = split_text(long_text)
translations = []

for chunk in chunks:
    result = await translate(chunk, "en", "es")
    translations.append(result["translated_text"])

final_translation = "\n\n".join(translations)
```

---

## Referencias

### Archivos del Código Fuente

| Archivo | Descripción | Líneas Clave |
|---------|-------------|--------------|
| `app/models/translation.py` | Modelos de datos (Provider, Language, Translation) | 10-88 |
| `app/schemas/translation.py` | Esquemas Pydantic para validación | 12-270 |
| `app/crud/translation.py` | Operaciones CRUD para providers y idiomas | 1-228 |
| `app/api/translations.py` | Endpoints REST API | 112-492 |
| `app/services/translation_service.py` | Servicio de traducción y factory | 21-560 |
| `app/core/encryption.py` | Encriptación de API keys | - |

### Modelos Hugging Face

- **Salamandra 2B**: https://huggingface.co/BSC-LT/salamandraTA-2b-instruct
- **Salamandra 7B**: https://huggingface.co/BSC-LT/salamandraTA-7b-instruct
- **Salamandra 2B GGUF** (cuantizado): https://huggingface.co/BSC-LT/salamandraTA-2B-instruct-GGUF
- **Salamandra 7B GGUF** (cuantizado): https://huggingface.co/BSC-LT/salamandraTA-7B-instruct-GGUF

### Documentación Relacionada

- **Guía de uso de modelos SalamandraTA**: `DOCUMENTATION.md`
- **Servicios de traducción**: `docs/SERVICIOS_TRADUCCION.md`
- **Gestión de usuarios y autenticación**: `docs/LOGIN_Y_GESTION_USUARIOS.md`
- **Gestión de usuarios (Admin)**: `docs/GESTION_USUARIOS_ADMIN.md`

---

**Documento generado**: 2025-12-21

**Autor**: Claude Sonnet 4.5 (Anthropic)

**Versión del sistema**: core_bsctranslation v1.0
