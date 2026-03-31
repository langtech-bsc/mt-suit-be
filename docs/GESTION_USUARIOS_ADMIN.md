# Gestión de Usuarios - Alta, Baja y Control de Acceso (Admin)

## Índice
1. [Descripción General](#descripción-general)
2. [Requisitos Previos](#requisitos-previos)
3. [Alta de Usuarios](#alta-de-usuarios)
4. [Baja de Usuarios](#baja-de-usuarios)
5. [Modificación de Usuarios](#modificación-de-usuarios)
6. [Control de Acceso](#control-de-acceso)
7. [Gestión de Roles](#gestión-de-roles)
8. [Gestión de Permisos](#gestión-de-permisos)
9. [Casos de Uso Administrativos](#casos-de-uso-administrativos)
10. [Auditoría y Monitoreo](#auditoría-y-monitoreo)
11. [Buenas Prácticas](#buenas-prácticas)
12. [Troubleshooting](#troubleshooting)

---

## Descripción General

Esta documentación está dirigida a **administradores del sistema** que necesitan gestionar usuarios, controlar accesos y mantener la seguridad del módulo de traducción.

### Responsabilidades del Administrador

Como administrador del sistema, tienes la capacidad de:

✅ Crear, modificar y eliminar usuarios
✅ Asignar y revocar roles a usuarios
✅ Activar/desactivar cuentas de usuario
✅ Gestionar roles y permisos del sistema
✅ Controlar el acceso a recursos específicos
✅ Monitorear la actividad de usuarios
✅ Configurar roles por defecto para nuevos usuarios

### Niveles de Privilegios Administrativos

| Nivel | Descripción | Capacidades |
|-------|-------------|-------------|
| **Superusuario** | Acceso total al sistema | Todas las operaciones sin restricciones |
| **Admin con permisos** | Administrador limitado | Solo acciones para las que tiene permisos específicos |
| **Usuario estándar** | Sin privilegios admin | Solo gestión de su propia cuenta |

---

## Requisitos Previos

### 1. Obtener Token de Superusuario

Para realizar operaciones administrativas, necesitas autenticarte como **superusuario**:

```bash
# Login como superusuario
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin_password"
  }'
```

**Respuesta:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**IMPORTANTE:** Guarda el token de acceso para usarlo en todas las operaciones administrativas.

### 2. Verificar Privilegios

```bash
# Verificar tu cuenta actual
curl -X GET http://localhost:8000/api/users/me \
  -H "Authorization: Bearer <tu_token>"
```

**Verificar que:**
- `is_superuser: true` → Acceso total
- `is_active: true` → Cuenta activa
- `roles` contiene roles administrativos necesarios

### 3. Variables de Entorno

```bash
# Para todas las llamadas siguientes, define:
export ADMIN_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
export API_BASE="http://localhost:8000/api"

# Uso en curl:
curl -H "Authorization: Bearer $ADMIN_TOKEN" $API_BASE/users
```

---

## Alta de Usuarios

### Método 1: Registro Público (Auto-registro)

Los usuarios pueden registrarse automáticamente a través del endpoint público:

**Endpoint:** `POST /api/users`

```bash
curl -X POST $API_BASE/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "nuevo_usuario",
    "email": "usuario@example.com",
    "password": "ContraseñaSegura123"
  }'
```

**Características:**
- ✅ No requiere autenticación
- ✅ Asigna automáticamente roles por defecto (`is_default: true`)
- ✅ El usuario queda activo inmediatamente (`is_active: true`)
- ❌ No puede crear superusuarios
- ❌ No permite asignar roles específicos en creación

**Respuesta:** 201 Created
```json
{
  "id": 15,
  "username": "nuevo_usuario",
  "email": "usuario@example.com",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2025-01-15T16:45:00",
  "updated_at": "2025-01-15T16:45:00",
  "roles": [
    {
      "id": 2,
      "name": "translator",
      "description": "Usuario traductor estándar",
      "is_default": true,
      "permissions": [...]
    }
  ]
}
```

### Método 2: Creación Administrativa (Recomendado)

Como administrador, puedes crear usuarios y luego asignarles roles específicos:

#### Paso 1: Crear el Usuario

```bash
curl -X POST $API_BASE/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "editor_senior",
    "email": "editor@company.com",
    "password": "TempPassword123"
  }'
```

#### Paso 2: Asignar Roles Específicos

```bash
# Asignar rol de "editor" al nuevo usuario (ID 15)
curl -X POST $API_BASE/roles/roles/assign \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 15,
    "role_id": 3
  }'
```

#### Paso 3 (Opcional): Configurar como Superusuario

Para convertir un usuario en superusuario, usa el endpoint de actualización:

```bash
curl -X PUT $API_BASE/users/15 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "is_superuser": true
  }'
```

⚠️ **ADVERTENCIA:** Solo otorga privilegios de superusuario a personas de máxima confianza.

### Validaciones en la Creación

| Campo | Validación | Ejemplo Válido | Ejemplo Inválido |
|-------|------------|----------------|------------------|
| **username** | 3-50 caracteres, único | `juan_translator` | `ab` (muy corto) |
| **email** | Formato email válido, único | `juan@example.com` | `juan@` (inválido) |
| **password** | 8-100 caracteres, máx 72 bytes UTF-8 | `SecurePass123` | `1234567` (muy corto) |

**Errores Comunes:**

```json
// 400 Bad Request - Username ya existe
{
  "detail": "Username already registered"
}

// 400 Bad Request - Email ya existe
{
  "detail": "Email already registered"
}

// 422 Unprocessable Entity - Validación fallida
{
  "detail": [
    {
      "loc": ["body", "password"],
      "msg": "ensure this value has at least 8 characters",
      "type": "value_error.any_str.min_length"
    }
  ]
}
```

### Creación Masiva de Usuarios

Para crear múltiples usuarios, puedes usar un script:

```bash
#!/bin/bash
# create_users.sh

USERS=(
  "translator1:translator1@company.com:Pass123456"
  "translator2:translator2@company.com:Pass123456"
  "editor1:editor@company.com:Pass123456"
)

for user_data in "${USERS[@]}"; do
  IFS=':' read -r username email password <<< "$user_data"

  echo "Creating user: $username"
  curl -X POST $API_BASE/users \
    -H "Content-Type: application/json" \
    -d "{
      \"username\": \"$username\",
      \"email\": \"$email\",
      \"password\": \"$password\"
    }"

  echo ""
done
```

---

## Baja de Usuarios

### Opciones de Baja

Existen dos estrategias para dar de baja a un usuario:

#### 1. Desactivación (Soft Delete) - **RECOMENDADO**

**Ventajas:**
- ✅ Preserva el historial del usuario
- ✅ Previene inicio de sesión sin eliminar datos
- ✅ Reversible (se puede reactivar)
- ✅ Mantiene integridad referencial

**Desactivar usuario:**

```bash
curl -X PUT $API_BASE/users/15 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "is_active": false
  }'
```

**Efecto:**
- El usuario **no puede iniciar sesión**
- Los tokens JWT existentes son válidos hasta su expiración
- Los registros del usuario (traducciones, etc.) se mantienen
- Aparece en listados pero marcado como inactivo

**Reactivar usuario:**

```bash
curl -X PUT $API_BASE/users/15 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "is_active": true
  }'
```

#### 2. Eliminación Permanente (Hard Delete)

**Ubicación:** [`app/api/users.py:190-211`](app/api/users.py#L190-L211)

**Advertencias:**
- ⚠️ **IRREVERSIBLE** - No se puede deshacer
- ⚠️ Puede romper relaciones con otros datos
- ⚠️ Verifica las relaciones de CASCADE antes de eliminar

**Endpoint:** `DELETE /api/users/{user_id}`

```bash
curl -X DELETE $API_BASE/users/15 \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Respuesta:** 204 No Content (sin cuerpo de respuesta)

**Errores:**
```json
// 404 Not Found
{
  "detail": "User not found"
}

// 403 Forbidden
{
  "detail": "The user doesn't have enough privileges"
}
```

### Verificación Antes de Eliminar

**Script de verificación:**

```bash
#!/bin/bash
# check_user_before_delete.sh

USER_ID=$1

echo "=== Información del Usuario ==="
curl -s $API_BASE/users/$USER_ID \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

echo ""
echo "=== Roles del Usuario ==="
curl -s $API_BASE/roles/users/$USER_ID/roles \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

echo ""
echo "=== Traducciones del Usuario ==="
curl -s "$API_BASE/translations?user_id=$USER_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '. | length'

echo ""
read -p "¿Deseas continuar con la eliminación? (yes/no): " confirm

if [ "$confirm" = "yes" ]; then
  curl -X DELETE $API_BASE/users/$USER_ID \
    -H "Authorization: Bearer $ADMIN_TOKEN"
  echo "Usuario eliminado"
else
  echo "Operación cancelada"
fi
```

### Eliminación en Cascada

**Ubicación:** [`app/models/role.py:22-23`](app/models/role.py#L22-L23)

Las tablas de asociación están configuradas con `ondelete="CASCADE"`:

```python
# En user_roles
Column("user_id", BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
Column("role_id", BigInteger, ForeignKey("roles.id", ondelete="CASCADE"))
```

**Comportamiento al eliminar usuario:**
1. Se eliminan automáticamente las asignaciones de roles (`user_roles`)
2. Las traducciones del usuario se mantienen (verifica tu configuración específica)
3. Los roles no se eliminan (solo las asociaciones)

---

## Modificación de Usuarios

### Actualizar Información de Usuario

**Ubicación:** [`app/api/users.py:150-188`](app/api/users.py#L150-L188)

**Endpoint:** `PUT /api/users/{user_id}`

### Campos Modificables

```bash
curl -X PUT $API_BASE/users/15 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "nuevo_username",
    "email": "nuevo_email@example.com",
    "password": "NuevaContraseña123",
    "is_active": true
  }'
```

**Notas:**
- Todos los campos son **opcionales**
- Solo envía los campos que deseas modificar
- Las validaciones se aplican igual que en la creación

### Casos de Uso Comunes

#### 1. Cambiar Contraseña de Usuario

```bash
curl -X PUT $API_BASE/users/15 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "password": "NuevaContraseñaTemporal123"
  }'
```

**Proceso recomendado:**
1. Admin genera contraseña temporal
2. Admin actualiza la contraseña del usuario
3. Admin notifica al usuario (email, etc.)
4. Usuario cambia la contraseña en su primer login

#### 2. Actualizar Email de Usuario

```bash
curl -X PUT $API_BASE/users/15 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "nuevo_email@company.com"
  }'
```

**Validación:**
- El nuevo email no debe estar en uso por otro usuario
- Debe ser un formato de email válido

#### 3. Suspender Temporalmente a un Usuario

```bash
curl -X PUT $API_BASE/users/15 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "is_active": false
  }'
```

### Modificación Masiva

Script para actualizar múltiples usuarios:

```bash
#!/bin/bash
# bulk_update_users.sh

# Desactivar usuarios específicos
USER_IDS=(15 16 17 18)

for user_id in "${USER_IDS[@]}"; do
  echo "Desactivando usuario ID: $user_id"
  curl -X PUT $API_BASE/users/$user_id \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"is_active": false}'
  echo ""
done
```

---

## Control de Acceso

### Conceptos Clave

El control de acceso se basa en tres pilares:

```
┌─────────────────────────────────────────┐
│           USUARIO                       │
│  - is_active: true/false                │
│  - is_superuser: true/false             │
└──────────────┬──────────────────────────┘
               │
               │ tiene múltiples
               ▼
┌─────────────────────────────────────────┐
│           ROLES                         │
│  - admin, editor, translator, etc.      │
└──────────────┬──────────────────────────┘
               │
               │ agrupan múltiples
               ▼
┌─────────────────────────────────────────┐
│         PERMISOS                        │
│  - users:read, translations:create,etc. │
└─────────────────────────────────────────┘
```

### Verificación de Acceso

#### Flujo de Autorización

```
Usuario solicita recurso
       │
       ▼
┌──────────────────────┐
│ ¿is_active = true?   │ ──No──> HTTP 400 Bad Request
└──────┬───────────────┘
       │ Sí
       ▼
┌──────────────────────┐
│ ¿is_superuser?       │ ──Sí──> ✅ ACCESO CONCEDIDO
└──────┬───────────────┘
       │ No
       ▼
┌──────────────────────┐
│ ¿Tiene el permiso?   │ ──Sí──> ✅ ACCESO CONCEDIDO
└──────┬───────────────┘
       │ No
       ▼
  HTTP 403 Forbidden
  ❌ ACCESO DENEGADO
```

### Listar Usuarios con sus Roles

```bash
# Obtener todos los usuarios
curl -X GET "$API_BASE/users?skip=0&limit=100" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Ver roles de un usuario específico
curl -X GET $API_BASE/roles/users/15/roles \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq
```

**Respuesta:**
```json
[
  {
    "id": 2,
    "name": "translator",
    "description": "Usuario traductor estándar",
    "is_default": true,
    "created_at": "2025-01-15T09:00:00",
    "updated_at": "2025-01-15T09:00:00",
    "permissions": [
      {
        "id": 5,
        "name": "translations:create",
        "description": "Crear traducciones",
        "resource": "translations",
        "action": "create",
        "created_at": "2025-01-15T09:00:00"
      },
      {
        "id": 6,
        "name": "translations:read",
        "description": "Ver traducciones",
        "resource": "translations",
        "action": "read",
        "created_at": "2025-01-15T09:00:00"
      }
    ]
  }
]
```

### Asignar Roles a Usuarios

**Ubicación:** [`app/api/roles.py:167-182`](app/api/roles.py#L167-L182)

**Endpoint:** `POST /api/roles/roles/assign`

```bash
# Asignar rol "editor" (ID: 3) al usuario (ID: 15)
curl -X POST $API_BASE/roles/roles/assign \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 15,
    "role_id": 3
  }'
```

**Respuesta:** 200 OK
```json
{
  "message": "Role assigned successfully",
  "user_id": 15
}
```

**Características:**
- Un usuario puede tener **múltiples roles simultáneamente**
- Los permisos se **acumulan** de todos los roles
- Si el usuario ya tiene el rol, no ocurre duplicación

### Revocar Roles de Usuarios

**Ubicación:** [`app/api/roles.py:184-199`](app/api/roles.py#L184-L199)

**Endpoint:** `POST /api/roles/roles/remove`

```bash
# Remover rol "translator" (ID: 2) del usuario (ID: 15)
curl -X POST $API_BASE/roles/roles/remove \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 15,
    "role_id": 2
  }'
```

**Respuesta:** 200 OK
```json
{
  "message": "Role removed successfully",
  "user_id": 15
}
```

### Verificar Permisos de un Usuario

Para verificar qué puede hacer un usuario:

```bash
# 1. Obtener usuario con sus roles
curl -X GET $API_BASE/users/15 \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# 2. Ver roles del usuario
curl -X GET $API_BASE/roles/users/15/roles \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# 3. Ver permisos específicos de cada rol
curl -X GET $API_BASE/roles/roles/3 \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.permissions'
```

### Script de Auditoría de Permisos

```bash
#!/bin/bash
# audit_user_permissions.sh

USER_ID=$1

echo "=== Auditoría de Permisos - Usuario ID: $USER_ID ==="
echo ""

# Info del usuario
echo "📋 Información del Usuario:"
USER_INFO=$(curl -s $API_BASE/users/$USER_ID \
  -H "Authorization: Bearer $ADMIN_TOKEN")

echo "$USER_INFO" | jq '{
  id,
  username,
  email,
  is_active,
  is_superuser
}'

echo ""

# Superusuario check
IS_SUPERUSER=$(echo "$USER_INFO" | jq -r '.is_superuser')
if [ "$IS_SUPERUSER" = "true" ]; then
  echo "⚠️  SUPERUSUARIO: Este usuario tiene TODOS los permisos"
  exit 0
fi

# Roles
echo "🎭 Roles Asignados:"
ROLES=$(curl -s $API_BASE/roles/users/$USER_ID/roles \
  -H "Authorization: Bearer $ADMIN_TOKEN")

echo "$ROLES" | jq -r '.[] | "  - \(.name): \(.description)"'

echo ""
echo "🔑 Permisos Consolidados:"
echo "$ROLES" | jq -r '.[] | .permissions[] | "  - \(.name) (\(.resource):\(.action))"' | sort -u

echo ""
echo "✅ Auditoría completada"
```

---

## Gestión de Roles

### Listar Todos los Roles

**Endpoint:** `GET /api/roles/roles`

```bash
curl -X GET "$API_BASE/roles/roles?skip=0&limit=100" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq
```

**Respuesta:**
```json
[
  {
    "id": 1,
    "name": "admin",
    "description": "Administrador del sistema",
    "is_default": false,
    "created_at": "2025-01-15T09:00:00",
    "updated_at": "2025-01-15T09:00:00",
    "permissions": [...]
  },
  {
    "id": 2,
    "name": "translator",
    "description": "Usuario traductor estándar",
    "is_default": true,
    "created_at": "2025-01-15T09:00:00",
    "updated_at": "2025-01-15T09:00:00",
    "permissions": [...]
  }
]
```

### Crear un Nuevo Rol

**Ubicación:** [`app/api/roles.py:122-138`](app/api/roles.py#L122-L138)

**Endpoint:** `POST /api/roles/roles`

```bash
curl -X POST $API_BASE/roles/roles \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "reviewer",
    "description": "Revisor de traducciones",
    "is_default": false,
    "permission_ids": [5, 6, 7, 10]
  }'
```

**Parámetros:**
- `name` (requerido): Nombre único del rol
- `description` (opcional): Descripción del rol
- `is_default` (opcional, default: false): Si se asigna automáticamente a nuevos usuarios
- `permission_ids` (opcional): Array de IDs de permisos a asignar

**Respuesta:** 201 Created
```json
{
  "id": 5,
  "name": "reviewer",
  "description": "Revisor de traducciones",
  "is_default": false,
  "created_at": "2025-01-15T17:00:00",
  "updated_at": "2025-01-15T17:00:00",
  "permissions": [
    {
      "id": 5,
      "name": "translations:create",
      ...
    },
    ...
  ]
}
```

### Actualizar un Rol

**Ubicación:** [`app/api/roles.py:140-152`](app/api/roles.py#L140-L152)

**Endpoint:** `PUT /api/roles/roles/{role_id}`

```bash
curl -X PUT $API_BASE/roles/roles/5 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Revisor senior de traducciones",
    "permission_ids": [5, 6, 7, 10, 11]
  }'
```

**Nota:** Al actualizar `permission_ids`, **reemplaza completamente** los permisos del rol.

### Eliminar un Rol

**Ubicación:** [`app/api/roles.py:154-164`](app/api/roles.py#L154-L164)

**Endpoint:** `DELETE /api/roles/roles/{role_id}`

```bash
curl -X DELETE $API_BASE/roles/roles/5 \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Respuesta:** 204 No Content

**Comportamiento CASCADE:**
- Se eliminan las asignaciones del rol a usuarios (`user_roles`)
- Los usuarios que tenían este rol lo pierden
- Los permisos asociados **NO** se eliminan (solo la asociación)

### Configurar Rol por Defecto

Un rol con `is_default: true` se asigna automáticamente a todos los nuevos usuarios durante el registro.

**Mejores prácticas:**
- Solo un rol debería ser `is_default: true` (generalmente)
- Debe tener permisos básicos mínimos
- Ejemplo: rol "translator" con permisos de lectura y creación de traducciones

```bash
# Configurar "translator" como rol por defecto
curl -X PUT $API_BASE/roles/roles/2 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "is_default": true
  }'
```

### Ver Usuarios con un Rol Específico

**Ubicación:** [`app/api/roles.py:219-230`](app/api/roles.py#L219-L230)

**Endpoint:** `GET /api/roles/roles/{role_id}/users`

```bash
# Ver todos los usuarios con el rol "translator" (ID: 2)
curl -X GET "$API_BASE/roles/roles/2/users?skip=0&limit=100" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq
```

**Uso:**
- Auditar quién tiene acceso a qué
- Identificar usuarios con roles específicos
- Planificar migraciones de roles

---

## Gestión de Permisos

### Estructura de Permisos

**Convención:** `<resource>:<action>`

**Recursos comunes:**
- `users`: Gestión de usuarios
- `roles`: Gestión de roles
- `permissions`: Gestión de permisos
- `translations`: Gestión de traducciones

**Acciones comunes:**
- `create`: Crear recursos
- `read`: Leer/ver recursos
- `update`: Actualizar recursos
- `delete`: Eliminar recursos
- `approve`: Aprobar (específico del dominio)
- `export`: Exportar (específico del dominio)

### Listar Permisos

**Endpoint:** `GET /api/roles/permissions`

```bash
curl -X GET "$API_BASE/roles/permissions?skip=0&limit=100" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq
```

**Respuesta:**
```json
[
  {
    "id": 1,
    "name": "users:read",
    "description": "Ver información de usuarios",
    "resource": "users",
    "action": "read",
    "created_at": "2025-01-15T09:00:00"
  },
  {
    "id": 2,
    "name": "users:create",
    "description": "Crear nuevos usuarios",
    "resource": "users",
    "action": "create",
    "created_at": "2025-01-15T09:00:00"
  },
  ...
]
```

### Crear Permiso

**Ubicación:** [`app/api/roles.py:52-68`](app/api/roles.py#L52-L68)

**Endpoint:** `POST /api/roles/permissions`

```bash
curl -X POST $API_BASE/roles/permissions \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "translations:approve",
    "description": "Aprobar traducciones para publicación",
    "resource": "translations",
    "action": "approve"
  }'
```

**Respuesta:** 201 Created
```json
{
  "id": 25,
  "name": "translations:approve",
  "description": "Aprobar traducciones para publicación",
  "resource": "translations",
  "action": "approve",
  "created_at": "2025-01-15T17:30:00"
}
```

### Actualizar Permiso

**Ubicación:** [`app/api/roles.py:70-82`](app/api/roles.py#L70-L82)

**Endpoint:** `PUT /api/roles/permissions/{permission_id}`

```bash
curl -X PUT $API_BASE/roles/permissions/25 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Aprobar y publicar traducciones finalizadas"
  }'
```

### Eliminar Permiso

**Ubicación:** [`app/api/roles.py:84-94`](app/api/roles.py#L84-L94)

**Endpoint:** `DELETE /api/roles/permissions/{permission_id}`

```bash
curl -X DELETE $API_BASE/roles/permissions/25 \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Respuesta:** 204 No Content

**Comportamiento CASCADE:**
- Se eliminan las asociaciones del permiso con roles (`role_permissions`)
- Los roles pierden este permiso automáticamente
- Los usuarios con esos roles pierden el permiso indirectamente

### Permisos Estándar Recomendados

#### Gestión de Usuarios
```json
[
  {"name": "users:create", "resource": "users", "action": "create"},
  {"name": "users:read", "resource": "users", "action": "read"},
  {"name": "users:update", "resource": "users", "action": "update"},
  {"name": "users:delete", "resource": "users", "action": "delete"}
]
```

#### Gestión de Roles
```json
[
  {"name": "roles:create", "resource": "roles", "action": "create"},
  {"name": "roles:read", "resource": "roles", "action": "read"},
  {"name": "roles:update", "resource": "roles", "action": "update"},
  {"name": "roles:delete", "resource": "roles", "action": "delete"}
]
```

#### Gestión de Permisos
```json
[
  {"name": "permissions:create", "resource": "permissions", "action": "create"},
  {"name": "permissions:read", "resource": "permissions", "action": "read"},
  {"name": "permissions:update", "resource": "permissions", "action": "update"},
  {"name": "permissions:delete", "resource": "permissions", "action": "delete"}
]
```

#### Gestión de Traducciones
```json
[
  {"name": "translations:create", "resource": "translations", "action": "create"},
  {"name": "translations:read", "resource": "translations", "action": "read"},
  {"name": "translations:update", "resource": "translations", "action": "update"},
  {"name": "translations:delete", "resource": "translations", "action": "delete"},
  {"name": "translations:approve", "resource": "translations", "action": "approve"},
  {"name": "translations:export", "resource": "translations", "action": "export"}
]
```

### Script para Crear Permisos Estándar

```bash
#!/bin/bash
# create_standard_permissions.sh

PERMISSIONS=(
  "users:create:users:create:Crear usuarios"
  "users:read:users:read:Ver usuarios"
  "users:update:users:update:Actualizar usuarios"
  "users:delete:users:delete:Eliminar usuarios"
  "roles:create:roles:create:Crear roles"
  "roles:read:roles:read:Ver roles"
  "roles:update:roles:update:Actualizar roles"
  "roles:delete:roles:delete:Eliminar roles"
  "translations:create:translations:create:Crear traducciones"
  "translations:read:translations:read:Ver traducciones"
  "translations:update:translations:update:Actualizar traducciones"
  "translations:delete:translations:delete:Eliminar traducciones"
)

for perm_data in "${PERMISSIONS[@]}"; do
  IFS=':' read -r name resource action description <<< "$perm_data"

  echo "Creating permission: $name"
  curl -X POST $API_BASE/roles/permissions \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"name\": \"$name\",
      \"description\": \"$description\",
      \"resource\": \"$resource\",
      \"action\": \"$action\"
    }"
  echo ""
done
```

---

## Casos de Uso Administrativos

### Caso 1: Onboarding de Nuevo Empleado

**Escenario:** Un nuevo traductor se une al equipo.

**Pasos:**

```bash
# 1. Crear usuario
curl -X POST $API_BASE/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "maria_garcia",
    "email": "maria.garcia@company.com",
    "password": "TempPassword123"
  }'
# Respuesta: Usuario creado con ID 20

# 2. Asignar rol de traductor (si no es por defecto)
curl -X POST $API_BASE/roles/roles/assign \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 20,
    "role_id": 2
  }'

# 3. Verificar configuración
curl -X GET $API_BASE/roles/users/20/roles \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# 4. Notificar al usuario (fuera del sistema)
# Email: "Tu cuenta ha sido creada. Username: maria_garcia, Password temporal: TempPassword123"
```

### Caso 2: Promoción a Editor Senior

**Escenario:** Un traductor es promovido a editor senior con permisos adicionales.

```bash
# 1. Ver roles actuales
curl -X GET $API_BASE/roles/users/20/roles \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# 2. Asignar rol de editor (ID: 3)
curl -X POST $API_BASE/roles/roles/assign \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 20,
    "role_id": 3
  }'

# 3. Mantener rol de translator o removerlo (según política)
# Opción A: Mantener ambos roles (acumulación de permisos)
# Opción B: Remover rol anterior
curl -X POST $API_BASE/roles/roles/remove \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 20,
    "role_id": 2
  }'

# 4. Verificar nuevos permisos
curl -X GET $API_BASE/roles/users/20/roles \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq
```

### Caso 3: Suspensión Temporal de Usuario

**Escenario:** Un usuario incumple políticas y debe ser suspendido temporalmente.

```bash
# 1. Documentar razón de suspensión (sistema externo de auditoría)

# 2. Desactivar usuario
curl -X PUT $API_BASE/users/20 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "is_active": false
  }'

# 3. Verificar estado
curl -X GET $API_BASE/users/20 \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.is_active'
# Respuesta: false

# 4. Después del período de suspensión, reactivar
curl -X PUT $API_BASE/users/20 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "is_active": true
  }'
```

### Caso 4: Offboarding de Empleado

**Escenario:** Un empleado deja la empresa.

```bash
# 1. Verificar actividad reciente del usuario
curl -X GET $API_BASE/users/20 \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# 2. Opción A: Desactivar (RECOMENDADO - preserva historial)
curl -X PUT $API_BASE/users/20 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "is_active": false
  }'

