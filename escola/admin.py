from django.contrib import admin
from .models import Escola, Trimestre, Turma, Professor, Aluno, TemaPeriodo, DiaLetivo, AnoLetivo, Materia, DistribuicaoMateria

admin.site.register(Escola)
admin.site.register(Trimestre)
admin.site.register(Turma)
admin.site.register(Professor)
admin.site.register(AnoLetivo)

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

@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo')
    list_filter = ('tipo',)

@admin.register(DistribuicaoMateria)
class DistribuicaoMateriaAdmin(admin.ModelAdmin):
    list_display = ('turma', 'materia', 'frequencia', 'dia_semana', 'ordem_rodizio')
    list_filter = ('turma', 'frequencia', 'dia_semana')
    ordering = ('turma', 'dia_semana', 'ordem_rodizio')
