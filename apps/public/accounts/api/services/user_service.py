"""
Servicio de creación y actualización de usuarios (Service Layer).

⚠️ IMPORTANTE:
- Usa set_password() para hashing seguro de contraseñas
- Transaccional: @transaction.atomic
- Sin signals: toda la lógica está aquí
- Genera username único si el modelo lo tiene (compatibilidad con AbstractUser)

Referencias:
- Django set_password: https://docs.djangoproject.com/en/6.0/topics/auth/customizing/
"""
from django.db import transaction, IntegrityError
from django.db.models import Field
from django.contrib.auth import get_user_model

User = get_user_model()


def _user_has_field(field_name: str) -> bool:
    """Verifica si el modelo User tiene un campo específico."""
    return any(isinstance(f, Field) and f.name == field_name for f in User._meta.get_fields())


def _generate_unique_username(email: str) -> str:
    """
    Genera un username único a partir del local-part del email.
    Evita colisiones añadiendo sufijos -1, -2, ...
    """
    base = (email.split("@")[0] if email else "user").strip().replace(" ", "").lower() or "user"
    candidate = base[:150]  # tamaño seguro (max_length de username en AbstractUser)
    if not User.objects.filter(username=candidate).exists():
        return candidate
    i = 1
    while True:
        cand = f"{base}-{i}"[:150]
        if not User.objects.filter(username=cand).exists():
            return cand
        i += 1


@transaction.atomic
def create_user_service(
    *,
    email: str,
    password: str,
    first_name: str = "",
    last_name: str = "",
    is_staff: bool = False,
    is_active: bool = True,
    telefono: str = None,
) -> User:
    """
    Crea un nuevo usuario global (esquema public).
    
    ⚠️ SEGURIDAD:
    - Normaliza email a minúsculas
    - Usa set_password() para hashing seguro (nunca texto plano)
    - Genera username único si el modelo lo tiene (compatibilidad con AbstractUser)
    
    Args:
        email: Email del usuario (único, requerido)
        password: Contraseña en texto plano (se hashea con set_password)
        first_name: Nombre (opcional)
        last_name: Apellido (opcional)
        is_staff: Si es staff/admin (default: False)
        is_active: Si está activo (default: True)
        telefono: Teléfono (opcional)
    
    Returns:
        User: Usuario creado
    
    Raises:
        ValueError: Si el email o password están vacíos
        IntegrityError: Si el email o username ya existen
    """
    # Normalizar email
    email = (email or "").strip().lower()
    if not email or not password:
        raise ValueError("Email y password son obligatorios.")
    
    # Preparar kwargs para crear usuario
    user_kwargs = {
        "email": email,
        "first_name": first_name or "",
        "last_name": last_name or "",
        "is_staff": is_staff,
        "is_active": is_active,
    }
    
    if telefono:
        user_kwargs["telefono"] = telefono
    
    # Si existe el campo username, generarlo de forma única para evitar IntegrityError
    if _user_has_field("username"):
        user_kwargs["username"] = _generate_unique_username(email)
    
    # Crear usuario
    user = User(**user_kwargs)
    user.set_password(password)  # hashing recomendado por Django
    
    try:
        user.save()
    except IntegrityError as e:
        # Email duplicado u otra unicidad: elevar error claro
        raise IntegrityError("No se pudo crear el usuario: email o username ya existente.") from e
    
    return user


@transaction.atomic
def update_user_service(
    *,
    user: User,
    first_name: str = None,
    last_name: str = None,
    password: str = None,
    is_staff: bool = None,
    is_active: bool = None,
    telefono: str = None,
) -> User:
    """
    Actualiza un usuario existente.
    
    ⚠️ SEGURIDAD:
    - Si se proporciona password, usa set_password() para hashing seguro
    - Solo actualiza los campos proporcionados (partial update)
    - No expone el password en la respuesta
    
    Args:
        user: Instancia de User a actualizar
        first_name: Nuevo nombre (opcional)
        last_name: Nuevo apellido (opcional)
        password: Nueva contraseña en texto plano (se hashea, opcional)
        is_staff: Nuevo estado de staff (opcional)
        is_active: Nuevo estado activo (opcional)
        telefono: Nuevo teléfono (opcional)
    
    Returns:
        User: Usuario actualizado
    """
    # Actualizar campos opcionales
    if first_name is not None:
        user.first_name = first_name
    if last_name is not None:
        user.last_name = last_name
    if is_staff is not None:
        user.is_staff = is_staff
    if is_active is not None:
        user.is_active = is_active
    if telefono is not None:
        user.telefono = telefono
    
    # Actualizar contraseña si se proporciona (hashing seguro)
    if password:
        user.set_password(password)
        user.save(update_fields=["first_name", "last_name", "is_staff", "is_active", "telefono", "password"])
    else:
        user.save(update_fields=["first_name", "last_name", "is_staff", "is_active", "telefono"])
    
    return user