# 3. Opción B: Eliminar (solo si es necesario)
# curl -X DELETE $API_BASE/users/20 \
#   -H "Authorization: Bearer $ADMIN_TOKEN"

# 4. Reasignar traducciones en progreso (lógica de negocio específica)
```

### Caso 5: Creación de Rol Personalizado

**Escenario:** Crear un rol "Corrector" con permisos específicos.

```bash
# 1. Identificar permisos necesarios
curl -X GET $API_BASE/roles/permissions \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Permisos identificados:
# - translations:read (ID: 6)
# - translations:update (ID: 7)

# 2. Crear el rol
curl -X POST $API_BASE/roles/roles \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "corrector",
    "description": "Corrector de traducciones - solo lectura y edición",
    "is_default": false,
    "permission_ids": [6, 7]
  }'
# Respuesta: Rol creado con ID 6

# 3. Asignar a usuarios específicos
curl -X POST $API_BASE/roles/roles/assign \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 25,
    "role_id": 6
  }'
```

### Caso 6: Auditoría de Seguridad

**Escenario:** Revisar todos los superusuarios del sistema.

```bash
#!/bin/bash
# audit_superusers.sh

echo "=== Auditoría de Superusuarios ==="
echo ""

ALL_USERS=$(curl -s "$API_BASE/users?skip=0&limit=1000" \
  -H "Authorization: Bearer $ADMIN_TOKEN")

