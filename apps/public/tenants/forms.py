"""
Formularios personalizados para el modelo Client (Tenant).

Este módulo contiene formularios personalizados para la administración de tenants,
incluyendo la selección de usuario propietario durante la creación.
"""
from django import forms
from django.contrib.auth import get_user_model
from apps.public.tenants.models import Client

User = get_user_model()


class ClientAdminForm(forms.ModelForm):
    """
    Formulario personalizado para el modelo Client en el admin de Django.
    
    Agrega un campo extra 'admin_user' para seleccionar el usuario propietario
    del tenant al momento de la creación.
    
    ⚠️ VALIDACIÓN:
    - En creación (nuevo tenant): El campo 'admin_user' es OBLIGATORIO
    - En edición (tenant existente): El campo 'admin_user' es OPCIONAL
    """
    
    admin_user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        label="Usuario Propietario (Admin)",
        help_text="Seleccione el usuario global que administrará este tenant.",
        required=False,  # Se valida manualmente en clean()
        empty_label="-- Seleccione un usuario --"
    )
    
    class Meta:
        model = Client
        fields = '__all__'
    
    def clean(self):
        """
        Valida que se asigne un usuario propietario al crear un nuevo tenant.
        
        ⚠️ LÓGICA DE NEGOCIO:
        - Si es creación nueva (self.instance.pk is None):
            * El campo 'admin_user' es OBLIGATORIO
            * Si está vacío, lanza ValidationError
        - Si es edición (tenant ya existe):
            * El campo 'admin_user' es OPCIONAL
            * Permite dejar el campo vacío sin error
        """
        cleaned_data = super().clean()
        admin_user = cleaned_data.get('admin_user')
        
        # Verificar si es una creación nueva
        is_new_tenant = self.instance.pk is None
        
        # Si es creación nueva y no se asignó usuario propietario
        if is_new_tenant and not admin_user:
            raise forms.ValidationError(
                {
                    'admin_user': "Debe asignar un usuario propietario al crear un nuevo tenant."
                }
            )
        
        return cleaned_data