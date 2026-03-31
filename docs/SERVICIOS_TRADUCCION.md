# Implementación de Servicios de Traducción + Grammar Checker + Post-Editing

## Índice
1. [Descripción General](#descripción-general)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Servicio de Traducción](#servicio-de-traducción)
4. [Servicio de Grammar Checker](#servicio-de-grammar-checker)
5. [Servicio de Post-Editing](#servicio-de-post-editing)
6. [Configuración de Providers](#configuración-de-providers)
7. [Endpoints de API](#endpoints-de-api)
8. [Idiomas Soportados](#idiomas-soportados)
9. [Ejemplos de Uso](#ejemplos-de-uso)
10. [Optimizaciones y Parámetros](#optimizaciones-y-parámetros)
11. [Manejo de Errores](#manejo-de-errores)
12. [Buenas Prácticas](#buenas-prácticas)

---

## Descripción General

El módulo de traducción proporciona tres servicios principales para procesamiento de texto mediante **Hugging Face Inference Endpoints**:

### Servicios Disponibles

| Servicio | Descripción | Uso Principal |
|----------|-------------|---------------|
| **Translation Service** | Traduce texto entre idiomas | Traducción automática multiidioma |
| **Grammar Checker** | Revisa gramática y ortografía | Corrección de errores gramaticales |
| **Post-Editing** | Mejora y reescribe texto | Refinamiento de traducciones y textos |

### Características Clave

✅ **Streaming en tiempo real** - Respuesta progresiva para mejor UX
✅ **Chunking inteligente** - Procesa textos largos preservando párrafos
✅ **Múltiples idiomas** - Soporte para 27+ idiomas
✅ **Reglas gramaticales** - Correcciones basadas en reglas para español
✅ **Personalización** - Parámetros ajustables por provider
✅ **Historial** - Registro completo de traducciones
✅ **Encriptación** - API keys encriptadas en BD

---

## Arquitectura del Sistema

### Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────┐
│                    API Endpoints                        │
│  /translate, /grammar-check, /post-edit               │
└───────────────────┬─────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────┐
│              Service Factories                          │
│  TranslationServiceFactory                             │
│  GrammarServiceFactory                                 │
│  PostEditingServiceFactory                             │
└───────────────────┬─────────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
┌───────▼──────┐ ┌──▼──────┐ ┌─▼─────────────┐
│ Translation  │ │ Grammar │ │ Post-Editing  │
│   Service    │ │ Service │ │   Service     │
└───────┬──────┘ └──┬──────┘ └─┬─────────────┘
        │           │           │
        └───────────┼───────────┘
                    │
┌───────────────────▼─────────────────────────────────────┐
│          Hugging Face InferenceClient                   │
│            (text_generation API)                        │
└─────────────────────────────────────────────────────────┘
```

### Flujo de Datos

```
1. Usuario envía solicitud → API Endpoint
2. Endpoint valida idioma y permisos
3. Factory crea instancia del servicio
4. Servicio divide texto en chunks
5. Para cada chunk:
   a. Construye prompt optimizado
   b. Llama a Hugging Face API
   c. Limpia respuesta
   d. Retorna/stream resultado
6. Guarda en historial (si corresponde)
7. Retorna respuesta al usuario
```

---

## Servicio de Traducción

**Ubicación:** [`app/services/translation_service.py`](app/services/translation_service.py)

### Clase Principal

```python
class HuggingFaceTranslationService:
    def __init__(
        self,
        api_key: str,
        endpoint: str,
        model: str | None = None,
        parameters: dict[str, Any] | None = None
    )
```

### Métodos Principales

#### 1. `translate()` - Traducción Estándar

**Ubicación:** [`app/services/translation_service.py:141-239`](app/services/translation_service.py#L141-L239)

```python
async def translate(
    self,
    text: str,
    source_language: str,
    target_language: str
) -> str
```

**Proceso:**

```
1. Mapear códigos ISO a nombres completos
   ├─ "es" → "Spanish"
   ├─ "en" → "English"
   └─ "ca" → "Catalan"

2. Dividir texto en chunks (800 caracteres por defecto)
   ├─ Preservar límites de párrafos
   └─ Dividir en puntos de espacio

3. Para cada chunk:
   ├─ Construir prompt específico
   ├─ Calcular max_new_tokens dinámicamente
   ├─ Llamar a HuggingFace (en thread para no bloquear)
   └─ Limpiar respuesta

4. Combinar chunks con separadores de párrafo

5. Retornar traducción completa
```

**Ejemplo de Prompt:**

```
Translate the following text from English to Spanish.
Return ONLY the translated text. Do not include labels, tags, explanations,
or any other content. Just the translation.

Text: Hello, how are you today?

Spanish translation:
```

#### 2. `translate_stream()` - Traducción en Streaming

**Ubicación:** [`app/services/translation_service.py:280-430`](app/services/translation_service.py#L280-L430)

```python
async def translate_stream(
    self,
    text: str,
    source_language: str,
    target_language: str
) -> AsyncGenerator[str, None]
```

**Ventajas del Streaming:**
- ⚡ Respuesta más rápida (primeros tokens en < 1s)
- 📊 Mejor experiencia de usuario (progreso visible)
- 🔄 Procesamiento incremental de chunks
- 🛡️ Fallback automático si streaming falla

**Flujo de Streaming:**

```
1. Dividir texto en chunks pequeños (800 chars)

2. Para cada chunk:
   ├─ Iniciar streaming de tokens
   ├─ Acumular texto para detectar stop words
   ├─ Filtrar tokens basura con _clean_output()
   ├─ Yield tokens limpios al cliente
   └─ Si falla: intentar sin streaming

3. Separar chunks con "\n\n"

4. Cliente recibe tokens progresivamente
```

#### 3. `_clean_output()` - Limpieza de Respuestas

**Ubicación:** [`app/services/translation_service.py:44-106`](app/services/translation_service.py#L44-L106)

```python
@staticmethod
def _clean_output(text: str) -> str
```

**Limpieza Realizada:**

```python
# 1. Remover marcadores
markers = (
    "<START_OF_TRANSLATION>",
    "</START_OF_TRANSLATION>",
    "START_OF_TRANSLATION",
    "```"
)

# 2. Filtrar líneas con metadata
labels_to_skip = [
    'output:', 'translation:', 'tags:',
    'translate from', 'using our',
    '[en]', '[es]', 'is a', 'language that'
]

# 3. Truncar en separadores
separators = ['Output:', 'Tags:', 'Translate from']

# 4. Detectar y remover descripciones de idiomas
# "Hello! English is a West Germanic language..."
# → Solo "Hello!"
```

#### 4. `_chunk_text()` - División Inteligente

**Ubicación:** [`app/services/translation_service.py:118-140`](app/services/translation_service.py#L118-L140)

```python
def _chunk_text(self, text: str) -> list[str]
```

**Algoritmo:**

```
1. Dividir por párrafos ("\n\n")

2. Para cada párrafo:
   ├─ Si < chunk_chars → agregar completo
   └─ Si > chunk_chars:
      ├─ Buscar último espacio antes del límite
      ├─ Dividir ahí
      └─ Repetir con el resto

3. Preservar párrafos vacíos (separadores visuales)

4. Retornar lista de chunks
```

**Ejemplo:**

```python
text = "Paragraph 1 with lots of text...\n\nParagraph 2\n\nParagraph 3..."
chunks = [
    "Paragraph 1 with lots",
    "of text...",
    "",  # separador preservado
    "Paragraph 2",
    "",
    "Paragraph 3..."
]
```

### Parámetros de Optimización

**Ubicación:** [`app/services/translation_service.py:27-34`](app/services/translation_service.py#L27-L34)

```python
self.parameters = {
    "max_new_tokens": 512,        # Límite de tokens generados
    "do_sample": False,           # Greedy decoding (más rápido)
    "return_full_text": False,    # Solo texto nuevo
}
self.chunk_chars = 800            # Tamaño de chunk
```

**Ajustes Dinámicos:**

```python
# max_new_tokens se calcula dinámicamente:
max_new = max(10, min(512, int(len(chunk) * 1.5) + 20))

# Multiplicador 1.5x porque traducciones
# suelen ser similares en longitud
```

---

## Servicio de Grammar Checker

**Ubicación:** [`app/services/grammar_service.py`](app/services/grammar_service.py)

### Clase Principal

```python
class HuggingFaceGrammarService:
    def __init__(
        self,
        api_key: str,
        endpoint: str,
        model: str | None = None,
        parameters: dict[str, Any] | None = None
    )
```

### Estrategia Dual: Reglas + IA

```
┌─────────────────────────────────────┐
│   1. Correcciones Basadas en Reglas│
│      (Solo para Español)            │
│   - Rápidas y confiables            │
│   - 50+ reglas gramaticales         │
└──────────────┬──────────────────────┘
               │
               ▼
       ¿Encontró errores?
               │
       ┌───────┴────────┐
      Sí                No
       │                 │
       │                 ▼
       │    ┌────────────────────────┐
       │    │ 2. Verificación con IA │
       │    │    (Hugging Face)      │
       │    │ - Más exhaustivo        │
       │    │ - Todos los idiomas     │
       │    └────────────────────────┘
       │                 │
       └────────┬────────┘
                ▼
        Retornar correcciones
```

### Reglas Gramaticales (Español)

**Ubicación:** [`app/services/grammar_service.py:17-53`](app/services/grammar_service.py#L17-L53)

#### Categorías de Reglas

**1. Conjugación Verbal**

```python
# Errores con "yo"
(r'\byo fue\b', 'yo fui', 'Verb conjugation: "yo fui" (preterite)'),
(r'\byo esta\b', 'yo estoy', 'Verb conjugation: "yo estoy"'),
(r'\byo tiene\b', 'yo tengo', 'Verb conjugation: "yo tengo"'),
(r'\byo hace\b', 'yo hago', 'Verb conjugation: "yo hago"'),
```

**2. Concordancia Sujeto-Verbo**

```python
(r'\bel equipo estaban\b', 'el equipo estaba', 'Subject-verb agreement'),
(r'\bla empresa tienen\b', 'la empresa tiene', 'Subject-verb agreement'),
(r'\blos requerimientos cambia\b', 'los requerimientos cambian', 'Plural subject'),
(r'\bnadie saben\b', 'nadie sabe', '"nadie" is singular'),
```

**3. Ortografía Común**

```python
(r'\b[Oo]la\b', lambda m: 'Hola' if m.group(0)[0].isupper() else 'hola',
 'Spelling: "hola" requires "h"'),
(r'\bhaci\b', 'así', 'Spelling: "así" with accent'),
(r'\btanbien\b', 'también', 'Spelling: "también"'),
```

**4. Acentos Faltantes (Contextuales)**

```python
# "esta" vs "está" (contexto: verbo + participio/gerundio)
(r'\besta\s+(terminado|haciendo|trabajando)\b',
 lambda m: f'está {m.group(1)}', 'Missing accent on "está"'),

# "sabia" vs "sabía" (contexto: verbo + complemento)
(r'\bsabia\s+(que|como|cuando|donde)\b',
 lambda m: f'sabía {m.group(1)}', 'Missing accent on "sabía"'),

# "mas" vs "más" (contexto: comparativo)
(r'\bmas\s+(importante|grande|pequeno)\b',
 lambda m: f'más {m.group(1)}', 'Missing accent on "más"'),
```

### Método Principal

#### `check_grammar()` - Verificación Gramatical

**Ubicación:** [`app/services/grammar_service.py:312-424`](app/services/grammar_service.py#L312-L424)

```python
async def check_grammar(
    self,
    text: str,
    language: str
) -> tuple[str, list[GrammarSuggestion], bool]
```

**Retorna:**
- `corrected_text`: Texto corregido
- `suggestions`: Lista de sugerencias con detalles
- `has_errors`: Boolean indicando si se encontraron errores

**Proceso:**

```
1. Aplicar reglas basadas en regex (si es español)
   ├─ Recopilar todas las coincidencias
   ├─ Ordenar por posición
   ├─ Aplicar correcciones preservando capitalización
   └─ Generar sugerencias con posición y explicación

2. Si reglas encontraron errores (español):
   └─ Retornar correcciones de reglas

3. Si no (o idioma diferente):
   ├─ Dividir texto en chunks
   ├─ Para cada chunk:
   │  ├─ Construir prompt de corrección
   │  ├─ Llamar a Hugging Face
   │  ├─ Parsear correcciones
   │  └─ Ajustar posiciones
   └─ Combinar resultados

4. Determinar si hay errores

5. Retornar resultado
```

**Ejemplo de Sugerencia:**

```python
GrammarSuggestion(
    original="yo fue",
    correction="yo fui",
    explanation='Verb conjugation: "yo fui" (preterite)',
    position=15  # posición en el texto original
)
```

#### `_apply_rule_based_corrections()` - Aplicar Reglas

**Ubicación:** [`app/services/grammar_service.py:158-218`](app/services/grammar_service.py#L158-L218)

```python
def _apply_rule_based_corrections(
    self,
    text: str,
    language_code: str
) -> tuple[str, list[GrammarSuggestion]]
```

**Algoritmo:**

```python
# 1. Verificar idioma
if language_code.lower() != "es":
    return text, []  # Solo español soportado

# 2. Recopilar coincidencias
all_matches: list[tuple[re.Match, str, str]] = []
for pattern, replacement, explanation in SPANISH_GRAMMAR_RULES:
    matches = list(re.finditer(pattern, text, re.IGNORECASE))
    for match in matches:
        all_matches.append((match, replacement, explanation))

# 3. Ordenar por posición
all_matches.sort(key=lambda x: x[0].start())

# 4. Aplicar correcciones con offset
offset = 0
for match, replacement, explanation in all_matches:
    # Manejar lambdas (correcciones dinámicas)
    if callable(replacement):
        replacement_with_case = replacement(match)
    else:
        # Preservar capitalización
        if original[0].isupper():
            replacement_with_case = replacement[0].upper() + replacement[1:]

    # Agregar sugerencia
    suggestions.append(GrammarSuggestion(...))

    # Aplicar con offset acumulado
    corrected_text = (
        corrected_text[:position + offset] +
        replacement_with_case +
        corrected_text[position + offset + len(original):]
    )

    # Actualizar offset
    offset += len(replacement_with_case) - len(original)

# 5. Retornar
return corrected_text, suggestions
```

#### `_parse_corrections()` - Parsear Respuesta IA

**Ubicación:** [`app/services/grammar_service.py:234-310`](app/services/grammar_service.py#L234-L310)

```python
def _parse_corrections(
    self,
    response: str,
    original_text: str
) -> tuple[str, list[GrammarSuggestion]]
```

**Estrategias de Parsing:**

```
1. Limpiar respuesta (remover explicaciones)

2. Verificar si respuesta == original
   └─ Si igual: no hay errores

3. Calcular similitud (similarity score)
   ├─ < 60%: modelo reformuló mucho → ignorar
   └─ ≥ 60%: correcciones aceptables

4. Intentar extraer correcciones estructuradas:
   Formato: "Original: \"X\" -> Correction: \"Y\" (Explanation: Z)"
   ├─ Si encuentra: usar esas correcciones
   └─ Si no: comparar palabra por palabra

5. Generar sugerencias con posiciones

6. Retornar texto corregido y sugerencias
```

**Ejemplo de Prompt para IA:**

```
▼ Grammar Correction

Please fix any mistakes in the following [source] sentence or
keep it unedited if it's correct.

Sentence: yo fue al mercado ayer

Corrected:
```

### Parámetros de Optimización

```python
self.parameters = {
    "max_new_tokens": 512,
    "do_sample": True,           # Habilita sampling
    "temperature": 0.3,          # Baja pero no muy baja
    "top_p": 0.9,                # Nucleus sampling
    "repetition_penalty": 1.1,   # Penaliza repetición
}
self.chunk_chars = 800
```

---

## Servicio de Post-Editing

**Ubicación:** [`app/services/post_editing_service.py`](app/services/post_editing_service.py)

### Clase Principal

```python
class HuggingFacePostEditingService:
    def __init__(
        self,
        api_key: str,
        endpoint: str,
        model: str | None = None,
        parameters: dict[str, Any] | None = None
    )
```

### Método Principal

#### `post_edit()` - Edición de Texto

**Ubicación:** [`app/services/post_editing_service.py:155-244`](app/services/post_editing_service.py#L155-L244)

```python
async def post_edit(
    self,
    text: str,
    language: str,
    tone: str | None = None,
    length: PostEditLength | None = None
) -> str
```

**Parámetros:**

| Parámetro | Tipo | Descripción | Valores |
|-----------|------|-------------|---------|
| `text` | string | Texto a editar | Cualquier texto |
| `language` | string | Código ISO del idioma | "es", "en", "ca", etc. |
| `tone` | string (opcional) | Tono deseado | "formal", "casual", "professional" |
| `length` | PostEditLength (opcional) | Preferencia de longitud | `shorter`, `longer`, `same` |

**Proceso:**

```
1. Dividir texto en chunks (800 chars)

2. Para cada chunk:
   ├─ Construir prompt con instrucciones
   │  ├─ Idioma objetivo
   │  ├─ Tono (si especificado)
   │  └─ Preferencia de longitud
   │
   ├─ Calcular max_new_tokens dinámicamente
   │  ├─ shorter: chunk * 0.9
   │  ├─ longer: chunk * 1.35
   │  └─ same: chunk * 1.1
   │
   ├─ Llamar a Hugging Face
   │
   └─ Limpiar respuesta

3. Combinar chunks editados

4. Retornar texto mejorado
```

#### `_build_prompt()` - Construcción de Prompt

**Ubicación:** [`app/services/post_editing_service.py:108-134`](app/services/post_editing_service.py#L108-L134)

```python
def _build_prompt(
    self,
    chunk: str,
    language_name: str,
    tone: str | None,
    length_preference: PostEditLength | None
) -> str
```

**Ejemplo de Prompts Generados:**

**Prompt Básico:**
```
Rewrite the following text in Spanish to improve clarity and correctness.
Keep the original meaning intact and avoid adding explanations.
Return only the edited text.
Keep roughly the same length as the input.

Text:
El texto necesita algunas mejoras aqui.

Edited text:
```

**Prompt con Tono Formal:**
```
Rewrite the following text in English to improve clarity and correctness.
Keep the original meaning intact and avoid adding explanations.
Return only the edited text.
Use a formal tone.
Make it shorter and more concise while keeping key details.

Text:
Hey, can you send me that file?

Edited text:
```

**Prompt para Expandir:**
```
Rewrite the following text in Catalan to improve clarity and correctness.
Keep the original meaning intact and avoid adding explanations.
Return only the edited text.
Expand it slightly with a bit more detail while keeping the same intent.

Text:
Està bé.

Edited text:
```

#### `_build_params()` - Parámetros Dinámicos

**Ubicación:** [`app/services/post_editing_service.py:136-153`](app/services/post_editing_service.py#L136-L153)

```python
def _build_params(
    self,
    chunk: str,
    length_preference: PostEditLength | None
) -> dict[str, Any]
```

**Cálculo de Tokens:**

```python
# Multiplicador según preferencia
multiplier = 1.1  # default (same)
if length_preference == PostEditLength.shorter:
    multiplier = 0.9   # 90% del original
elif length_preference == PostEditLength.longer:
    multiplier = 1.35  # 135% del original

# Calcular tokens con límite
configured_max = 512
max_new = max(80, min(configured_max, int(len(chunk) * multiplier) + 80))
```

**Ejemplo:**

```python
chunk = "Texto de 100 caracteres..."

# shorter: max_new_tokens = max(80, min(512, 100 * 0.9 + 80)) = 170
# same:    max_new_tokens = max(80, min(512, 100 * 1.1 + 80)) = 190
# longer:  max_new_tokens = max(80, min(512, 100 * 1.35 + 80)) = 215
```

### Enum PostEditLength

```python
class PostEditLength(str, Enum):
    shorter = "shorter"  # Más conciso
    longer = "longer"    # Más detallado
    same = "same"        # Misma longitud aprox
```

### Parámetros de Optimización

```python
self.parameters = {
    "max_new_tokens": 512,
    "do_sample": False,      # Greedy para consistencia
    "temperature": 0.2,      # Baja para ediciones conservadoras
}
self.chunk_chars = 800
```

---

## Configuración de Providers

### Modelo TranslationProvider

**Ubicación:** [`app/models/translation.py`](app/models/translation.py)

```python
class TranslationProvider(Base):
    __tablename__ = "translation_providers"

    id: BigInteger
    name: String(100)                    # Nombre descriptivo
    provider_type: String(50)            # "huggingface"
    endpoint: String(255)                # URL del endpoint
    encrypted_api_key: String(500)      # API key encriptada
    region: String(50)                   # Región (opcional)
    is_active: Boolean                   # Activo/inactivo
    is_default: Boolean                  # Provider por defecto
    configuration: JSON                  # Configuración personalizada
    input_language_ids: list[int]       # IDs de idiomas de entrada
    output_language_ids: list[int]      # IDs de idiomas de salida
```

### Configuración JSON

```json
{
  "model": "BSC-LT/salamandra-2b",
  "parameters": {
    "max_new_tokens": 512,
    "do_sample": false,
    "temperature": 0.2,
    "top_p": 0.9,
    "repetition_penalty": 1.1,
    "chunk_chars": 800
  }
}
```

**Parámetros Configurables:**

| Parámetro | Descripción | Valores Típicos |
|-----------|-------------|-----------------|
| `max_new_tokens` | Tokens máximos a generar | 256, 512, 1024 |
| `do_sample` | Habilitar sampling | true, false |
| `temperature` | Aleatoriedad (0-2) | 0.1-1.0 |
| `top_p` | Nucleus sampling | 0.8-0.95 |
| `repetition_penalty` | Penaliza repetición | 1.0-1.2 |
| `chunk_chars` | Tamaño de chunk | 500-1000 |

### Factory Pattern

**Ubicación:** [`app/services/translation_service.py:432-496`](app/services/translation_service.py#L432-L496)

```python
class TranslationServiceFactory:
    @staticmethod
    async def get_service(
        db: AsyncSession,
        provider_id: int | None = None
    ) -> HuggingFaceTranslationService
```

**Proceso:**

```
1. Obtener provider de BD
   ├─ Si provider_id: buscar ese provider
   └─ Si None: buscar provider por defecto

2. Validar provider
   ├─ Existe?
   ├─ Está activo?
   ├─ Es tipo "huggingface"?
   └─ Tiene endpoint?

3. Desencriptar API key
   └─ Usar EncryptionService

4. Extraer configuración
   ├─ model
   └─ parameters

5. Crear y retornar instancia del servicio
```

**Ejemplo de Uso:**

```python
# Obtener servicio con provider por defecto
service = await TranslationServiceFactory.get_service(db)

# Obtener servicio con provider específico
service = await TranslationServiceFactory.get_service(db, provider_id=2)

# Usar el servicio
translated = await service.translate(
    text="Hello world",
    source_language="en",
    target_language="es"
)
```

---

## Endpoints de API

**Ubicación:** [`app/api/translations.py`](app/api/translations.py)

### Traducción

#### POST `/api/translations/translate`

**Ubicación:** [`app/api/translations.py:274-326`](app/api/translations.py#L274-L326)

**Descripción:** Traduce texto (respuesta única).

**Request Body:**
```json
{
  "text": "Hello, how are you?",
  "source_language_code": "en",
  "target_language_code": "es",
  "provider_id": null
}
```

**Response:** 200 OK
```json
{
  "id": 15,
  "provider_id": 1,
  "source_language_id": 1,
  "target_language_id": 2,
  "source_text": "Hello, how are you?",
  "translated_text": "Hola, ¿cómo estás?",
  "character_count": 19,
  "user_id": 10,
  "created_at": "2025-01-15T18:30:00",
  "source_language": {
    "id": 1,
    "code": "en",
    "name": "English",
    "is_active": true
  },
  "target_language": {
    "id": 2,
    "code": "es",
    "name": "Spanish",
    "is_active": true
  }
}
```

**Características:**
- ✅ Guarda en historial automáticamente
- ✅ Valida idiomas disponibles
- ✅ Usa provider por defecto si no se especifica
- ✅ Requiere permiso `translations:translate`

#### POST `/api/translations/translate/stream`

**Ubicación:** [`app/api/translations.py:328-391`](app/api/translations.py#L328-L391)

**Descripción:** Traduce texto con streaming (respuesta progresiva).

**Request Body:** (igual que `/translate`)

**Response:** 200 OK (text/plain; charset=utf-8)
```
Hola... ¿cómo... estás?
```

**Características:**
- ⚡ Streaming de tokens en tiempo real
- 📊 Cliente recibe tokens mientras se generan
- 💾 Guarda en historial al finalizar
- 🔄 Streaming chunk por chunk

**Ejemplo de Cliente (JavaScript):**

```javascript
async function translateStream(text, sourceLang, targetLang) {
  const response = await fetch('/api/translations/translate/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      text,
      source_language_code: sourceLang,
      target_language_code: targetLang
    })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  let translatedText = '';

  while (true) {
    const {done, value} = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    translatedText += chunk;

    // Actualizar UI progresivamente
    updateTranslationDisplay(translatedText);
  }

  return translatedText;
}
```

### Grammar Checker

#### POST `/api/translations/grammar-check`

**Ubicación:** [`app/api/translations.py:424-454`](app/api/translations.py#L424-L454)

**Descripción:** Revisa gramática y ortografía.

**Request Body:**
```json
{
  "text": "yo fue al mercado ayer",
  "language_code": "es",
  "provider_id": null
}
```

**Response:** 200 OK
```json
{
  "corrected_text": "yo fui al mercado ayer",
  "suggestions": [
    {
      "original": "yo fue",
      "correction": "yo fui",
      "explanation": "Verb conjugation: \"yo fui\" (preterite)",
      "position": 0
    }
  ],
  "has_errors": true,
  "language": {
    "id": 2,
    "code": "es",
    "name": "Spanish",
    "is_active": true
  }
}
```

**Características:**
- 🔍 Reglas gramaticales para español
- 🤖 IA para otros idiomas
- 📝 Sugerencias con posición y explicación
- ✅ Indica si hay errores

### Post-Editing

#### POST `/api/translations/post-edit`

**Ubicación:** [`app/api/translations.py:459-491`](app/api/translations.py#L459-L491)

**Descripción:** Mejora y reescribe texto.

**Request Body:**
```json
{
  "text": "El texto necesita mejoras aqui",
  "language_code": "es",
  "tone": "formal",
  "length": "same",
  "provider_id": null
}
```

**Response:** 200 OK
```json
{
  "edited_text": "El texto requiere mejoras aquí",
  "language": {
    "id": 2,
    "code": "es",
    "name": "Spanish",
    "is_active": true
  },
  "tone_applied": "formal",
  "length": "same"
}
```

**Parámetros Opcionales:**

| Campo | Valores | Descripción |
|-------|---------|-------------|
| `tone` | "formal", "casual", "professional", etc. | Tono del texto editado |
| `length` | "shorter", "longer", "same" | Preferencia de longitud |

**Ejemplo de Uso - Formal y Conciso:**

```bash
curl -X POST $API_BASE/translations/post-edit \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "hey, envíame el archivo porfa",
    "language_code": "es",
    "tone": "formal",
    "length": "shorter"
  }'
```

**Response:**
```json
{
  "edited_text": "Por favor, envíeme el archivo.",
  "tone_applied": "formal",
  "length": "shorter"
}
```

### Historial de Traducciones

#### GET `/api/translations/history`

**Ubicación:** [`app/api/translations.py:393-407`](app/api/translations.py#L393-L407)

**Descripción:** Obtiene historial del usuario actual.

**Query Parameters:**
- `skip`: Registros a omitir (default: 0)
- `limit`: Máximo de registros (default: 100, max: 100)

**Response:** 200 OK
```json
[
  {
    "id": 15,
    "source_text": "Hello",
    "translated_text": "Hola",
    "source_language": {...},
    "target_language": {...},
    "created_at": "2025-01-15T18:30:00",
    ...
  },
  ...
]
```

#### GET `/api/translations/history/all` 🔒

**Ubicación:** [`app/api/translations.py:410-419`](app/api/translations.py#L410-L419)

**Descripción:** Obtiene todo el historial (admin).

**Requiere:** Permiso `translations:read`

---

## Idiomas Soportados

### Lista Completa de Idiomas

**Ubicación:** [`app/services/translation_service.py:148-186`](app/services/translation_service.py#L148-L186)

| Código ISO | Nombre Completo | Código ISO | Nombre Completo |
|------------|-----------------|------------|-----------------|
| **en** | English | **pl** | Polish |
| **es** | Spanish | **ro** | Romanian |
| **ca** | Catalan | **ru** | Russian |
| **gl** | Galician | **sr** | Serbian |
| **pt** | Portuguese | **sk** | Slovak |
| **fr** | French | **sl** | Slovenian |
| **de** | German | **sv** | Swedish |
| **it** | Italian | **uk** | Ukrainian |
| **eu** | Basque | **cy** | Welsh |
| **an** | Aragonese | **nb** | Norwegian Bokmål |
| **ast** | Asturian | **nn** | Norwegian Nynorsk |
| **bg** | Bulgarian | **oc** | Occitan |
| **hr** | Croatian | **mt** | Maltese |
| **cs** | Czech | **ga** | Irish |
| **da** | Danish | **lv** | Latvian |
| **nl** | Dutch | **lt** | Lithuanian |
| **et** | Estonian | | |
| **fi** | Finnish | | |
| **el** | Greek | | |
| **hu** | Hungarian | | |

**Total:** 27 idiomas soportados

### Gestión de Idiomas

#### GET `/api/translations/languages` (Público)

**Ubicación:** [`app/api/translations.py:192-201`](app/api/translations.py#L192-L201)

```bash
curl -X GET "$API_BASE/translations/languages?only_active=true"
```

#### POST `/api/translations/languages` 🔒

**Ubicación:** [`app/api/translations.py:204-217`](app/api/translations.py#L204-L217)

```bash
curl -X POST $API_BASE/translations/languages \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "ja",
    "name": "Japanese",
    "is_active": true
  }'
```

**Requiere:** Permiso `translations:manage`

#### PATCH `/api/translations/languages/{id}/toggle` 🔒

**Ubicación:** [`app/api/translations.py:258-269`](app/api/translations.py#L258-L269)

```bash
# Desactivar idioma
curl -X PATCH "$API_BASE/translations/languages/5/toggle?is_active=false" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## Ejemplos de Uso

### Ejemplo 1: Traducción Simple

```bash
# Traducir de inglés a español
curl -X POST http://localhost:8000/api/translations/translate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "The quick brown fox jumps over the lazy dog",
    "source_language_code": "en",
    "target_language_code": "es"
  }'
```

**Respuesta:**
```json
{
  "id": 20,
  "translated_text": "El rápido zorro marrón salta sobre el perro perezoso",
  "character_count": 44,
  ...
}
```

### Ejemplo 2: Traducción con Streaming (Python)

```python
import httpx

async def translate_with_streaming():
    url = "http://localhost:8000/api/translations/translate/stream"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "text": "This is a long paragraph that needs translation...",
        "source_language_code": "en",
        "target_language_code": "es"
    }

    async with httpx.AsyncClient() as client:
        async with client.stream("POST", url, headers=headers, json=data) as response:
            translated_text = ""
            async for chunk in response.aiter_text():
                translated_text += chunk
                print(chunk, end="", flush=True)  # Mostrar progresivamente

            print(f"\n\nTraducción completa: {translated_text}")
```

### Ejemplo 3: Revisión Gramatical

```bash
# Revisar gramática en español
curl -X POST http://localhost:8000/api/translations/grammar-check \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "yo fue al mercado ayer y nadie saben donde esta el pan",
    "language_code": "es"
  }'
```

**Respuesta:**
```json
{
  "corrected_text": "yo fui al mercado ayer y nadie sabe donde está el pan",
  "suggestions": [
    {
      "original": "yo fue",
      "correction": "yo fui",
      "explanation": "Verb conjugation: \"yo fui\" (preterite)",
      "position": 0
    },
    {
      "original": "nadie saben",
      "correction": "nadie sabe",
      "explanation": "Subject-verb agreement: \"nadie\" is singular",
      "position": 28
    },
    {
      "original": "esta",
      "correction": "está",
      "explanation": "Missing accent on \"está\"",
      "position": 47
    }
  ],
  "has_errors": true
}
```

### Ejemplo 4: Post-Editing con Tono Formal

```bash
# Convertir texto casual a formal
curl -X POST http://localhost:8000/api/translations/post-edit \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "hey, necesito que me envies el archivo cuanto antes porfa",
    "language_code": "es",
    "tone": "formal",
    "length": "same"
  }'
```

**Respuesta:**
```json
{
  "edited_text": "Estimado/a, le agradecería que me envíe el archivo lo antes posible.",
  "tone_applied": "formal",
  "length": "same"
}
```

### Ejemplo 5: Acortar Texto

```bash
# Hacer texto más conciso
curl -X POST http://localhost:8000/api/translations/post-edit \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "En el día de hoy, hemos llevado a cabo una reunión muy importante con todos los miembros del equipo para discutir ampliamente sobre los diversos temas relacionados con el proyecto actual que estamos desarrollando en este momento",
    "language_code": "es",
    "length": "shorter"
  }'
```

**Respuesta:**
```json
{
  "edited_text": "Hoy realizamos una reunión importante con el equipo para discutir el proyecto actual.",
  "length": "shorter"
}
```

### Ejemplo 6: Expandir Texto

```bash
# Hacer texto más detallado
curl -X POST http://localhost:8000/api/translations/post-edit \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Proyecto finalizado. Documentación lista.",
    "language_code": "es",
    "length": "longer"
  }'
```

**Respuesta:**
```json
{
  "edited_text": "El proyecto ha sido finalizado exitosamente y toda la documentación técnica correspondiente ha sido completada y está lista para su revisión.",
  "length": "longer"
}
```

### Ejemplo 7: Flujo Completo de Traducción y Mejora

```python
import httpx

async def translate_and_improve(text, source_lang, target_lang, tone="formal"):
    base_url = "http://localhost:8000/api/translations"
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient() as client:
        # 1. Traducir
        print("Traduciendo...")
        response = await client.post(
            f"{base_url}/translate",
            headers=headers,
            json={
                "text": text,
                "source_language_code": source_lang,
                "target_language_code": target_lang
            }
        )
        translation = response.json()
        translated_text = translation["translated_text"]
        print(f"Traducción: {translated_text}")

        # 2. Revisar gramática
        print("\nRevisando gramática...")
        response = await client.post(
            f"{base_url}/grammar-check",
            headers=headers,
            json={
                "text": translated_text,
                "language_code": target_lang
            }
        )
        grammar = response.json()
        corrected_text = grammar["corrected_text"]
        if grammar["has_errors"]:
            print(f"Errores encontrados: {len(grammar['suggestions'])}")
            for suggestion in grammar["suggestions"]:
                print(f"  - {suggestion['original']} → {suggestion['correction']}")
        print(f"Texto corregido: {corrected_text}")

        # 3. Mejorar estilo
        print("\nMejorando estilo...")
        response = await client.post(
            f"{base_url}/post-edit",
            headers=headers,
            json={
                "text": corrected_text,
                "language_code": target_lang,
                "tone": tone,
                "length": "same"
            }
        )
        edited = response.json()
        final_text = edited["edited_text"]
        print(f"Texto final: {final_text}")

        return final_text

# Usar
text = "Please send me the report by tomorrow morning"
result = await translate_and_improve(text, "en", "es", "formal")
```

---

## Optimizaciones y Parámetros

### Parámetros de Generación

#### Translation Service

```python
# Optimizado para velocidad
{
    "max_new_tokens": 512,
    "do_sample": False,         # Greedy decoding = más rápido
    "return_full_text": False,
}
```

**Razones:**
- `do_sample: False` → Greedy decoding más rápido y determinista
- `max_new_tokens: 512` → Suficiente para la mayoría de traducciones
- Sin temperature/top_p → No hay aleatoriedad

#### Grammar Service

```python
# Optimizado para corrección
{
    "max_new_tokens": 512,
    "do_sample": True,              # Permite variaciones
    "temperature": 0.3,             # Baja pero no demasiado
    "top_p": 0.9,                   # Nucleus sampling
    "repetition_penalty": 1.1,      # Evita repeticiones
}
```

**Razones:**
- `do_sample: True` → Permite correcciones variadas
- `temperature: 0.3` → Balance entre creatividad y precisión
- `top_p: 0.9` → Filtra opciones poco probables
- `repetition_penalty` → Evita bucles de repetición

#### Post-Editing Service

```python
# Optimizado para reescritura
{
    "max_new_tokens": 512,
    "do_sample": False,      # Determinista
    "temperature": 0.2,      # Muy baja para conservar significado
}
```

**Razones:**
- `temperature: 0.2` → Ediciones conservadoras
- `do_sample: False` → Consistencia en resultados

### Chunking Strategies

**Tamaño Óptimo de Chunk:** 800 caracteres

**Razones:**
- ✅ Balance entre contexto y velocidad
- ✅ Evita timeouts en endpoints lentos
- ✅ Preserva párrafos completos en la mayoría de casos
- ✅ Permite streaming eficiente

**Ajustar chunk_chars:**

```json
{
  "parameters": {
    "chunk_chars": 1000  # Chunks más grandes (más contexto)
  }
}
```

### max_new_tokens Dinámico

**Translation:**
```python
# Basado en longitud del chunk
max_new = max(10, min(512, int(len(chunk) * 1.5) + 20))
```

**Post-Editing:**
```python
# Basado en preferencia de longitud
multiplier = {
    "shorter": 0.9,
    "same": 1.1,
    "longer": 1.35
}[length_preference]

max_new = max(80, min(512, int(len(chunk) * multiplier) + 80))
```

### Consideraciones de Rendimiento

**Latencia Típica:**

| Operación | Latencia | Factores |
|-----------|----------|----------|
| Translate (1 chunk) | 1-3s | Tamaño de chunk, modelo |
| Translate Stream (inicio) | < 1s | Primer token |
| Grammar Check | 2-4s | Complejidad del texto |
| Post-Edit | 2-3s | Longitud del texto |

**Optimizaciones Implementadas:**

1. **Streaming** - Primeros tokens en < 1s
2. **Async/await** - No bloquea el event loop
3. **Thread pool** - HF client síncrono en thread separado
4. **Chunking** - Procesamiento parallelizable
5. **Caching** - Reutilización de servicios (factory pattern)

---

## Manejo de Errores

### Errores Comunes y Soluciones

#### Error 400: Language not available

```json
{
  "detail": "Source language 'xx' not available"
}
```

**Causa:** Idioma no existe o está inactivo

**Solución:**
```bash
# Verificar idiomas disponibles
curl -X GET "$API_BASE/translations/languages?only_active=true"

# Activar idioma (admin)
curl -X PATCH "$API_BASE/translations/languages/5/toggle?is_active=true" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

#### Error 500: Empty response from service

```json
{
  "detail": "Empty response from Hugging Face translation service"
}
```

**Causa:** Endpoint de HF no respondió

**Solución:**
1. Verificar endpoint está activo
2. Verificar API key es válida
3. Revisar logs del provider

#### Error 502: Translation failed

```json
{
  "detail": "Hugging Face translation failed: Connection timeout"
}
```

**Causas posibles:**
- Endpoint de HF caído
- API key inválida
- Rate limiting

**Solución:**
```bash
# Verificar provider
curl -X GET $API_BASE/translations/providers/1 \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Cambiar a provider alternativo
curl -X POST $API_BASE/translations/providers/2/default \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Estrategias de Fallback

**En Streaming:**

```python
# Si streaming falla, intenta sin streaming
try:
    async for token in stream_tokens():
        yield token
except Exception:
    # Fallback a generación completa
    result = await generate_complete()
    yield result
```

**En Grammar Check:**

```python
# Si IA falla, usar solo reglas (español)
if language == "es":
    corrected, suggestions = apply_rules(text)
    if suggestions:
        return corrected, suggestions, True

# Intentar con IA
try:
    return await ai_check(text)
except Exception:
    # Retornar texto original si todo falla
    return text, [], False
```

### Logging y Debugging

**Habilitar logs detallados:**

```python
import logging

# En development
logging.basicConfig(level=logging.DEBUG)

# En production
logging.basicConfig(level=logging.INFO)
```

**Logs útiles:**

```python
logger.info(f"Translation request: {len(text)} chars, {source} → {target}")
logger.debug(f"Chunks created: {len(chunks)}")
logger.debug(f"Prompt: {prompt[:100]}...")
logger.debug(f"Response: {response[:100]}...")
logger.error(f"Translation failed: {str(e)}")
```

---

## Buenas Prácticas

### 1. Gestión de Providers

✅ **HACER:**
- Mantener al menos 2 providers activos (redundancia)
- Configurar provider por defecto confiable
- Monitorear uso y rendimiento de cada provider
- Rotar API keys periódicamente

❌ **NO HACER:**
- Almacenar API keys en código
- Compartir API keys entre ambientes
- Dejar providers inactivos sin eliminar

### 2. Uso de Servicios

✅ **HACER:**
- Usar streaming para textos > 100 caracteres
- Validar idiomas antes de traducir
- Implementar rate limiting en cliente
- Cachear traducciones frecuentes

❌ **NO HACER:**
- Traducir textos > 5000 chars sin chunking
- Ignorar errores de validación
- Hacer requests en bucles sin delay

### 3. Optimización de Parámetros

✅ **HACER:**
```python
# Para velocidad máxima
{
    "do_sample": False,
    "max_new_tokens": 256,
    "chunk_chars": 500
}

# Para calidad máxima
{
    "do_sample": True,
    "temperature": 0.3,
    "top_p": 0.9,
    "max_new_tokens": 512,
    "chunk_chars": 1000
}
```

❌ **NO HACER:**
```python
# Muy lento
{
    "max_new_tokens": 2048,
    "chunk_chars": 5000
}

# Muy aleatorio
{
    "temperature": 1.5,
    "top_p": 0.5
}
```

### 4. Manejo de Textos Largos

✅ **HACER:**
```python
# Dividir texto largo antes de enviar
paragraphs = text.split("\n\n")
results = []

for para in paragraphs:
    if len(para) > 5000:
        # Dividir párrafo muy largo
        chunks = split_into_chunks(para, 800)
        for chunk in chunks:
            result = await translate(chunk)
            results.append(result)
    else:
        result = await translate(para)
        results.append(result)

final_text = "\n\n".join(results)
```

❌ **NO HACER:**
```python
# Enviar texto completo sin dividir
huge_text = "..." * 10000
result = await translate(huge_text)  # Probablemente falle
```

### 5. Grammar Checking

✅ **HACER:**
- Usar grammar check después de traducción automática
- Aplicar sugerencias selectivamente (revisar contexto)
- Para español: confiar en reglas basadas en regex
- Para otros idiomas: usar IA con temperatura baja

❌ **NO HACER:**
- Aplicar todas las sugerencias automáticamente
- Ignorar el campo `has_errors`
- Usar grammar check en textos ya corregidos manualmente

### 6. Post-Editing

✅ **HACER:**
```python
# Uso apropiado de tone
"formal" → Documentos oficiales, emails profesionales
"casual" → Redes sociales, conversaciones informales
"professional" → Presentaciones, informes técnicos

# Uso apropiado de length
"shorter" → Resúmenes, tweets, títulos
"same" → Mantener longitud original
"longer" → Explicaciones detalladas, documentación
```

❌ **NO HACER:**
- Usar "longer" cuando el texto ya es largo
- Cambiar tone múltiples veces en el mismo texto
- Esperar cambios drásticos con "same"

### 7. Seguridad

✅ **HACER:**
- Validar longitud máxima de input (ej: 10,000 chars)
- Sanitizar texto antes de procesar
- Verificar permisos en cada request
- Encriptar API keys en BD
- Usar HTTPS en producción

❌ **NO HACER:**
- Aceptar inputs sin límite
- Exponer API keys en respuestas
- Permitir acceso sin autenticación
- Almacenar API keys en plaintext

### 8. Monitoreo y Métricas

✅ **HACER:**
```python
# Métricas importantes a trackear
- Traducciones por usuario/día
- Latencia promedio por servicio
- Tasa de errores
- Uso de caracteres por provider
- Distribución de idiomas
```

**Ejemplo de Query:**

```sql
-- Traducciones por día
SELECT
    DATE(created_at) as date,
    COUNT(*) as translations,
    SUM(character_count) as total_chars
FROM translations
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

---

## Referencias de Código

### Archivos Principales

| Archivo | Descripción |
|---------|-------------|
| [`app/services/translation_service.py`](app/services/translation_service.py) | Servicio de traducción |
| [`app/services/grammar_service.py`](app/services/grammar_service.py) | Servicio de grammar checking |
| [`app/services/post_editing_service.py`](app/services/post_editing_service.py) | Servicio de post-editing |
| [`app/api/translations.py`](app/api/translations.py) | Endpoints de API |
| [`app/schemas/translation.py`](app/schemas/translation.py) | Schemas de validación |
| [`app/models/translation.py`](app/models/translation.py) | Modelos de BD |
| [`app/crud/translation.py`](app/crud/translation.py) | Operaciones CRUD |

### Dependencias Clave

```
huggingface_hub     # Cliente para Hugging Face API
fastapi            # Framework web
sqlalchemy         # ORM
pydantic           # Validación de datos
cryptography       # Encriptación de API keys
```

---

**Documentación generada el 2025-01-15**
**Versión: 1.0**