echo "👑 Usuarios con privilegios de SUPERUSUARIO:"
echo ""

echo "$ALL_USERS" | jq -r '.[] | select(.is_superuser == true) |
  "  ID: \(.id)
   Username: \(.username)
   Email: \(.email)
   Activo: \(.is_active)
   Creado: \(.created_at)
   ---"'

SUPERUSER_COUNT=$(echo "$ALL_USERS" | jq '[.[] | select(.is_superuser == true)] | length')

echo ""
echo "Total de superusuarios: $SUPERUSER_COUNT"
echo ""
echo "⚠️  Recomendación: Mantener el número de superusuarios al mínimo necesario."
```

### Caso 7: Reseteo Masivo de Contraseñas

**Escenario:** Resetear contraseñas de múltiples usuarios tras incidente de seguridad.

```bash
#!/bin/bash
# mass_password_reset.sh

USERS=(15 16 17 18 19)
TEMP_PASSWORD="ResetPass2025!"

echo "⚠️  Reseteo masivo de contraseñas"
echo ""

for user_id in "${USERS[@]}"; do
  echo "Reseteando contraseña para usuario ID: $user_id"

  curl -X PUT $API_BASE/users/$user_id \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"password\": \"$TEMP_PASSWORD\"
    }"

  echo ""
