from rest_framework import serializers
from core.models import Processo


class ProcessoSerializer(serializers.ModelSerializer):
    """
    Serializer para o modelo Processo.
    Converte objetos Processo em JSON e vice-versa.
    """
    
    class Meta:
        model = Processo
        fields = '__all__'
