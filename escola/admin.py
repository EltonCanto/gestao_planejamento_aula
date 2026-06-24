from django.contrib import admin
from .models import Escola, Trimestre, Turma, Professor, Aluno, TemaPeriodo, DiaLetivo

admin.site.register(Escola)
admin.site.register(Trimestre)
admin.site.register(Turma)
admin.site.register(Professor)

@admin.register(Aluno)
class AlunoAdmin(admin.ModelAdmin):
    list_display = ('numero', 'nome', 'turma', 'turno')
    list_filter = ('turma', 'turno')
    search_fields = ('nome',)

@admin.register(TemaPeriodo)
class TemaPeriodoAdmin(admin.ModelAdmin):
    list_display = ('tema', 'data_inicial', 'data_final')

@admin.register(DiaLetivo)
class DiaLetivoAdmin(admin.ModelAdmin):
    list_display = ('data', 'eh_dia_letivo', 'observacao')
    list_filter = ('eh_dia_letivo',)
    list_editable = ('eh_dia_letivo', 'observacao')
    ordering = ('data',)