done

echo ""
echo "✅ Contraseñas reseteadas. IMPORTANTE:"
echo "   1. Notificar a todos los usuarios"
echo "   2. Solicitar cambio de contraseña en primer login"
echo "   3. Documentar el incidente"
```

---

## Auditoría y Monitoreo

### Información de Auditoría Disponible

Los modelos incluyen timestamps automáticos:

| Campo | Descripción |
|-------|-------------|
| `created_at` | Fecha/hora de creación del registro |
| `updated_at` | Fecha/hora de última actualización |

**Ubicación:** [`app/models/user.py:18-19`](app/models/user.py#L18-L19)

### Consultas de Auditoría

#### 1. Usuarios Creados en un Período

```bash
# Obtener todos los usuarios
curl -X GET $API_BASE/users \
  -H "Authorization: Bearer $ADMIN_TOKEN" | \
  jq '[.[] | select(.created_at >= "2025-01-01" and .created_at <= "2025-01-31")]'
```

#### 2. Usuarios Inactivos

```bash
curl -X GET $API_BASE/users \
  -H "Authorization: Bearer $ADMIN_TOKEN" | \
  jq '[.[] | select(.is_active == false)]'
```

#### 3. Distribución de Roles

```bash
#!/bin/bash
# role_distribution.sh

