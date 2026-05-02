class NormalizationMixin:
    """
    Mixin para normalizar campos a MAYÚSCULAS en serializers.
    Define 'normalization_fields' en el serializer.
    """
    normalization_fields = []

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        for field in self.normalization_fields:
            value = data.get(field)
            if isinstance(value, str):
                data[field] = value.upper()
        return data
