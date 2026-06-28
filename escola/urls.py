from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('api/dashboard/resumo-ia/', views.api_dashboard_resumo_ia, name='api_dashboard_resumo_ia'),
    path('escola/', views.CalendarioView.as_view(), name='calendario'),
    path('escola/toggle-dia/<str:data_str>/', views.toggle_dia_letivo, name='toggle_dia_letivo'),
    path('escola/gerar-calendario/', views.gerar_dias_letivos, name='gerar_dias_letivos'),
    path('escola/gerar-calendario/confirmar/', views.confirmar_geracao_dias_letivos, name='confirmar_geracao_dias_letivos'),
    path('escola/gerar-calendario/efetivar/', views.efetivar_geracao_dias_letivos, name='efetivar_geracao_dias_letivos'),
    path('escola/upload-bncc/', views.upload_bncc, name='upload_bncc'),
    path('escola/plano-aula/configurar/', views.configurar_plano, name='configurar_plano'),
    path('escola/api/normas/', views.api_get_normas, name='api_get_normas'),
    path('escola/api/sugerir-atividades/', views.api_sugerir_atividades, name='api_sugerir_atividades'),
    path('escola/plano-aula/gerar/', views.gerar_plano, name='gerar_plano'),
    path('escola/plano-aula/salvar/', views.salvar_plano, name='salvar_plano'),
    path('escola/plano-aula/<int:plano_id>/', views.visualizar_plano, name='visualizar_plano'),
    
    path('planejamento-geral/', views.planejamento_geral_config, name='planejamento_geral_config'),
    path('planejamento-geral/gerar/', views.planejamento_geral_gerar, name='planejamento_geral_gerar'),
    path('planejamento-geral/salvar/', views.planejamento_geral_salvar, name='planejamento_geral_salvar'),
    path('planejamento-geral/visualizar/<int:turma_id>/<int:materia_id>/<int:trimestre_id>/', views.planejamento_geral_visualizar, name='planejamento_geral_visualizar'),
    path('planejamento-geral/excluir/', views.planejamento_geral_excluir, name='planejamento_geral_excluir'),
    # Planejamento Diário Genérico
    path('plano-diario/generico/novo/<int:turma_id>/<int:dia_id>/', views.plano_diario_generico_novo, name='plano_diario_generico_novo'),
    path('plano-diario/generico/salvar/', views.plano_diario_generico_salvar, name='plano_diario_generico_salvar'),
    
    # Planejamento Diário
    path('plano-diario/abrir/<int:turma_id>/<int:dia_id>/', views.plano_diario_abrir, name='plano_diario_abrir'),
    path('plano-diario/excluir/<int:plano_id>/', views.plano_diario_excluir, name='plano_diario_excluir'),
    path('plano-diario/api/upload-atividade/', views.api_upload_atividade, name='api_upload_atividade'),
    path('plano-diario/api/salvar-dinamica/', views.api_salvar_dinamica, name='api_salvar_dinamica'),
    path('plano-diario/gerar-ia/', views.plano_diario_gerar, name='plano_diario_gerar'),
    path('plano-diario/salvar-manual/', views.plano_diario_salvar, name='plano_diario_salvar_manual'),
    path('plano-diario/finalizar/', views.plano_diario_finalizar, name='plano_diario_finalizar_manual'),
    path('plano-diario/visualizar/<int:plano_id>/', views.plano_diario_visualizar, name='plano_diario_visualizar_manual'),
    
    path('plano-diario/<int:plano_id>/salvar/', views.plano_diario_salvar, name='plano_diario_salvar'),
    path('plano-diario/<int:plano_id>/finalizar/', views.plano_diario_finalizar, name='plano_diario_finalizar'),
    path('plano-diario/<int:plano_id>/visualizar/', views.plano_diario_visualizar, name='plano_diario_visualizar'),
    path('plano-diario/<int:plano_id>/gerar-pdf/', views.gerar_plano_pdf, name='gerar_plano_pdf'),

    # Controle de Alunos
    path('controle-alunos/', views.controle_alunos_index, name='controle_alunos_index'),
    path('controle-alunos/<int:turma_id>/<int:dia_letivo_id>/', views.controle_alunos_chamada, name='controle_alunos_chamada'),

    # Relatórios Trimestrais
    path('relatorios/', views.relatorio_index, name='relatorio_index'),
    path('relatorios/turma/<int:turma_id>/trimestre/<int:trimestre_id>/', views.relatorio_turma, name='relatorio_turma'),
    path('relatorios/aluno/<int:aluno_id>/trimestre/<int:trimestre_id>/gerar/', views.relatorio_gerar_ia, name='relatorio_gerar_ia'),
    path('relatorios/revisar/<int:relatorio_id>/', views.relatorio_revisar, name='relatorio_revisar'),
    path('relatorios/gerar-pdf/<int:relatorio_id>/', views.relatorio_gerar_pdf, name='relatorio_gerar_pdf'),
]