echo "=== Distribución de Roles ==="
echo ""

ROLES=$(curl -s $API_BASE/roles/roles \
  -H "Authorization: Bearer $ADMIN_TOKEN")

echo "$ROLES" | jq -r '.[] | "\(.name) (ID: \(.id))"' | while read role_info; do
  ROLE_ID=$(echo "$role_info" | grep -oP '\(ID: \K[0-9]+')

  USER_COUNT=$(curl -s "$API_BASE/roles/roles/$ROLE_ID/users" \
    -H "Authorization: Bearer $ADMIN_TOKEN" | jq '. | length')

  echo "$role_info -> $USER_COUNT usuarios"
done
```

### Logging de Operaciones Administrativas

**Recomendación:** Implementar logging para todas las operaciones administrativas.

```python
# Ejemplo de logging en endpoint
import logging

logger = logging.getLogger(__name__)

@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_superuser)
):
    logger.warning(
        f"User deletion requested - "
        f"Target: {user_id}, "
        f"Performed by: {current_user.username} (ID: {current_user.id})"
    )

    success = await crud_user.delete_user(db, user_id)

    if success:
        logger.info(f"User {user_id} successfully deleted")
    else:
        logger.error(f"Failed to delete user {user_id}")

    return success
```

### Exportar Reporte de Usuarios

```bash
#!/bin/bash
# export_user_report.sh

