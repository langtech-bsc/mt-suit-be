# Documentación: Login y Gestión de Usuarios

## Índice
1. [Descripción General](#descripción-general)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Modelos de Datos](#modelos-de-datos)
4. [Autenticación y Seguridad](#autenticación-y-seguridad)
5. [Endpoints de API](#endpoints-de-api)
6. [Sistema de Roles y Permisos](#sistema-de-roles-y-permisos)
7. [Flujos de Trabajo](#flujos-de-trabajo)
8. [Ejemplos de Uso](#ejemplos-de-uso)
9. [Seguridad y Mejores Prácticas](#seguridad-y-mejores-prácticas)

---

## Descripción General

El módulo de traducción cuenta con un sistema completo de **autenticación** y **gestión de usuarios** que incluye:

- **Autenticación basada en JWT (JSON Web Tokens)**
- **Sistema de roles y permisos granulares**
- **Control de acceso basado en roles (RBAC)**
- **Gestión completa de usuarios (CRUD)**
- **Seguridad mediante bcrypt para contraseñas**

### Características Principales

✅ Registro e inicio de sesión de usuarios
✅ Autenticación mediante tokens JWT
✅ Sistema de roles con permisos personalizables
✅ Control de acceso a nivel de endpoint
✅ Usuarios con privilegios de superadministrador
✅ Validación robusta de contraseñas
✅ Gestión de estados de usuario (activo/inactivo)

---

## Arquitectura del Sistema

### Capas de la Aplicación

```
┌─────────────────────────────────────────┐
│         API Endpoints Layer             │
│  (auth.py, users.py, roles.py)         │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      Dependencies & Security Layer      │
│   (deps.py, security.py, config.py)    │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         Business Logic Layer            │
│      (CRUD: user.py, role.py)          │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         Data Access Layer               │
│    (Models & Schemas & Database)        │
└─────────────────────────────────────────┘
```

### Componentes Principales

| Componente | Ubicación | Descripción |
|------------|-----------|-------------|
| **Modelos** | `app/models/user.py`, `app/models/role.py` | Definición de tablas de base de datos |
| **Schemas** | `app/schemas/user.py`, `app/schemas/role.py` | Validación y serialización de datos |
| **CRUD** | `app/crud/user.py`, `app/crud/role.py` | Operaciones de base de datos |
| **API Endpoints** | `app/api/auth.py`, `app/api/users.py`, `app/api/roles.py` | Rutas y controladores HTTP |
| **Seguridad** | `app/core/security.py` | Hashing de contraseñas y JWT |
| **Dependencias** | `app/api/deps.py` | Autenticación y autorización |

---

## Modelos de Datos

### 1. Modelo User

**Ubicación:** [`app/models/user.py:9-50`](app/models/user.py#L9-L50)

```python
class User(Base):
    __tablename__ = "users"

    # Campos principales
    id: BigInteger (PK, autoincrement)
    username: String(50) (unique, indexed)
    email: String(120) (unique, indexed)
    hashed_password: String(255)
    is_active: Boolean (default=True)
    is_superuser: Boolean (default=False)
    created_at: DateTime (auto)
    updated_at: DateTime (auto)

    # Relaciones
    roles: Many-to-Many → Role
    translations: One-to-Many → Translation
```

**Métodos:**
- `has_permission(permission_name: str) -> bool`: Verifica si el usuario tiene un permiso específico
- `has_role(role_name: str) -> bool`: Verifica si el usuario tiene un rol específico

### 2. Modelo Role

**Ubicación:** [`app/models/role.py:55-85`](app/models/role.py#L55-L85)

```python
class Role(Base):
    __tablename__ = "roles"

    # Campos principales
    id: BigInteger (PK, autoincrement)
    name: String(50) (unique, indexed)
    description: String(255)
    is_default: Boolean (default=False)
    created_at: DateTime (auto)
    updated_at: DateTime (auto)

    # Relaciones
    permissions: Many-to-Many → Permission
    users: Many-to-Many → User
```

### 3. Modelo Permission

**Ubicación:** [`app/models/role.py:27-53`](app/models/role.py#L27-L53)

```python
class Permission(Base):
    __tablename__ = "permissions"

    # Campos principales
    id: BigInteger (PK, autoincrement)
    name: String(100) (unique, indexed)
    description: String(255)
    resource: String(100) (indexed)
    action: String(50)
    created_at: DateTime (auto)

    # Relaciones
    roles: Many-to-Many → Role
```

### 4. Tablas de Asociación

```python
# user_roles: Relación User ↔ Role
user_roles (user_id, role_id)

# role_permissions: Relación Role ↔ Permission
role_permissions (role_id, permission_id)
```

---

## Autenticación y Seguridad

### Seguridad de Contraseñas

**Ubicación:** [`app/core/security.py`](app/core/security.py)

#### Hashing con bcrypt

```python
# Generar hash de contraseña
def get_password_hash(password: str) -> str
    - Usa bcrypt con salt generado automáticamente
    - Límite de 72 bytes (restricción de bcrypt)
    - Retorna hash en formato string
```

#### Verificación de Contraseñas

```python
# Verificar contraseña
def verify_password(plain_password: str, hashed_password: str) -> bool
    - Compara de forma segura contraseña plana con hash
    - Retorna True si coinciden, False en caso contrario
```

#### Validación de Contraseñas

**Ubicación:** [`app/schemas/user.py:22-28`](app/schemas/user.py#L22-L28)

```python
Requisitos:
- Longitud mínima: 8 caracteres
- Longitud máxima: 100 caracteres
- Límite UTF-8: 72 bytes (restricción bcrypt)
```

### Tokens JWT (JSON Web Tokens)

**Ubicación:** [`app/core/security.py:54-96`](app/core/security.py#L54-L96)

#### Creación de Tokens

```python
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str
```

**Configuración:**
- Algoritmo: HS256 (configurado en `settings.jwt_algorithm`)
- Tiempo de expiración: Configurable en `settings.jwt_access_token_expire_minutes`
- Secret Key: Almacenada en `settings.jwt_secret_key`
- Claim "sub": Contiene el username del usuario

#### Decodificación de Tokens

```python
def decode_access_token(token: str) -> dict | None
```

**Proceso:**
1. Decodifica el token usando la secret key
2. Verifica la firma y la expiración
3. Retorna el payload o None si es inválido

### Dependencias de Autenticación

**Ubicación:** [`app/api/deps.py`](app/api/deps.py)

#### 1. `get_current_user`

**Ubicación:** [`app/api/deps.py:18-58`](app/api/deps.py#L18-L58)

```python
async def get_current_user(
    credentials: HTTPAuthorizationCredentials,
    db: AsyncSession
) -> User
```

**Función:**
- Extrae y valida el token JWT del header Authorization
- Decodifica el token y obtiene el username
- Busca el usuario en la base de datos
- Retorna el objeto User
- Lanza HTTPException 401 si falla

#### 2. `get_current_active_user`

**Ubicación:** [`app/api/deps.py:60-78`](app/api/deps.py#L60-L78)

```python
async def get_current_active_user(current_user: User) -> User
```

**Función:**
- Verifica que `user.is_active == True`
- Lanza HTTPException 400 si el usuario está inactivo

#### 3. `get_current_superuser`

**Ubicación:** [`app/api/deps.py:80-100`](app/api/deps.py#L80-L100)

```python
async def get_current_superuser(current_user: User) -> User
```

**Función:**
- Verifica que `user.is_superuser == True`
- Lanza HTTPException 403 si no es superusuario

#### 4. `PermissionChecker`

**Ubicación:** [`app/api/deps.py:102-140`](app/api/deps.py#L102-L140)

```python
class PermissionChecker:
    def __init__(self, required_permissions: list[str])
    async def __call__(self, current_user: User) -> User
```

**Uso:**
```python
@router.get("/protected")
async def protected_route(
    _: Annotated[User, Depends(PermissionChecker(["resource:action"]))]
):
    pass
```

**Función:**
- Verifica si el usuario tiene alguno de los permisos requeridos
- Los superusuarios siempre tienen acceso
- Lanza HTTPException 403 si no tiene permisos

#### 5. `RoleChecker`

**Ubicación:** [`app/api/deps.py:142-180`](app/api/deps.py#L142-L180)

```python
class RoleChecker:
    def __init__(self, required_roles: list[str])
    async def __call__(self, current_user: User) -> User
```

**Uso:**
```python
@router.get("/admin")
async def admin_route(
    _: Annotated[User, Depends(RoleChecker(["admin", "moderator"]))]
):
    pass
```

**Función:**
- Verifica si el usuario tiene alguno de los roles requeridos
- Los superusuarios siempre tienen acceso
- Lanza HTTPException 403 si no tiene el rol

---

## Endpoints de API

### Autenticación

**Ubicación:** [`app/api/auth.py`](app/api/auth.py)

#### POST `/api/auth/login`

**Ubicación:** [`app/api/auth.py:18-52`](app/api/auth.py#L18-L52)

**Descripción:** Autentica un usuario y retorna un token JWT.

**Request Body:**
```json
{
  "username": "usuario o email",
  "password": "contraseña"
}
```

**Response:** 200 OK
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Errores:**
- `401 Unauthorized`: Credenciales incorrectas
- `400 Bad Request`: Usuario inactivo

**Proceso:**
1. Valida credenciales (username/email + password)
2. Verifica que el usuario esté activo
3. Genera token JWT con expiración configurable
4. Retorna token de acceso

#### POST `/api/auth/logout`

**Ubicación:** [`app/api/auth.py:54-66`](app/api/auth.py#L54-L66)

**Descripción:** Endpoint de logout (principalmente client-side).

**Response:** 200 OK
```json
{
  "message": "Successfully logged out"
}
```

**Nota:** Con JWT, el logout se maneja principalmente en el cliente eliminando el token. Este endpoint confirma la acción y puede extenderse para blacklisting de tokens.

---

### Gestión de Usuarios

**Ubicación:** [`app/api/users.py`](app/api/users.py)

#### POST `/api/users` (Registro Público)

**Ubicación:** [`app/api/users.py:17-47`](app/api/users.py#L17-L47)

**Descripción:** Crea un nuevo usuario (endpoint público para registro).

**Request Body:**
```json
{
  "username": "nuevouser",
  "email": "user@example.com",
  "password": "contraseña123"
}
```

**Validaciones:**
- `username`: 3-50 caracteres
- `email`: Formato válido de email
- `password`: 8-100 caracteres, máx 72 bytes UTF-8

**Response:** 201 Created
```json
{
  "id": 1,
  "username": "nuevouser",
  "email": "user@example.com",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2025-01-15T10:30:00",
  "updated_at": "2025-01-15T10:30:00",
  "roles": []
}
```

**Errores:**
- `400 Bad Request`: Username o email ya registrado

#### GET `/api/users/me` 🔒

**Ubicación:** [`app/api/users.py:49-63`](app/api/users.py#L49-L63)

**Descripción:** Obtiene la información del usuario autenticado actual.

**Autenticación:** Requiere token JWT válido

**Headers:**
```
Authorization: Bearer <token>
```

**Response:** 200 OK
```json
{
  "id": 1,
  "username": "usuario",
  "email": "user@example.com",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2025-01-15T10:30:00",
  "updated_at": "2025-01-15T10:30:00",
  "roles": [
    {
      "id": 1,
      "name": "translator",
      "description": "Usuario traductor",
      "is_default": true,
      "created_at": "2025-01-15T09:00:00",
      "updated_at": "2025-01-15T09:00:00",
      "permissions": [...]
    }
  ]
}
```

#### PUT `/api/users/me` 🔒

**Ubicación:** [`app/api/users.py:65-99`](app/api/users.py#L65-L99)

**Descripción:** Actualiza la información del usuario autenticado.

**Autenticación:** Requiere token JWT válido

**Request Body:** (todos los campos son opcionales)
```json
{
  "username": "nuevo_username",
  "email": "nuevo@email.com",
  "password": "nueva_contraseña",
  "is_active": true
}
```

**Response:** 200 OK (mismo formato que GET /me)

**Errores:**
- `400 Bad Request`: Username o email ya en uso por otro usuario

#### GET `/api/users` 🔒👑

**Ubicación:** [`app/api/users.py:101-122`](app/api/users.py#L101-L122)

**Descripción:** Lista todos los usuarios (solo superusuarios).

**Autenticación:** Requiere superusuario

**Query Parameters:**
- `skip`: Número de registros a omitir (default: 0)
- `limit`: Máximo de registros a retornar (default: 100, max: 100)

**Response:** 200 OK
```json
[
  {
    "id": 1,
    "username": "user1",
    ...
  },
  {
    "id": 2,
    "username": "user2",
    ...
  }
]
```

**Errores:**
- `403 Forbidden`: Usuario no es superusuario

#### GET `/api/users/{user_id}` 🔒👑

**Ubicación:** [`app/api/users.py:124-148`](app/api/users.py#L124-L148)

**Descripción:** Obtiene un usuario por ID (solo superusuarios).

**Autenticación:** Requiere superusuario

**Response:** 200 OK (formato de usuario completo)

**Errores:**
- `403 Forbidden`: Usuario no es superusuario
- `404 Not Found`: Usuario no encontrado

#### PUT `/api/users/{user_id}` 🔒👑

**Ubicación:** [`app/api/users.py:150-188`](app/api/users.py#L150-L188)

**Descripción:** Actualiza un usuario por ID (solo superusuarios).

**Autenticación:** Requiere superusuario

**Request Body:** (campos opcionales)
```json
{
  "username": "nuevo_username",
  "email": "nuevo@email.com",
  "password": "nueva_contraseña",
  "is_active": false
}
```

**Response:** 200 OK (usuario actualizado)

**Errores:**
- `403 Forbidden`: Usuario no es superusuario
- `404 Not Found`: Usuario no encontrado
- `400 Bad Request`: Username/email en uso

#### DELETE `/api/users/{user_id}` 🔒👑

**Ubicación:** [`app/api/users.py:190-211`](app/api/users.py#L190-L211)

**Descripción:** Elimina un usuario por ID (solo superusuarios).

**Autenticación:** Requiere superusuario

**Response:** 204 No Content

**Errores:**
- `403 Forbidden`: Usuario no es superusuario
- `404 Not Found`: Usuario no encontrado

---

### Gestión de Roles y Permisos

**Ubicación:** [`app/api/roles.py`](app/api/roles.py)

#### Permisos

##### GET `/api/roles/permissions` 🔒

**Ubicación:** [`app/api/roles.py:27-37`](app/api/roles.py#L27-L37)

**Descripción:** Lista todos los permisos.

**Autenticación:** Requiere permiso `permissions:read`

**Query Parameters:**
- `skip`: Registros a omitir (default: 0)
- `limit`: Máximo de registros (default: 100)

**Response:** 200 OK
```json
[
  {
    "id": 1,
    "name": "users:read",
    "description": "Ver usuarios",
    "resource": "users",
    "action": "read",
    "created_at": "2025-01-15T09:00:00"
  }
]
```

##### GET `/api/roles/permissions/{permission_id}` 🔒

**Ubicación:** [`app/api/roles.py:39-50`](app/api/roles.py#L39-L50)

**Descripción:** Obtiene un permiso específico por ID.

**Autenticación:** Requiere permiso `permissions:read`

##### POST `/api/roles/permissions` 🔒

**Ubicación:** [`app/api/roles.py:52-68`](app/api/roles.py#L52-L68)

**Descripción:** Crea un nuevo permiso.

**Autenticación:** Requiere permiso `permissions:create`

**Request Body:**
```json
{
  "name": "translations:create",
  "description": "Crear traducciones",
  "resource": "translations",
  "action": "create"
}
```

##### PUT `/api/roles/permissions/{permission_id}` 🔒

**Ubicación:** [`app/api/roles.py:70-82`](app/api/roles.py#L70-L82)

**Descripción:** Actualiza un permiso.

**Autenticación:** Requiere permiso `permissions:update`

##### DELETE `/api/roles/permissions/{permission_id}` 🔒

**Ubicación:** [`app/api/roles.py:84-94`](app/api/roles.py#L84-L94)

**Descripción:** Elimina un permiso.

**Autenticación:** Requiere permiso `permissions:delete`

---

#### Roles

##### GET `/api/roles/roles` 🔒

**Ubicación:** [`app/api/roles.py:97-107`](app/api/roles.py#L97-L107)

**Descripción:** Lista todos los roles.

**Autenticación:** Requiere permiso `roles:read`

**Response:** 200 OK
```json
[
  {
    "id": 1,
    "name": "admin",
    "description": "Administrador del sistema",
    "is_default": false,
    "created_at": "2025-01-15T09:00:00",
    "updated_at": "2025-01-15T09:00:00",
    "permissions": [
      {
        "id": 1,
        "name": "users:read",
        ...
      }
    ]
  }
]
```

##### POST `/api/roles/roles` 🔒

**Ubicación:** [`app/api/roles.py:122-138`](app/api/roles.py#L122-L138)

**Descripción:** Crea un nuevo rol.

**Autenticación:** Requiere permiso `roles:create`

**Request Body:**
```json
{
  "name": "editor",
  "description": "Editor de contenido",
  "is_default": false,
  "permission_ids": [1, 2, 3]
}
```

##### POST `/api/roles/roles/assign` 🔒

**Ubicación:** [`app/api/roles.py:167-182`](app/api/roles.py#L167-L182)

**Descripción:** Asigna un rol a un usuario.

**Autenticación:** Requiere permiso `roles:update` O `users:update`

**Request Body:**
```json
{
  "user_id": 5,
  "role_id": 2
}
```

**Response:** 200 OK
```json
{
  "message": "Role assigned successfully",
  "user_id": 5
}
```

##### POST `/api/roles/roles/remove` 🔒

**Ubicación:** [`app/api/roles.py:184-199`](app/api/roles.py#L184-L199)

**Descripción:** Remueve un rol de un usuario.

**Autenticación:** Requiere permiso `roles:update` O `users:update`

**Request Body:**
```json
{
  "user_id": 5,
  "role_id": 2
}
```

##### GET `/api/roles/users/{user_id}/roles` 🔒

**Ubicación:** [`app/api/roles.py:201-217`](app/api/roles.py#L201-L217)

**Descripción:** Obtiene todos los roles de un usuario.

**Autenticación:** Usuario puede ver sus propios roles, o necesita permiso `users:read`

**Response:** 200 OK (array de roles)

##### GET `/api/roles/roles/{role_id}/users` 🔒

**Ubicación:** [`app/api/roles.py:219-230`](app/api/roles.py#L219-L230)

**Descripción:** Obtiene todos los usuarios con un rol específico.

**Autenticación:** Requiere permiso `users:read` O `roles:read`

---

## Sistema de Roles y Permisos

### Conceptos Clave

#### 1. Permisos

Los permisos son unidades atómicas de acceso definidas por:
- **name**: Identificador único (ej: `users:read`)
- **resource**: Recurso al que aplica (ej: `users`)
- **action**: Acción permitida (ej: `read`, `create`, `update`, `delete`)

**Convención de nombres:** `<resource>:<action>`

**Ejemplos:**
```
users:read          → Ver usuarios
users:create        → Crear usuarios
translations:update → Actualizar traducciones
roles:delete        → Eliminar roles
```

#### 2. Roles

Los roles son **agrupaciones de permisos** que se asignan a usuarios:
- Un rol puede tener múltiples permisos
- Un usuario puede tener múltiples roles
- Los permisos se heredan de todos los roles del usuario

**Ejemplo de Rol:**
```json
{
  "name": "translator",
  "description": "Usuario traductor estándar",
  "is_default": true,
  "permissions": [
    "translations:create",
    "translations:read",
    "translations:update"
  ]
}
```

#### 3. Superusuarios

**Ubicación:** [`app/models/user.py:16-17`](app/models/user.py#L16-L17)

Los usuarios con `is_superuser = True`:
- Tienen **todos los permisos** automáticamente
- Bypassean todas las verificaciones de roles y permisos
- No necesitan roles asignados para acceder a recursos

**Verificación en código:**
```python
# En User.has_permission()
if self.is_superuser:
    return True

# En User.has_role()
if self.is_superuser:
    return True
```

### Lógica de Autorización

#### Flujo de Verificación

```
┌────────────────────────────────────────────────┐
│  1. ¿Es superusuario?                         │
│     Sí → Acceso garantizado ✓                 │
│     No → Continuar verificación               │
└─────────────────┬──────────────────────────────┘
                  │
┌─────────────────▼──────────────────────────────┐
│  2. ¿Tiene algún rol con el permiso requerido?│
│     Sí → Acceso garantizado ✓                 │
│     No → Acceso denegado ✗                    │
└────────────────────────────────────────────────┘
```

#### Ejemplo de Verificación

```python
# Usuario solicita acceso a endpoint protegido
@router.get("/protected")
async def protected_route(
    _: Annotated[User, Depends(PermissionChecker(["resource:read"]))]
):
    pass

# Proceso:
# 1. FastAPI extrae el token JWT
# 2. get_current_user valida el token y carga el usuario
# 3. get_current_active_user verifica que is_active=True
# 4. PermissionChecker verifica:
#    - Si user.is_superuser → Permitir ✓
#    - Si user.has_permission("resource:read") → Permitir ✓
#    - Caso contrario → HTTP 403 ✗
```

### Asignación de Roles por Defecto

**Ubicación:** [`app/models/role.py:63`](app/models/role.py#L63)

Los roles con `is_default = True` se asignan automáticamente a nuevos usuarios durante el registro.

**Ejemplo:**
```python
# Al crear un usuario:
user = await crud_user.create_user(db, user_in)

# El CRUD automáticamente asigna roles por defecto:
default_roles = await db.execute(
    select(Role).where(Role.is_default == True)
)
for role in default_roles:
    user.roles.append(role)
```

---

## Flujos de Trabajo

### 1. Registro de Usuario

```
┌──────────────┐
│   Cliente    │
└──────┬───────┘
       │ POST /api/users
       │ {username, email, password}
       ▼
┌──────────────────────────────────────┐
│  Validar datos (Pydantic)            │
│  - username: 3-50 caracteres         │
│  - email: formato válido             │
│  - password: 8-100 chars, ≤72 bytes  │
└──────┬───────────────────────────────┘
       │ ✓
       ▼
┌──────────────────────────────────────┐
│  Verificar unicidad                  │
│  - ¿Username existe? → 400 Error     │
│  - ¿Email existe? → 400 Error        │
└──────┬───────────────────────────────┘
       │ ✓
       ▼
┌──────────────────────────────────────┐
│  Hashear contraseña (bcrypt)         │
│  - Generar salt                      │
│  - Crear hash                        │
└──────┬───────────────────────────────┘
       │ ✓
       ▼
┌──────────────────────────────────────┐
│  Crear usuario en BD                 │
│  - Insertar registro                 │
│  - Asignar roles por defecto         │
└──────┬───────────────────────────────┘
       │ ✓
       ▼
┌──────────────────────────────────────┐
│  Retornar UserResponse (201)         │
│  - Sin hashed_password               │
│  - Con roles asignados               │
└──────────────────────────────────────┘
```

### 2. Login de Usuario

```
┌──────────────┐
│   Cliente    │
└──────┬───────┘
       │ POST /api/auth/login
       │ {username, password}
       ▼
┌──────────────────────────────────────┐
│  Buscar usuario                      │
│  - Por username O email              │
│  - ¿No existe? → 401 Error           │
└──────┬───────────────────────────────┘
       │ ✓
       ▼
┌──────────────────────────────────────┐
│  Verificar contraseña                │
│  - bcrypt.checkpw()                  │
│  - ¿No coincide? → 401 Error         │
└──────┬───────────────────────────────┘
       │ ✓
       ▼
┌──────────────────────────────────────┐
│  Verificar estado activo             │
│  - ¿is_active=False? → 400 Error     │
└──────┬───────────────────────────────┘
       │ ✓
       ▼
┌──────────────────────────────────────┐
│  Generar JWT token                   │
│  - Payload: {sub: username}          │
│  - Expiración: config time           │
│  - Firma: HS256 con secret_key       │
└──────┬───────────────────────────────┘
       │ ✓
       ▼
┌──────────────────────────────────────┐
│  Retornar token (200)                │
│  {access_token, token_type: "bearer"}│
└──────────────────────────────────────┘
       │
       ▼
┌──────────────┐
│   Cliente    │
│ Guarda token │
└──────────────┘
```

### 3. Acceso a Recurso Protegido

```
┌──────────────┐
│   Cliente    │
└──────┬───────┘
       │ GET /api/users/me
       │ Authorization: Bearer <token>
       ▼
┌──────────────────────────────────────┐
│  Extraer token del header            │
│  - ¿No hay token? → 401 Error        │
└──────┬───────────────────────────────┘
       │ ✓
       ▼
┌──────────────────────────────────────┐
│  Decodificar y validar JWT           │
│  - Verificar firma                   │
│  - Verificar expiración              │
│  - ¿Inválido? → 401 Error            │
└──────┬───────────────────────────────┘
       │ ✓ payload: {sub: "username"}
       ▼
┌──────────────────────────────────────┐
│  Buscar usuario en BD                │
│  - Por username del token            │
│  - ¿No existe? → 401 Error           │
└──────┬───────────────────────────────┘
       │ ✓ user loaded with roles
       ▼
┌──────────────────────────────────────┐
│  Verificar is_active                 │
│  - ¿is_active=False? → 400 Error     │
└──────┬───────────────────────────────┘
       │ ✓ current_user
       ▼
┌──────────────────────────────────────┐
│  Verificar permisos (si requerido)   │
│  - ¿Es superuser? → Permitir ✓       │
│  - ¿Tiene permiso? → Permitir ✓      │
│  - Caso contrario → 403 Error        │
└──────┬───────────────────────────────┘
       │ ✓
       ▼
┌──────────────────────────────────────┐
│  Ejecutar lógica del endpoint        │
│  - Acceso a current_user             │
│  - Retornar respuesta                │
└──────────────────────────────────────┘
```

### 4. Asignación de Rol a Usuario

```
┌──────────────┐
│ Administrador│
└──────┬───────┘
       │ POST /api/roles/roles/assign
       │ {user_id: 5, role_id: 2}
       │ Authorization: Bearer <admin_token>
       ▼
┌──────────────────────────────────────┐
│  Autenticar y verificar permisos     │
│  - Validar token                     │
│  - ¿Tiene "roles:update"? → Sí ✓     │
└──────┬───────────────────────────────┘
       │ ✓
       ▼
┌──────────────────────────────────────┐
│  Buscar usuario y rol                │
│  - ¿Usuario existe?                  │
│  - ¿Rol existe?                      │
│  - ¿Alguno no existe? → 404 Error    │
└──────┬───────────────────────────────┘
       │ ✓
       ▼
┌──────────────────────────────────────┐
│  Verificar si ya tiene el rol        │
│  - ¿Ya asignado? → No hacer nada     │
└──────┬───────────────────────────────┘
       │ ✓
       ▼
┌──────────────────────────────────────┐
│  Asignar rol al usuario              │
│  - user.roles.append(role)           │
│  - Commit a BD                       │
└──────┬───────────────────────────────┘
       │ ✓
       ▼
┌──────────────────────────────────────┐
│  Retornar confirmación (200)         │
│  {message, user_id}                  │
└──────────────────────────────────────┘
```

---

## Ejemplos de Uso

### Ejemplo 1: Registro e Inicio de Sesión

```bash
# 1. Registrar un nuevo usuario
curl -X POST http://localhost:8000/api/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "juan_translator",
    "email": "juan@example.com",
    "password": "SecurePass123"
  }'

# Respuesta (201 Created):
{
  "id": 10,
  "username": "juan_translator",
  "email": "juan@example.com",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2025-01-15T14:30:00",
  "updated_at": "2025-01-15T14:30:00",
  "roles": [
    {
      "id": 2,
      "name": "translator",
      "description": "Usuario traductor estándar",
      "is_default": true,
      ...
    }
  ]
}

# 2. Iniciar sesión
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "juan_translator",
    "password": "SecurePass123"
  }'

# Respuesta (200 OK):
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}

# 3. Acceder a información del usuario actual
curl -X GET http://localhost:8000/api/users/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Respuesta (200 OK):
{
  "id": 10,
  "username": "juan_translator",
  "email": "juan@example.com",
  ...
}
```

### Ejemplo 2: Actualizar Información de Usuario

```bash
# Actualizar email del usuario actual
curl -X PUT http://localhost:8000/api/users/me \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "juan.nuevo@example.com"
  }'

# Respuesta (200 OK): Usuario actualizado
```

### Ejemplo 3: Gestión de Roles (Administrador)

```bash
# 1. Crear un nuevo rol
curl -X POST http://localhost:8000/api/roles/roles \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "editor",
    "description": "Editor de traducciones",
    "is_default": false,
    "permission_ids": [1, 2, 3, 5]
  }'

# 2. Asignar rol a un usuario
curl -X POST http://localhost:8000/api/roles/roles/assign \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 10,
    "role_id": 3
  }'

# 3. Ver roles de un usuario
curl -X GET http://localhost:8000/api/roles/users/10/roles \
  -H "Authorization: Bearer <admin_token>"
```

### Ejemplo 4: Crear Permisos Personalizados

```bash
# Crear un nuevo permiso
curl -X POST http://localhost:8000/api/roles/permissions \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "translations:approve",
    "description": "Aprobar traducciones para publicación",
    "resource": "translations",
    "action": "approve"
  }'
```

### Ejemplo 5: Listar Usuarios (Superusuario)

```bash
# Listar usuarios con paginación
curl -X GET "http://localhost:8000/api/users?skip=0&limit=20" \
  -H "Authorization: Bearer <superuser_token>"

# Respuesta: Array de usuarios
```

---

## Seguridad y Mejores Prácticas

### 1. Seguridad de Contraseñas

#### ✅ Implementado

- **Bcrypt para hashing**: Algoritmo robusto y resistente a ataques
- **Salt automático**: Cada contraseña tiene un salt único
- **Límite de 72 bytes**: Previene problemas con bcrypt
- **Validación de longitud**: Mínimo 8 caracteres

#### 📋 Recomendaciones Adicionales

```python
# Validación adicional de complejidad (opcional)
@field_validator('password')
@classmethod
def validate_password_strength(cls, v: str) -> str:
    if not any(char.isdigit() for char in v):
        raise ValueError('Password must contain at least one digit')
    if not any(char.isupper() for char in v):
        raise ValueError('Password must contain at least one uppercase letter')
    if not any(char.islower() for char in v):
        raise ValueError('Password must contain at least one lowercase letter')
    return v
```

### 2. Seguridad de Tokens JWT

#### ✅ Implementado

- **Firma HMAC SHA-256**: Verificación de integridad
- **Expiración configurable**: Tokens no permanentes
- **Secret key segura**: Almacenada en variables de entorno

#### 📋 Recomendaciones

**Configuración de Seguridad:**
```python
# .env
JWT_SECRET_KEY="<clave-aleatoria-segura-de-al-menos-32-caracteres>"
JWT_ALGORITHM="HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30  # Ajustar según necesidades
```

**Rotación de Secret Key:**
- Cambiar periódicamente la secret key
- Implementar versionado de keys para transición suave

**Refresh Tokens (Extensión):**
```python
# Implementar refresh tokens para renovación sin re-autenticación
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

### 3. Protección de Endpoints

#### Niveles de Protección

| Nivel | Descripción | Ejemplo |
|-------|-------------|---------|
| **Público** | Sin autenticación | POST /api/users (registro) |
| **Autenticado** | Requiere token válido | GET /api/users/me |
| **Con Permiso** | Requiere permiso específico | GET /api/roles/permissions |
| **Superusuario** | Solo superusuarios | DELETE /api/users/{id} |

#### Ejemplo de Protección Gradual

```python
# Nivel 1: Público
@router.post("/register")
async def register(user_in: UserCreate):
    pass

# Nivel 2: Autenticado
@router.get("/me")
async def get_me(user: Annotated[User, Depends(get_current_active_user)]):
    pass

# Nivel 3: Con Permiso
@router.post("/admin")
async def admin_action(
    _: Annotated[User, Depends(PermissionChecker(["admin:action"]))]
):
    pass

# Nivel 4: Superusuario
@router.delete("/{id}")
async def delete(
    id: int,
    _: Annotated[User, Depends(get_current_superuser)]
):
    pass
```

### 4. Validación de Datos

#### ✅ Implementado con Pydantic

```python
# Validaciones automáticas
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr  # Valida formato de email
    password: str = Field(..., min_length=8, max_length=100)

    @field_validator('password')
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        if len(v.encode('utf-8')) > 72:
            raise ValueError('Password cannot exceed 72 bytes')
        return v
```

### 5. Manejo de Errores

#### Códigos de Estado HTTP

| Código | Descripción | Cuándo Usar |
|--------|-------------|-------------|
| 200 OK | Éxito | GET, PUT exitosos |
| 201 Created | Recurso creado | POST exitoso (creación) |
| 204 No Content | Éxito sin contenido | DELETE exitoso |
| 400 Bad Request | Datos inválidos | Validación falla, duplicados |
| 401 Unauthorized | No autenticado | Token inválido/faltante |
| 403 Forbidden | No autorizado | Sin permisos suficientes |
| 404 Not Found | Recurso no existe | Usuario/Rol no encontrado |

#### Mensajes de Error Claros

```python
# ✅ Bueno: Mensaje específico
raise HTTPException(
    status_code=400,
    detail="Username already registered"
)

# ❌ Malo: Mensaje genérico
raise HTTPException(
    status_code=400,
    detail="Error"
)
```

### 6. Rate Limiting (Recomendación)

```python
# Implementar rate limiting para prevenir ataques de fuerza bruta
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/login")
@limiter.limit("5/minute")  # Máx 5 intentos por minuto
async def login(...):
    pass
```

### 7. Logging y Auditoría

```python
# Registrar eventos importantes
import logging

logger = logging.getLogger(__name__)

@router.post("/login")
async def login(...):
    logger.info(f"Login attempt for user: {credentials.username}")

    user = await authenticate_user(...)
    if not user:
        logger.warning(f"Failed login attempt for: {credentials.username}")
        raise HTTPException(...)

    logger.info(f"Successful login for user: {user.username}")
    return token
```

### 8. CORS y Seguridad de Headers

```python
# app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tudominio.com"],  # No usar "*" en producción
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### 9. HTTPS en Producción

**Configuración recomendada:**
```bash
# Usar proxy reverso (nginx, traefik) con SSL/TLS
# Forzar HTTPS en todas las conexiones
# Usar certificados válidos (Let's Encrypt)
```

### 10. Variables de Entorno

```bash
# .env (NUNCA commitear este archivo)
DATABASE_URL=postgresql://user:pass@localhost/db
JWT_SECRET_KEY=<generada-con-openssl-rand-hex-32>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
ENVIRONMENT=production
```

```python
# Generación segura de secret key
import secrets
secret_key = secrets.token_urlsafe(32)
print(secret_key)
```

---

## Resumen de Iconos

- 🔒 = Requiere autenticación (token JWT)
- 👑 = Requiere superusuario
- ⚠️ = Endpoint público (sin autenticación)
- ✅ = Implementado
- 📋 = Recomendación

---

## Referencias de Código

### Archivos Principales

| Archivo | Descripción |
|---------|-------------|
| [`app/models/user.py`](app/models/user.py) | Modelo de base de datos User |
| [`app/models/role.py`](app/models/role.py) | Modelos Role, Permission, tablas de asociación |
| [`app/schemas/user.py`](app/schemas/user.py) | Schemas de validación de usuarios |
| [`app/schemas/role.py`](app/schemas/role.py) | Schemas de validación de roles/permisos |
| [`app/api/auth.py`](app/api/auth.py) | Endpoints de autenticación (login/logout) |
| [`app/api/users.py`](app/api/users.py) | Endpoints CRUD de usuarios |
| [`app/api/roles.py`](app/api/roles.py) | Endpoints de roles y permisos |
| [`app/api/deps.py`](app/api/deps.py) | Dependencias de autenticación y autorización |
| [`app/core/security.py`](app/core/security.py) | Utilidades de seguridad (bcrypt, JWT) |

---

## Conclusión

El sistema de **Login y Gestión de Usuarios** implementado en el módulo de traducción proporciona:

✅ **Autenticación robusta** mediante JWT
✅ **Control de acceso granular** con roles y permisos
✅ **Seguridad de contraseñas** con bcrypt
✅ **Flexibilidad** para extender permisos y roles
✅ **Escalabilidad** con arquitectura en capas
✅ **Cumplimiento** de mejores prácticas de seguridad

Este sistema es adecuado para aplicaciones de producción y puede extenderse con características adicionales como:
- Autenticación de dos factores (2FA)
- OAuth2 / OpenID Connect
- Refresh tokens
- Blacklisting de tokens
- Auditoría completa de acciones
- Rate limiting por usuario
- Notificaciones de seguridad

---

**Documentación generada el 2025-01-15**
