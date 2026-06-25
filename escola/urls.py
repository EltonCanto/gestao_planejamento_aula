from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('escola/', views.CalendarioView.as_view(), name='calendario'),
    path('escola/toggle-dia/<str:data_str>/', views.toggle_dia_letivo, name='toggle_dia_letivo'),
    path('escola/gerar-calendario/', views.gerar_dias_letivos, name='gerar_dias_letivos'),
    path('escola/upload-bncc/', views.upload_bncc, name='upload_bncc'),
    path('escola/plano-aula/configurar/', views.configurar_plano, name='configurar_plano'),
    path('escola/api/normas/', views.api_get_normas, name='api_get_normas'),
    path('escola/plano-aula/gerar/', views.gerar_plano, name='gerar_plano'),
    path('escola/plano-aula/salvar/', views.salvar_plano, name='salvar_plano'),
    path('escola/plano-aula/<int:plano_id>/', views.visualizar_plano, name='visualizar_plano'),
    
    path('planejamento-geral/', views.planejamento_geral_config, name='planejamento_geral_config'),
    path('planejamento-geral/gerar/', views.planejamento_geral_gerar, name='planejamento_geral_gerar'),
    path('planejamento-geral/salvar/', views.planejamento_geral_salvar, name='planejamento_geral_salvar'),
    path('planejamento-geral/visualizar/<int:turma_id>/<int:materia_id>/<int:trimestre_id>/', views.planejamento_geral_visualizar, name='planejamento_geral_visualizar'),
]