OUTPUT_FILE="user_report_$(date +%Y%m%d_%H%M%S).json"

echo "Generando reporte de usuarios..."

curl -s "$API_BASE/users?skip=0&limit=10000" \
  -H "Authorization: Bearer $ADMIN_TOKEN" > "$OUTPUT_FILE"

echo "Reporte guardado en: $OUTPUT_FILE"

# Estadísticas rápidas
TOTAL=$(jq '. | length' "$OUTPUT_FILE")
ACTIVE=$(jq '[.[] | select(.is_active == true)] | length' "$OUTPUT_FILE")
SUPERUSERS=$(jq '[.[] | select(.is_superuser == true)] | length' "$OUTPUT_FILE")

echo ""
echo "=== Resumen ==="
echo "Total usuarios: $TOTAL"
echo "Usuarios activos: $ACTIVE"
echo "Superusuarios: $SUPERUSERS"
```

---

## Buenas Prácticas

### 1. Principio de Mínimo Privilegio

✅ **HACER:**
- Asignar solo los permisos necesarios para cada rol
- Usar roles específicos en lugar de superusuarios
- Revisar periódicamente permisos asignados

❌ **NO HACER:**
- Hacer a todos los usuarios superusuarios
- Crear roles con todos los permisos
- Mantener permisos innecesarios

### 2. Gestión de Superusuarios

✅ **HACER:**
- Limitar al mínimo el número de superusuarios
- Documentar quién es superusuario y por qué
- Auditar regularmente la lista de superusuarios
- Usar cuentas personales, no compartidas

❌ **NO HACER:**
- Compartir credenciales de superusuario
- Crear superusuarios para tareas específicas
- Mantener superusuarios de ex-empleados

### 3. Ciclo de Vida de Usuarios

✅ **HACER:**
- Desactivar en lugar de eliminar (soft delete)
- Documentar razones de desactivación
- Establecer proceso de offboarding formal
- Revisar accesos periódicamente

❌ **NO HACER:**
- Eliminar usuarios sin verificar dependencias
- Dejar usuarios inactivos sin documentación
- Mantener cuentas de ex-empleados activas

### 4. Gestión de Contraseñas

✅ **HACER:**
- Usar contraseñas temporales aleatorias
- Forzar cambio de contraseña en primer login (implementar)
- Documentar procedimiento de reseteo
- Notificar al usuario cambios en su cuenta

❌ **NO HACER:**
- Usar contraseñas predecibles (user123, password, etc.)
- Compartir contraseñas por canales inseguros
- Reutilizar contraseñas temporales

### 5. Auditoría y Cumplimiento

✅ **HACER:**
- Mantener logs de operaciones administrativas
- Revisar cambios de permisos regularmente
- Documentar cambios significativos
- Exportar reportes periódicos

❌ **NO HACER:**
- Realizar cambios sin documentar
- Ignorar actividad sospechosa
- Eliminar logs prematuramente

### 6. Roles y Permisos

✅ **HACER:**
- Usar nomenclatura consistente (`resource:action`)
- Documentar propósito de cada rol
- Agrupar permisos lógicamente
- Revisar roles obsoletos periódicamente

❌ **NO HACER:**
- Crear roles con nombres ambiguos
- Duplicar permisos innecesariamente
- Mantener roles sin usuarios

### 7. Seguridad Operacional

✅ **HACER:**
- Verificar antes de eliminar
- Usar scripts para operaciones masivas
- Realizar backups antes de cambios grandes
- Probar en entorno de desarrollo primero

❌ **NO HACER:**
- Ejecutar comandos sin verificar
- Modificar datos de producción sin backup
- Realizar cambios masivos sin planificación

---

## Troubleshooting

### Error 401: Unauthorized

**Síntoma:**
```json
{
  "detail": "Could not validate credentials"
}
```

**Causas posibles:**
1. Token expirado
2. Token inválido
3. Usuario no existe
4. Usuario fue eliminado

**Solución:**
```bash
# 1. Verificar token
echo $ADMIN_TOKEN

