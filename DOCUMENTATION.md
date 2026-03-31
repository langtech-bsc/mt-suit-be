# 🦎 Cómo usar los modelos SalamandraTA

## 📌 Ubicación de nuestros modelos publicados:

- https://huggingface.co/BSC-LT/salamandraTA-2b-instruct → [Versión cuantizada](https://huggingface.co/BSC-LT/salamandraTA-2B-instruct-GGUF)
- https://huggingface.co/BSC-LT/salamandraTA-7b-instruct → [Versión cuantizada](https://huggingface.co/BSC-LT/salamandraTA-7B-instruct-GGUF)

## Tabla de Contenidos

- [Introducción](#introducción)
- [Guía de Inicio Rápido - Modelos Completos](#guía-de-inicio-rápido---modelos-completos)
  - [Requisitos de Instalación](#requisitos-de-instalación)
  - [Cargar el Modelo y el Tokenizer en Python](#cargar-el-modelo-y-el-tokenizer-en-python)
  - [Preparar tu Primer Prompt](#preparar-tu-primer-prompt)
  - [Generar una Traducción (Inferencia)](#generar-una-traducción-inferencia)
- [Guía de Inicio Rápido - Modelos Cuantizados](#guía-de-inicio-rápido---modelos-cuantizados)
  - [Requisitos de Instalación](#requisitos-de-instalación-1)
  - [Cargar el Modelo y el Tokenizer en Python](#cargar-el-modelo-y-el-tokenizer-en-python-1)
  - [Preparar tu Primer Prompt](#preparar-tu-primer-prompt-1)
  - [Generar una Traducción (Inferencia)](#generar-una-traducción-inferencia-1)
- [Guía de Prompts](#guía-de-prompts)
- [Prompts Multi-turno](#prompts-multi-turno)
  - [Cargar el Modelo y el Tokenizer](#cargar-el-modelo-y-el-tokenizer)
  - [Definir una Función Helper de Chat](#definir-una-función-helper-de-chat)
  - [Ejemplo: Traducciones Alternativas](#ejemplo-traducciones-alternativas)
  - [Notas sobre interacciones multi-turno](#notas-sobre-interacciones-multi-turno)
- [Estrategias de Decodificación](#estrategias-de-decodificación)
  - [Decodificación Greedy (Por Defecto)](#decodificación-greedy-por-defecto)
  - [Beam Search](#beam-search)
  - [Nota Importante sobre Tokens de Finalización](#nota-importante-sobre-tokens-de-finalización)
  - [Diverse Beam Search](#diverse-beam-search)
- [Estrategias de Decodificación Conscientes de Calidad](#estrategias-de-decodificación-conscientes-de-calidad)
  - [Tuned Re-ranking](#tuned-re-ranking)
  - [Decodificación Minimum Bayes Risk (MBR)](#decodificación-minimum-bayes-risk-mbr)

## Introducción

SalamandraTA es una familia de modelos de lenguaje multilingües ajustados para traducción y tareas tecnológicas relacionadas con el lenguaje. Estas variantes ajustadas por instrucciones (disponibles en tamaños de 2B y 7B) son parte de la suite más amplia de modelos Salamandra y son particularmente fuertes en catalán, español e inglés, con soporte para más de 35 idiomas.

Los modelos soportan traducción a nivel de oración y párrafo, post-edición automática, paráfrasis, corrección gramatical y NER multilingüe. Ambos modelos están disponibles en formatos de precisión completa y cuantizados, haciéndolos accesibles para una amplia gama de configuraciones de hardware.

Este documento sirve como wiki y guía de inicio rápido para desarrolladores e investigadores que quieran usar SalamandraTA para traducción y tareas relacionadas con MT. Incluye notas introductorias sobre prompts, estrategias de decodificación y especificaciones técnicas clave del modelo, con planes de publicar posts de blog más detallados que cubran estos temas con mayor profundidad.

## 📎 Resumen General

### Idiomas soportados: 35 idiomas (y 3 variedades)

Aragonés, Asturiano, Vasco, Búlgaro, Catalán (y variedad Valenciana), Croata, Checo, Danés, Neerlandés, Inglés, Estonio, Finlandés, Francés, Gallego, Alemán, Griego, Húngaro, Irlandés, Italiano, Letón, Lituano, Maltés, Noruego (variedades Bokmål y Nynorsk), Occitano (y variedad Aranesa), Polaco, Portugués, Rumano, Ruso, Serbio, Eslovaco, Esloveno, Español, Sueco, Ucraniano, Galés

### Tareas soportadas: 9 tareas de traducción y/o relacionadas con MT

- Traducción a nivel de oración
- Traducción a nivel de párrafo
- Traducción a nivel de documento
- Post-edición automática
- Revisión gramatical
- Evaluación de traducción automática
- Traducciones alternativas
- Reconocimiento de entidades nombradas
- Traducción consciente del contexto

### Arquitecturas

#### salamandraTA-2b-instruct

| Feature | Value |
|---------|-------|
| Parámetros totales | 2,253,490,176 |
| Parámetros de embedding | 524,288,000 |
| Capas | 24 |
| Tamaño oculto | 2,048 |
| Cabezales de atención | 16 |
| Longitud de contexto | 8,192 |
| Tamaño del vocabulario | 256,000 |
| Precisión | bfloat16 |
| Tipo de embedding | RoPE |
| Función de activación | SwiGLU |
| Normalización de capas | RMS Norm |
| Grouped query attention | ❌ |
| Flash attention | ✅ |
| Num. query groups | N/A |

#### salamandraTA-7b-instruct

| Feature | Value |
|---------|-------|
| Parámetros totales | 7,768,117,248 |
| Parámetros de embedding | 1,048,576,000 |
| Capas | 32 |
| Tamaño oculto | 4,096 |
| Cabezales de atención | 32 |
| Longitud de contexto | 8,192 |
| Tamaño del vocabulario | 256,000 |
| Precisión | bfloat16 |
| Tipo de embedding | RoPE |
| Función de activación | SwiGLU |
| Normalización de capas | RMS Norm |
| Grouped query attention | ✅ |
| Flash attention | ✅ |
| Num. query groups | 8 |

### Consideraciones de recursos

#### Modelos completos

**salamandraTA-2b-instruct**

Cargar el modelo SalamandraTA-2b requiere aproximadamente 4.5 GB de memoria GPU solo para los pesos. Se necesita memoria adicional para computaciones intermedias, activaciones y buffers.

Para inferencia estable y evitar errores de falta de memoria, se recomienda una GPU con al menos 12 GB de VRAM.

| Recurso | Requerimiento | Notas |
|---------|---------------|-------|
| Pesos (bf16) | ~4.5 GB | De 2.25B params |
| KV cache (8192 ctx) | ~1.6 GB | Crece linealmente con longitud de contexto |
| Total mínimo | ~6.1 GB | Solo pesos + KV |
| VRAM práctica | ≥12 GB | - |
| FLOPs/token | ~4.5B | ≈2 × params |

**salamandraTA-7b-instruct**

Cargar el modelo SalamandraTA-7b requiere aproximadamente 15.5 GB de memoria GPU solo para los pesos. Se necesita memoria adicional para computaciones intermedias, activaciones y buffers.

Para inferencia estable y evitar errores de falta de memoria, se recomienda una GPU con al menos 24 GB de VRAM.

| Recurso | Requerimiento | Notas |
|---------|---------------|-------|
| Pesos (bf16) | ~15.5 GB | De 7.77B params |
| KV cache (8192 ctx) | ~4.3 GB | Crece linealmente con longitud de contexto |
| Total mínimo | ~19.8 GB | Solo pesos + KV |
| VRAM práctica | ≥24 GB | - |
| FLOPs/token | ~15.5B | ≈3.45 × más pesado que 2B |

#### Modelos cuantizados

**salamandraTA-2b-instruct-GGUF**

Cargar el modelo SalamandraTA-2b cuantizado requiere aproximadamente 2.7 GB de memoria GPU solo para los pesos. Se necesita memoria adicional para computaciones intermedias, activaciones y buffers.

Para inferencia estable y evitar errores de falta de memoria, se recomienda una GPU con al menos 8 GB de VRAM.

| Recurso | Requerimiento | Notas |
|---------|---------------|-------|
| Pesos (Q4, CPU) | ~2.7-3 GB | De 2.25B params cuantizados |
| KV cache (8192 ctx, FP16) | ~1.6 GB | Crece linealmente con longitud de contexto |
| Total mínimo | ~4.3 GB | Solo pesos + KV |
| VRAM práctica | ≥8 GB | - |
| FLOPs/token | ~2.2B | ≈params × overhead de cuantización |

**salamandraTA-7b-instruct-GGUF**

Cargar el modelo SalamandraTA-7b cuantizado requiere aproximadamente 8.6 GB de memoria GPU solo para los pesos. Se necesita memoria adicional para computaciones intermedias, activaciones y buffers.

Para inferencia estable y evitar errores de falta de memoria, se recomienda una GPU con al menos 16 GB de VRAM.

| Recurso | Requerimiento | Notas |
|---------|---------------|-------|
| Pesos (Q4, CPU) | ~8.6 GB | De 6.7B params cuantizados |
| KV cache (8192 ctx, FP16) | ~5 GB | Crece linealmente con longitud de contexto |
| Total mínimo | ~13.6 GB | Solo pesos + KV |
| VRAM práctica | ≥16 GB | - |
| FLOPs/token | ~6.7B | ≈params × overhead de cuantización |

## Guía de Inicio Rápido - Modelos Completos

Esta sección guía a los usuarios desde la instalación de las herramientas necesarias hasta ejecutar tu primera tarea de traducción, independientemente del nivel de experiencia.

### Requisitos de Instalación

Asegúrate de tener los paquetes requeridos instalados:

```bash
pip install transformers accelerate sentencepiece
```

### Cargar el Modelo y el Tokenizer en Python

```python
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

# Cargar modelo y tokenizer
model_id = "BSC-LT/salamandraTA-7b-instruct"  # También puedes usar "BSC-LT/salamandraTA-2b-instruct"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    device_map="auto",  # Selecciona automáticamente GPU/CPU (recomendado para uso fluido)
    torch_dtype=torch.bfloat16  # Usa bfloat16 para inferencia más rápida (asegura soporte de hardware)
)
```

### Preparar tu Primer Prompt

Los modelos SalamandraTA usan un formato de prompt específico (ChatML) para entender las instrucciones correctamente. Así es como preparas un prompt para traducir texto de español a inglés:

```python
# Define tu tarea
# Estas variables cambiarán dependiendo de la tarea (traducción, NER, corrección gramatical, etc.)
source = "Spanish"
target = "English"
sentence = (
    "Ayer se fue, tomó sus cosas y se puso a navegar. Una camisa, un pantalón vaquero "
    "y una canción, dónde irá, dónde irá. Se despidió, y decidió batirse en duelo con el mar. "
    "Y recorrer el mundo en su velero. Y navegar, nai-na-na, navegar."
)

# Prepara el prompt de entrada usando el formato de instrucción estándar
# ver la Guía de Prompts para prompts recomendados para diferentes tareas
text = (
    f"Translate the following text from {source} into {target}.\n"
    f"{source}: {sentence}\n"
    f"{target}:"
)

# Estructura el prompt usando el formato ChatML
message = [{"role": "user", "content": text}]
prompt = tokenizer.apply_chat_template(
    message,
    tokenize=False,  # Devuelve string plano, no tokenizado
    add_generation_prompt=True  # Añade token especial para señalar que el modelo debe comenzar a generar
)
```

### Generar una Traducción (Inferencia)

```python
inputs = tokenizer.encode(
    prompt,
    add_special_tokens=False,  # No añade tokens especiales más allá de lo que incluye la plantilla ChatML
    return_tensors="pt"  # Devuelve como tensor de PyTorch
)
input_length = inputs.shape[1]  # Usado para recortar la porción del prompt de la salida

eos_tokens = [tokenizer.eos_token_id, tokenizer.convert_tokens_to_ids("<|im_end|>")]

outputs = model.generate(
    input_ids=inputs.to(model.device),  # Mueve automáticamente a CPU/GPU según sea necesario
    max_new_tokens=200,  # Aumenta esto para entradas más largas (ej., traducción a nivel de párrafo o documento)
    eos_token_id=eos_tokens,  # Usa token de parada ajustado por instrucciones y token de parada de pre-entrenamiento
    num_beams=1,  # 1 = decodificación greedy (usa num_beams > 1 para habilitar beam search)
    pad_token_id=tokenizer.eos_token_id  # Requerido para algunos modelos durante beam search
)

translation = tokenizer.decode(
    outputs[0, input_length:],  # Omite el prompt al decodificar
    skip_special_tokens=True  # Elimina cualquier token especial persistente
)

print(translation)
```

## Guía de Inicio Rápido - Modelos Cuantizados

### Requisitos de Instalación

Para inferencia con modelos cuantizados (GGUF), asegúrate de tener los paquetes requeridos instalados:

```bash
pip install huggingface_hub vllm torch
pip install llama-cpp-python
```

### Cargar el Modelo y el Tokenizer en Python

```python
from huggingface_hub import snapshot_download
from vllm import LLM, SamplingParams

# Descargar el modelo GGUF cuantizado de Hugging Face
model_dir = snapshot_download(
    repo_id="BSC-LT/salamandraTA-7B-instruct-GGUF",  # Reemplaza con el repo 2B si es necesario
    revision="main"  # Opcional: fija a una versión específica
)

# Elige qué archivo GGUF cargar; q4 es generalmente recomendado
model_name = "salamandrata_7b_inst_q4.gguf"

# Cargar el modelo cuantizado y tokenizer para inferencia
llm = LLM(
    model=model_dir + '/' + model_name,  # Ruta al archivo GGUF
    tokenizer=model_dir  # El tokenizer se detecta automáticamente desde el snapshot
)
```

### Preparar tu Primer Prompt

Los modelos SalamandraTA usan un formato de prompt específico (ChatML) para entender las instrucciones correctamente. Así es como preparas un prompt para traducir texto de español a inglés:

```python
# Define tu tarea
# Estas variables cambiarán dependiendo de la tarea (traducción, NER, corrección gramatical, etc.)
source = "Spanish"
target = "English"
sentence = (
    "Ayer se fue, tomó sus cosas y se puso a navegar. Una camisa, un pantalón vaquero "
    "y una canción, dónde irá, dónde irá. Se despidió, y decidió batirse en duelo con el mar. "
    "Y recorrer el mundo en su velero. Y navegar, nai-na-na, navegar."
)

# Prepara el prompt de entrada usando el formato de instrucción estándar
# ver la Guía de Prompts para prompts recomendados para diferentes tareas
prompt = f"Translate the following text from {source} into {target}.\\n{source}: {sentence} \\n{target}:"
messages = [{'role': 'user', 'content': prompt}]
```

### Generar una Traducción (Inferencia)

```python
outputs = llm.chat(
    messages,
    sampling_params=SamplingParams(
        temperature=0,  # Decodificación greedy (sin aleatoriedad)
        stop_token_ids=[5],  # Detiene la generación en el ID de token especial (debería corresponder a <|im_end|>)
        max_tokens=200  # Número máximo de nuevos tokens a generar; aumenta para textos más largos
    )
)[0].outputs

print(outputs[0].text)
```

## Guía de Prompts

Los modelos SalamandraTA fueron ajustados por instrucciones usando una combinación de prompts personalizados y conjuntos de datos de instrucciones disponibles públicamente.

Para traducción a nivel de oración, párrafo y documento, usamos un único prompt fijo en inglés aplicado consistentemente a través de pares de idiomas. Estas tareas son las más robustas y consistentes a través de la salida del modelo.

Para otras tareas, incluyendo post-edición, corrección gramatical, parafraseo, traducciones alternativas, evaluación de traducción automática y traducción consciente del contexto, incorporamos muestras de instrucción del [conjunto de datos TowerBlocks (Alves et al., 2024)](https://arxiv.org/pdf/2402.17733), que proporciona datos de ajuste de instrucciones de alta calidad y diversidad de tareas.

TowerBlocks incluye múltiples formulaciones de prompts por tarea, a menudo parafraseadas o reformuladas de diferentes maneras. Como resultado, el modelo tiene cierta tolerancia para instrucciones variadas en estas tareas secundarias. Sin embargo, el rendimiento puede ser menos consistente que para tareas de traducción a menos que la formulación del prompt esté cerca de lo que el modelo vio durante el entrenamiento.

### 🤖 Ejemplos de estructuras de prompt recomendadas para cada tarea soportada:

#### Traducción

```
Translate the following text from {src} into {tgt}.
{src}: {context}
{tgt}:
```

#### Post-edición

```
Please fix any mistakes in the following {source}-{target} machine translation
or keep it unedited if it's correct.
Source: {source_sentence}
MT: {machine_translation}
Corrected:
```

#### Traducción Consciente del Contexto

```
What is the {target} translation of the sentence below?
{sentence}
Use the following context to help your translation:
{context}
Translation:
```

#### Parafraseo

```
Rewrite the following sentence in {target} without changing its meaning:
Source: {sentence}
Paraphrase:
```

#### Corrección Gramatical

```
Please fix any mistakes in the following {source} sentence or keep it unedited if it's correct.
Sentence: {sentence}
Corrected:
```

#### Reconocimiento de Entidades Nombradas (NER)

```
Analyse the following tokenized text and mark the tokens containing named entities.
Use the following annotation guidelines with these tags for named entities:
- ORG (Refers to named groups or organizations)
- PER (Refers to individual people or named groups of people)
- LOC (Refers to physical places or natural landmarks)
- MISC (Refers to entities that don't fit into standard categories).

Prepend B- to the first token of a given entity and I- to the remaining ones if they exist.
If a token is not a named entity, label it as O.

Input: {list of words in a sentence}
Marked:
```

#### Evaluación de Traducción Automática

```
Source: {sentence}
Pick the best English translation from the following pool of candidates:
1. {translation_1}
2. {translation_2}
3. {translation_3}
4. {translation_4}

Choose the translation that best conveys the meaning of the original source by indicating its corresponding number.
```

## Prompts Multi-turno

Algunas tareas soportadas por los modelos SalamandraTA, como Traducciones Alternativas, requieren interacciones multi-turno. Estos son escenarios donde el modelo recibe prompts más de una vez en una estructura similar a una conversación, y cada prompt depende de la respuesta anterior del modelo.

A diferencia de las tareas de un solo disparo, las interacciones multi-turno deben manejarse programáticamente o dentro de un entorno de notebook, donde puedes:

1. Enviar un prompt inicial
2. Capturar la respuesta del modelo
3. Enviar un segundo prompt que se base en esa respuesta
4. Repetir según sea necesario

Este estilo conversacional refleja el formato usado durante el ajuste de instrucciones y es importante para elicitar un comportamiento de seguimiento coherente y contextual.

### Cargar el Modelo y el Tokenizer

Para interactuar con el modelo de esta manera, debes comenzar cargando el modelo y el tokenizer como en la Guía de Inicio Rápido anterior. Luego sigue los siguientes pasos:

### Definir una Función Helper de Chat

```python
def chat(messages, max_new_tokens=200):
    # Convierte la lista de mensajes en un prompt estilo ChatML
    # aumenta max_new_tokens si trabajas con entradas más largas (nivel párrafo/documento)
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    
    # Tokeniza el prompt
    inputs = tokenizer.encode(prompt, return_tensors="pt", add_special_tokens=False).to(model.device)
    input_len = inputs.shape[1]
    
    # Genera una respuesta usando decodificación greedy y token de parada específico de ChatML
    outputs = model.generate(
        input_ids=inputs,
        max_new_tokens=max_new_tokens,
        pad_token_id=tokenizer.eos_token_id,
        eos_token_id=tokenizer.convert_tokens_to_ids("<|im_end|>")
    )
    
    # Devuelve solo el texto recién generado, omitiendo tokens especiales
    return tokenizer.decode(outputs[0, input_len:], skip_special_tokens=True)
```

### Ejemplo: Traducciones Alternativas

```python
# Primer mensaje del usuario: Solicitar una traducción al catalán
messages = [
    {
        "role": "user",
        "content": 'Given the English sentence "Nothing is achieved without effort.", generate a translation in Catalan.'
    }
]

# Generar e imprimir la primera respuesta
response_1 = chat(messages)
print("Response 1:", response_1)
# Response 1: Translation in Catalan as listed:
# Res s'aconsegueix sense esforç.

# Añadir la primera respuesta del modelo al historial de chat
messages.append({"role": "assistant", "content": response_1})

# Añadir un segundo mensaje del usuario solicitando una traducción alternativa
messages.append({
    "role": "user",
    "content": 'That was a useful translation. For a broader understanding, please provide one additional translation of the English phrase "Nothing is achieved without effort." into Catalan.'
})

# Generar e imprimir la segunda respuesta
response_2 = chat(messages)
print("Response 2:", response_2)
# Response 2: Res s'aconsegueix sense treballar.
```

### Notas sobre interacciones multi-turno

Esta estructura puede extenderse a más de dos turnos continuando añadiendo objetos `{"role": "assistant", "content": ...}` y `{"role": "user", "content": ...}` a la lista de mensajes. También puede usarse con otras tareas - por ejemplo, en Evaluación de Traducción Automática, podrías seguir una solicitud de la mejor traducción con una solicitud de la peor.

## Estrategias de Decodificación

Hay diferentes estrategias de decodificación que pueden usarse con los modelos SalamandraTA para generar traducciones. La estrategia que elijas puede afectar la fluidez, precisión y consistencia de las traducciones u otras salidas de tareas.

Para la mayoría de casos de uso, recomendamos una de las siguientes:

### Decodificación Greedy (Por Defecto)

La decodificación greedy selecciona el siguiente token más probable en cada paso, produciendo salidas rápidas y predecibles. Es adecuada para la mayoría de tareas de traducción donde la consistencia y velocidad son prioridades.

**Usar cuando:** Quieres traducciones de inferencia rápidas y confiables — ideal para la mayoría de tareas de MT y post-edición.

```python
outputs = model.generate(
    input_ids=inputs.to(model.device),
    max_new_tokens=200,
    num_beams=1,  # 1 = decodificación greedy
    pad_token_id=tokenizer.eos_token_id
)
```

### Beam Search

Beam search mantiene múltiples secuencias candidatas en cada paso y elige la secuencia más probable en general después de considerar estas opciones. Esto puede mejorar la fluidez y calidad, especialmente para texto más largo o complejo, pero requiere más recursos computacionales y puede a veces producir tokens de finalización menos consistentes.

**Usar cuando:** Quieres salidas más pulidas, estás trabajando con párrafos más largos, o estás post-seleccionando entre alternativas.

```python
outputs = model.generate(
    input_ids=inputs.to(model.device),
    max_new_tokens=200,
    num_beams=5,  # > 1 = beam search, generalmente 5 beams es un buen balance entre calidad y costo
    pad_token_id=tokenizer.eos_token_id
)
```

### Nota Importante sobre Tokens de Finalización

Los modelos SalamandraTA ajustados por instrucciones están diseñados para finalizar salidas con `<|im_end|>`.

La decodificación greedy respeta esto confiablemente. Beam search a veces prefiere `</s>`, dependiendo de cuán probable sea `<|im_end|>` bajo las hipótesis del beam.

Si es necesario, establece lo siguiente para asegurar un comportamiento de parada limpio:

```python
stop_sequence = '<|im_end|>'
eos_tokens = [
    tokenizer.eos_token_id,
    tokenizer.convert_tokens_to_ids(stop_sequence),
]
```

En la generación, puede aplicarse como en el siguiente:

```python
outputs = model.generate(
    input_ids=inputs.to(model.device),
    max_new_tokens=4000,
    early_stopping=True,
    eos_token_id=eos_tokens,
    pad_token_id=tokenizer.eos_token_id,
    num_beams=5
)
```

### Diverse Beam Search

Diverse beam search es una variación de beam search que fomenta la variedad entre los candidatos de traducción. En lugar de solo encontrar las secuencias más probables, busca encontrar un conjunto de secuencias de alta probabilidad que también sean diferentes entre sí. Esto se logra penalizando hipótesis que son demasiado similares a otras ya en el beam.

**Usar cuando:** Quieres generar múltiples opciones de traducción distintas para una única oración fuente. Esto es útil para tareas como proporcionar traducciones alternativas o para crear un conjunto más rico de candidatos para un paso posterior de decodificación consciente de calidad.

```python
# Usa num_beam_groups y diversity_penalty para habilitar diverse beam search
# Esto generará 5 beams, divididos en 5 grupos (así que cada grupo es independiente)
# La penalidad de diversidad desalienta que los beams dentro de un grupo sean demasiado similares.
outputs = model.generate(
    input_ids=inputs.to(model.device),
    max_new_tokens=200,
    num_beams=5,
    num_beam_groups=5,
    diversity_penalty=1.0,
    pad_token_id=tokenizer.eos_token_id
)
```

## Estrategias de Decodificación Conscientes de Calidad

Mientras que la decodificación greedy y beam search son poderosas, priorizan la probabilidad estadística (lo que el modelo piensa que es la traducción más probable) sobre la calidad real de la traducción. Esto puede a veces llevar a la "maldición del beam search", donde las traducciones con la mayor probabilidad no son en realidad las mejores en términos de calidad, resultando a veces en texto no natural. Las estrategias conscientes de calidad abordan esto incorporando un sentido más directo de "bondad" en el proceso de decodificación. Para usar estrategias de decodificación conscientes de calidad con SalamandraTA necesitaremos instalar dos bibliotecas; `mbrs` y `comet`.

```bash
pip install mbrs
pip install unbabel-comet
```

Luego, necesitaremos un conjunto de traducciones candidatas, usaremos diverse beam search para generar un conjunto de hipótesis. El beam search tradicional a menudo genera secuencias muy similares a través de diferentes beams. Diverse beam search aborda esto penalizando beams que generan tokens ya elegidos por otros beams en el mismo paso de tiempo.

```python
sentence = "Ayer se fue, tomó sus cosas y se puso a navegar"
text = (
    f"Translate the following text from {source} into {target}.\n"
    f"{source}: {sentence}\n"
    f"{target}:"
)

message = [{"role": "user", "content": text}]
prompt = tokenizer.apply_chat_template(message, tokenize=False, add_generation_prompt=True)

inputs = tokenizer.encode(prompt, add_special_tokens=False, return_tensors="pt")
input_length = inputs.shape[1]  # Usado para recortar la porción del prompt de la salida

eos_tokens = [tokenizer.eos_token_id, tokenizer.convert_tokens_to_ids("<|im_end|>")]

# Generaremos 20 traducciones candidatas
num_hypotheses = 20

outputs = model.generate(
    input_ids=inputs.to(model.device),
    max_new_tokens=200,
    num_beams=num_hypotheses,
    num_return_sequences=num_hypotheses,
    num_beam_groups=5,
    diversity_penalty=1.0,
    pad_token_id=tokenizer.eos_token_id,
    eos_token_id=tokenizer.convert_tokens_to_ids("<|im_end|>")
)

# Decodificar todas las hipótesis en una lista de strings
hypotheses = [
    tokenizer.decode(output[input_length:], skip_special_tokens=True).strip().replace('\n', '')
    for output in outputs
]
```

### Tuned Re-ranking

Tuned re-ranking es un proceso de dos pasos:

1. **Generación:** Primero, usa un método de decodificación como beam search o diverse beam search para generar una lista de múltiples candidatos de traducción (una "lista N-best").

2. **Re-ranking:** Luego, usa un segundo modelo especializado—un "re-ranker"—para puntuar cada candidato en la lista N-best. Este re-ranker es a menudo un modelo de Estimación de Calidad (QE) entrenado específicamente para predecir la calidad de una traducción sin necesitar una referencia humana. La traducción con la puntuación de calidad más alta se selecciona entonces como la salida final.

**Usar cuando:** Quieres lograr la mayor calidad de traducción posible. Al usar un modelo QE dedicado para la selección final, a menudo puedes encontrar una mejor traducción en la lista N-best de lo que el modelo principal habría elegido basándose solo en la probabilidad.

```python
from mbrs.metrics import MetricCOMETkiwi
from mbrs.decoders import DecoderRerank

# 1. Inicializa la métrica de calidad que quieres usar para re-ranking.
# Aquí, usamos COMET-kiwi, una métrica de última generación para estimación de calidad
metric_cfg = MetricCOMETkiwi.Config(model="Unbabel/wmt22-cometkiwi-da")
metric = MetricCOMETkiwi(metric_cfg)

# 2. Inicializa el decodificador de re-rank.
decoder_cfg = DecoderRerank.Config()
decoder = DecoderRerank(decoder_cfg, metric)

# 3. ¡Decodifica! El método 'decode' toma tu lista de hipótesis
# y las re-rankea según la métrica seleccionada
result = decoder.decode(hypotheses, source=sentence, nbest=1)
best_hyp = result.sentence[0]

# Imprime el resultado seleccionado por re-ranking de Comet-kiwi
print(f"Selected sentence: {best_hyp}")
```

### Decodificación Minimum Bayes Risk (MBR)

La decodificación Minimum Bayes Risk (MBR) es una alternativa poderosa que optimiza directamente para la calidad de salida. En lugar de seleccionar la única hipótesis más probable (como en beam search estándar), MBR selecciona la hipótesis que es más similar, en promedio, a todas las demás hipótesis plausibles.

La idea central es encontrar la traducción candidata que tenga la mayor utilidad esperada (es decir, la puntuación de calidad promedio más alta) cuando se compara con un conjunto de otras traducciones potenciales de alta calidad, conocidas como "pseudo-referencias". Este enfoque es efectivo para evitar los problemas comunes de la decodificación estándar al favorecer el consenso y la calidad sobre la probabilidad bruta.

```python
from mbrs.metrics import MetricCOMET
from mbrs.decoders import DecoderMBR

# 1. Inicializa la métrica de calidad que quieres usar para la función de utilidad.
# Aquí, usamos COMET, una métrica de última generación para estimación de calidad
# de traducción basada en redes neuronales
metric_cfg = MetricCOMET.Config(model="Unbabel/wmt22-comet-da")
metric = MetricCOMET(metric_cfg)

# 2. Inicializa el decodificador MBR.
decoder_cfg = DecoderMBR.Config()
decoder = DecoderMBR(decoder_cfg, metric)

# 3. ¡Decodifica! El método 'decode' toma tu lista de hipótesis y también las usa
# como pseudo-referencias para calcular las puntuaciones de utilidad esperada.
result = decoder.decode(hypotheses, hypotheses, source=sentence, nbest=1)
best_hyp = result.sentence[0]

# Imprime el resultado seleccionado por decodificación MBR
print(f"Selected sentence: {best_hyp}")
```