# core/models.py

from django.contrib.auth.models import AbstractUser, Group
from django.db import models


class UsuarioCustomizado(AbstractUser):
    """
    Modelo de Usuário Personalizado para adicionar campos de negócio.
    """
    # 1. Campo para a lógica de acesso por letras (A, B, C...)
    acesso_despesa = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name="Acesso a Despesas (Ex: A,B,C)",
        help_text="Letras que definem quais fornecedores o usuário pode ver."
    )

    # 2. Flag para Forçar Troca de Senha (Segurança)
    troca_senha_obrigatoria = models.BooleanField(
        default=True,
        verbose_name="Troca de Senha Obrigatória",
        help_text="O usuário deve alterar a senha no primeiro acesso."
    )

    def __str__(self):
        return self.username

    # A CLASSE GRUPO DEVE FICAR FORA DA CLASSE USUÁRIO (SEM RECUO)


class Grupo(Group):
    class Meta:
        proxy = True
        verbose_name = "Grupo"
        verbose_name_plural = "Grupos"