# 2. Generar nuevo token
curl -X POST $API_BASE/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin_password"
  }'

# 3. Actualizar variable
export ADMIN_TOKEN="<nuevo_token>"
```

### Error 403: Forbidden

**Síntoma:**
```json
{
  "detail": "The user doesn't have enough privileges"
}
```

**Causas posibles:**
1. Usuario no es superusuario (para endpoints que lo requieren)
2. Usuario no tiene el permiso necesario

**Solución:**
```bash
# 1. Verificar permisos del usuario
curl -X GET $API_BASE/users/me \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# 2. Verificar roles
curl -X GET $API_BASE/roles/users/<user_id>/roles \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# 3. Si es necesario, usar token de superusuario real
```

### Error 400: Bad Request - Inactive user

**Síntoma:**
```json
{
  "detail": "Inactive user"
}
```

**Causa:**
El usuario con el que intentas autenticarte tiene `is_active: false`

**Solución:**
```bash
# Activar el usuario (requiere otro admin)
curl -X PUT $API_BASE/users/<user_id> \
  -H "Authorization: Bearer $OTHER_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "is_active": true
  }'
```

### Error 400: Username/Email already registered

**Síntoma:**
```json
{
  "detail": "Username already registered"
}
```

**Causa:**
El username o email ya existe en el sistema

**Solución:**
```bash
# 1. Verificar si el usuario existe
curl -X GET $API_BASE/users \
  -H "Authorization: Bearer $ADMIN_TOKEN" | \
  jq '.[] | select(.username == "nombre_usuario")'

# 2. Opciones:
# A) Usar un username diferente
# B) Si es el mismo usuario, actualizar en lugar de crear
# C) Si es inactivo, reactivar
```

### Error 404: User/Role/Permission not found

**Síntoma:**
```json
{
  "detail": "User not found"
}
```

**Causa:**
El ID especificado no existe en la base de datos

**Solución:**
```bash
# 1. Listar recursos para verificar IDs correctos
curl -X GET $API_BASE/users \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

curl -X GET $API_BASE/roles/roles \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# 2. Usar el ID correcto
```

### No puedo eliminar un rol

**Síntoma:**
El rol se elimina pero usuarios aún lo tienen

**Causa:**
Problema de sincronización o cache

**Solución:**
```bash
# 1. Verificar que el rol fue eliminado
curl -X GET $API_BASE/roles/roles/<role_id> \
  -H "Authorization: Bearer $ADMIN_TOKEN"
# Debería retornar 404

# 2. Verificar usuarios
curl -X GET $API_BASE/roles/roles/<role_id>/users \
  -H "Authorization: Bearer $ADMIN_TOKEN"
# Debería estar vacío

# 3. Si persiste, revisar base de datos directamente
```

### Token expira demasiado rápido

**Solución:**
Modificar la configuración de expiración en `.env`:

```bash
# .env
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60  # 1 hora
# O
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=480  # 8 horas
```

**Nota:** Tokens más largos son más convenientes pero menos seguros.

### Operación masiva falla a mitad

**Problema:**
Script de operación masiva falla después de procesar algunos usuarios

**Solución:**
```bash
#!/bin/bash
# robust_mass_operation.sh

USERS=(15 16 17 18 19)
SUCCESS_LOG="success.log"
ERROR_LOG="error.log"

for user_id in "${USERS[@]}"; do
  echo "Processing user ID: $user_id"

  RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT $API_BASE/users/$user_id \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"is_active": false}')

  HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

  if [ "$HTTP_CODE" -eq 200 ]; then
    echo "$user_id" >> "$SUCCESS_LOG"
    echo "  ✅ Success"
  else
    echo "$user_id:$HTTP_CODE" >> "$ERROR_LOG"
    echo "  ❌ Failed (HTTP $HTTP_CODE)"
  fi

  sleep 1  # Rate limiting
done

echo ""
echo "Operación completada. Revisar logs:"
echo "  Exitosos: $SUCCESS_LOG"
echo "  Errores: $ERROR_LOG"
```

---

## Resumen de Comandos Rápidos

### Gestión de Usuarios

```bash
# Listar usuarios
curl -X GET "$API_BASE/users?skip=0&limit=100" -H "Authorization: Bearer $ADMIN_TOKEN"

# Crear usuario
curl -X POST $API_BASE/users -H "Content-Type: application/json" \
  -d '{"username":"user","email":"user@ex.com","password":"Pass1234"}'

# Actualizar usuario
curl -X PUT $API_BASE/users/15 -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" -d '{"is_active":false}'

# Eliminar usuario
curl -X DELETE $API_BASE/users/15 -H "Authorization: Bearer $ADMIN_TOKEN"

# Ver usuario específico
curl -X GET $API_BASE/users/15 -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Gestión de Roles

```bash
# Listar roles
curl -X GET $API_BASE/roles/roles -H "Authorization: Bearer $ADMIN_TOKEN"

# Crear rol
curl -X POST $API_BASE/roles/roles -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"rol","description":"Desc","permission_ids":[1,2]}'

# Asignar rol a usuario
curl -X POST $API_BASE/roles/roles/assign -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" -d '{"user_id":15,"role_id":2}'

# Remover rol de usuario
curl -X POST $API_BASE/roles/roles/remove -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" -d '{"user_id":15,"role_id":2}'

# Ver roles de usuario
curl -X GET $API_BASE/roles/users/15/roles -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Gestión de Permisos

```bash
# Listar permisos
curl -X GET $API_BASE/roles/permissions -H "Authorization: Bearer $ADMIN_TOKEN"

# Crear permiso
curl -X POST $API_BASE/roles/permissions -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"res:action","resource":"res","action":"action","description":"Desc"}'
```

---

## Referencias

- [Documentación de Login y Gestión de Usuarios](LOGIN_Y_GESTION_USUARIOS.md) - Documentación técnica completa
- [`app/api/users.py`](app/api/users.py) - Endpoints de gestión de usuarios
- [`app/api/roles.py`](app/api/roles.py) - Endpoints de gestión de roles y permisos
- [`app/api/auth.py`](app/api/auth.py) - Endpoints de autenticación
- [`app/crud/user.py`](app/crud/user.py) - Operaciones CRUD de usuarios
- [`app/crud/role.py`](app/crud/role.py) - Operaciones CRUD de roles y permisos

---

**Documentación generada el 2025-01-15**
**Versión: 1.0**
