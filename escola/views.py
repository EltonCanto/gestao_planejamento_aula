from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.utils import timezone
from .models import DiaLetivo, AnoLetivo, PlanoAula, AulaPlanejamentoGeral
import calendar
from datetime import date
from collections import defaultdict
from django.db.models import Count, Sum, Avg, Q, F
from django.db.models.functions import TruncMonth
from .models import Turma, Trimestre, Aluno, FrequenciaAluno, RegistroAulaTurma, PlanoDia, AtividadeDisciplina, NormaBNCC

@login_required
def dashboard(request):
    # Base Data for Filters
    anos = AnoLetivo.objects.all().order_by('-ano')
    turmas = Turma.objects.all()
    trimestres = Trimestre.objects.all()
    
    # Get filters
    ano_id = request.GET.get('ano')
    turma_id = request.GET.get('turma') or request.session.get('ultima_turma_calendario')
    trimestre_id = request.GET.get('trimestre')
    aluno_id = request.GET.get('aluno')
    
    if turma_id:
        request.session['ultima_turma_calendario'] = turma_id
        
    alunos = Aluno.objects.filter(turma_id=turma_id) if turma_id else Aluno.objects.all()
    
    # Base Querysets
    registros = RegistroAulaTurma.objects.all()
    planos = PlanoDia.objects.all()
    frequencias = FrequenciaAluno.objects.all()
    atividades = AtividadeDisciplina.objects.all()
    
    if ano_id:
        registros = registros.filter(dia_letivo__ano_letivo_id=ano_id)
        planos = planos.filter(dia_letivo__ano_letivo_id=ano_id)
        frequencias = frequencias.filter(registro_aula__dia_letivo__ano_letivo_id=ano_id)
        atividades = atividades.filter(plano_dia__dia_letivo__ano_letivo_id=ano_id)
        
    if turma_id:
        registros = registros.filter(turma_id=turma_id)
        planos = planos.filter(turma_id=turma_id)
        frequencias = frequencias.filter(registro_aula__turma_id=turma_id)
        atividades = atividades.filter(plano_dia__turma_id=turma_id)
        
    if trimestre_id:
        trimestre = Trimestre.objects.filter(id=trimestre_id).first()
        if trimestre:
            registros = registros.filter(dia_letivo__data__gte=trimestre.data_inicial, dia_letivo__data__lte=trimestre.data_final)
            planos = planos.filter(dia_letivo__data__gte=trimestre.data_inicial, dia_letivo__data__lte=trimestre.data_final)
            frequencias = frequencias.filter(registro_aula__dia_letivo__data__gte=trimestre.data_inicial, registro_aula__dia_letivo__data__lte=trimestre.data_final)
            atividades = atividades.filter(plano_dia__dia_letivo__data__gte=trimestre.data_inicial, plano_dia__dia_letivo__data__lte=trimestre.data_final)
            
    if aluno_id:
        frequencias = frequencias.filter(aluno_id=aluno_id)
        
    # KPIs - Visão Geral
    total_aulas = registros.count()
    aulas_ministradas = registros.filter(status='M').count()
    aulas_pendentes = registros.filter(status='P').count()
    aulas_canceladas = registros.filter(status='C').count()
    pct_aulas_realizadas = (aulas_ministradas / total_aulas * 100) if total_aulas > 0 else 0
    
    total_frequencias = frequencias.count()
    total_presencas = frequencias.filter(presente=True).count()
    total_faltas = total_frequencias - total_presencas
    media_frequencia = (total_presencas / total_frequencias * 100) if total_frequencias > 0 else 0
    
    ranking_faltas = FrequenciaAluno.objects.filter(registro_aula__in=registros, presente=False)\
        .values('aluno__nome')\
        .annotate(faltas=Count('id'))\
        .order_by('-faltas')[:5]
        
    total_planos = planos.count()
    planos_finalizados = planos.filter(finalizado=True).count()
    planos_pendentes = total_planos - planos_finalizados
    
    # Atividades
    total_atividades = atividades.count()
    
    # BNCC
    # Simples contagem de menções a códigos BNCC nos planos de aula consolidados
    # A base de dados real exigiria parse do texto, mas podemos contar planos com habilidades.
    planos_com_bncc = planos.exclude(habilidades_bncc='').count()
    
    # Alertas (Regras de Negócio)
    alertas = []
    if media_frequencia < 75 and total_frequencias > 0:
        alertas.append({"tipo": "danger", "mensagem": "Média de Frequência da turma está abaixo de 75%!"})
    if planos_pendentes > 5:
        alertas.append({"tipo": "warning", "mensagem": f"Existem {planos_pendentes} planos diários não finalizados."})
    if aulas_canceladas > 3:
        alertas.append({"tipo": "warning", "mensagem": f"Alto número de aulas canceladas ({aulas_canceladas})."})
        
    aluno_obj = None
    if aluno_id:
        aluno_obj = Aluno.objects.filter(id=aluno_id).first()
        if media_frequencia < 75:
            alertas.append({"tipo": "danger", "mensagem": f"O aluno {aluno_obj.nome} está com risco de reprovação por falta (Frequência: {media_frequencia:.1f}%)."})
            
    # Chart Data (Frequência por Mês)
    # Group by month
    freq_mensal = frequencias.annotate(mes=TruncMonth('registro_aula__dia_letivo__data'))\
        .values('mes')\
        .annotate(total=Count('id'), presencas=Count('id', filter=Q(presente=True)))\
        .order_by('mes')
        
    labels_freq = []
    data_freq = []
    for f in freq_mensal:
        if f['mes']:
            labels_freq.append(f['mes'].strftime('%b/%Y'))
            pct = (f['presencas'] / f['total'] * 100) if f['total'] > 0 else 0
            data_freq.append(round(pct, 1))

    context = {
        'anos': anos,
        'turmas': turmas,
        'trimestres': trimestres,
        'alunos': alunos,
        'filtros': {
            'ano_id': ano_id,
            'turma_id': turma_id,
            'trimestre_id': trimestre_id,
            'aluno_id': aluno_id
        },
        'aluno_obj': aluno_obj,
        'kpis': {
            'total_aulas': total_aulas,
            'aulas_ministradas': aulas_ministradas,
            'aulas_canceladas': aulas_canceladas,
            'pct_aulas_realizadas': round(pct_aulas_realizadas, 1),
            'media_frequencia': round(media_frequencia, 1),
            'total_faltas': total_faltas,
            'planos_criados': total_planos,
            'planos_finalizados': planos_finalizados,
            'planos_pendentes': planos_pendentes,
            'total_atividades': total_atividades,
            'planos_com_bncc': planos_com_bncc
        },
        'ranking_faltas': ranking_faltas,
        'alertas': alertas,
        'chart_labels': labels_freq,
        'chart_data': data_freq
    }
    
    return render(request, 'escola/dashboard.html', context)

from django.http import JsonResponse
from escola.services import gerar_resumo_dashboard_ia

@login_required
def api_dashboard_resumo_ia(request):
    try:
        # Pega os mesmos filtros da query string
        ano_id = request.GET.get('ano')
        turma_id = request.GET.get('turma') or request.session.get('ultima_turma_calendario')
        trimestre_id = request.GET.get('trimestre')
        aluno_id = request.GET.get('aluno')

        registros = RegistroAulaTurma.objects.all()
        planos = PlanoDia.objects.all()
        frequencias = FrequenciaAluno.objects.all()
        
        if ano_id:
            registros = registros.filter(dia_letivo__ano_letivo_id=ano_id)
            planos = planos.filter(dia_letivo__ano_letivo_id=ano_id)
            frequencias = frequencias.filter(registro_aula__dia_letivo__ano_letivo_id=ano_id)
            
        if turma_id:
            registros = registros.filter(turma_id=turma_id)
            planos = planos.filter(turma_id=turma_id)
            frequencias = frequencias.filter(registro_aula__turma_id=turma_id)
            
        if trimestre_id:
            trimestre = Trimestre.objects.filter(id=trimestre_id).first()
            if trimestre:
                registros = registros.filter(dia_letivo__data__gte=trimestre.data_inicial, dia_letivo__data__lte=trimestre.data_final)
                planos = planos.filter(dia_letivo__data__gte=trimestre.data_inicial, dia_letivo__data__lte=trimestre.data_final)
                frequencias = frequencias.filter(registro_aula__dia_letivo__data__gte=trimestre.data_inicial, registro_aula__dia_letivo__data__lte=trimestre.data_final)
                
        aluno_nome = None
        if aluno_id:
            frequencias = frequencias.filter(aluno_id=aluno_id)
            aluno_obj = Aluno.objects.filter(id=aluno_id).first()
            if aluno_obj: aluno_nome = aluno_obj.nome

        # KPIs basicos
        total_aulas = registros.count()
        aulas_ministradas = registros.filter(status='M').count()
        aulas_canceladas = registros.filter(status='C').count()
        
        total_freq = frequencias.count()
        total_presencas = frequencias.filter(presente=True).count()
        media_freq = (total_presencas / total_freq * 100) if total_freq > 0 else 0
        
        total_planos = planos.count()
        planos_finalizados = planos.filter(finalizado=True).count()
        planos_com_bncc = planos.exclude(habilidades_bncc='').count()

        # Montar a string de dados
        dados_texto = f"""
Filtro Aplicado:
- Aluno Específico: {aluno_nome if aluno_nome else 'Não (Visão de Turma)'}

Frequência e Aulas:
- Aulas Previstas: {total_aulas}
- Aulas Ministradas: {aulas_ministradas}
- Aulas Canceladas: {aulas_canceladas}
- Presenças Registradas: {total_presencas} de {total_freq}
- Média de Frequência: {media_freq:.1f}%

Planejamentos (Professor):
- Total de Planos Criados: {total_planos}
- Planos Finalizados: {planos_finalizados}
- Planos com Habilidades BNCC preenchidas: {planos_com_bncc}
        """

        resumo = gerar_resumo_dashboard_ia(dados_texto)
        return JsonResponse({'sucesso': True, 'resumo': resumo})
    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': str(e)}, status=500)

class CalendarioView(LoginRequiredMixin, ListView):
    model = DiaLetivo
    template_name = 'escola/calendario.html'
    context_object_name = 'dias'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Pega mes/ano da query string ou usa atual
        try:
            mes_atual = int(self.request.GET.get('mes', timezone.now().month))
            ano_atual = int(self.request.GET.get('ano', timezone.now().year))
        except ValueError:
            mes_atual = timezone.now().month
            ano_atual = timezone.now().year
            
        # Pega todos os dias do banco filtrados pelo ano
        dias_bd = {dia.data: dia for dia in DiaLetivo.objects.filter(data__year=ano_atual, data__month=mes_atual)}
        
        # Gera o calendario do mes
        cal = calendar.Calendar(firstweekday=6) # Domingo como primeiro dia
        mes_dias = cal.monthdatescalendar(ano_atual, mes_atual)
        
        calendario_estruturado = []
        for semana in mes_dias:
            semana_estruturada = []
            for dia in semana:
                if dia.month == mes_atual:
                    dia_bd = dias_bd.get(dia)
                    semana_estruturada.append({
                        'data': dia,
                        'eh_letivo': dia_bd.eh_dia_letivo if dia_bd else False,
                        'observacao': dia_bd.observacao if dia_bd else '',
                        'no_banco': bool(dia_bd)
                    })
                else:
                    semana_estruturada.append(None)
            calendario_estruturado.append(semana_estruturada)
            
        # Calcula proximo e anterior
        if mes_atual == 12:
            prox_mes, prox_ano = 1, ano_atual + 1
        else:
            prox_mes, prox_ano = mes_atual + 1, ano_atual
            
        if mes_atual == 1:
            ant_mes, ant_ano = 12, ano_atual - 1
        else:
            ant_mes, ant_ano = mes_atual - 1, ano_atual
            
        from .models import Turma, PlanoDia
        turmas = Turma.objects.all()
        
        turma_id = self.request.GET.get('turma')
        if turma_id:
            self.request.session['ultima_turma_calendario'] = turma_id
        else:
            turma_id = self.request.session.get('ultima_turma_calendario')
        
        # Mapear os planos diários para a turma selecionada
        planos_bd = {}
        if turma_id and str(turma_id).isdigit():
            planos_bd = {p.dia_letivo_id: p for p in PlanoDia.objects.filter(
                turma_id=turma_id, 
                dia_letivo__data__year=ano_atual, 
                dia_letivo__data__month=mes_atual
            )}
        
        # Injetar dia id e plano no calendário estruturado
        for semana in calendario_estruturado:
            for dia_dict in semana:
                if dia_dict and dia_dict['no_banco']:
                    dia_obj = DiaLetivo.objects.filter(data=dia_dict['data']).first()
                    if dia_obj:
                        dia_dict['id'] = dia_obj.id
                        plano_associado = planos_bd.get(dia_obj.id)
                        dia_dict['tem_plano'] = True if plano_associado else False
                        if plano_associado:
                            dia_dict['plano_id'] = plano_associado.id
                            dia_dict['plano_finalizado'] = plano_associado.finalizado
                    else:
                        dia_dict['id'] = None
                        dia_dict['tem_plano'] = False
                        dia_dict['plano_finalizado'] = False
            
        context['calendario'] = calendario_estruturado
        context['mes_atual'] = mes_atual
        context['ano_atual'] = ano_atual
        context['prox_mes'] = prox_mes
        context['prox_ano'] = prox_ano
        context['ant_mes'] = ant_mes
        context['ant_ano'] = ant_ano
        context['turmas'] = turmas
        context['turma_selecionada'] = int(turma_id) if turma_id and str(turma_id).isdigit() else None
        return context

from django.contrib import messages
from datetime import datetime, timedelta

def calcular_pascoa(ano):
    a = ano % 19
    b = ano // 100
    c = ano % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return datetime(ano, mes, dia).date()

def get_feriados(ano):
    feriados_fixos = [
        (1, 1, 'Confraternização Universal'),
        (4, 21, 'Tiradentes'),
        (4, 23, 'São Jorge (Feriado Estadual RJ)'),
        (5, 1, 'Dia do Trabalhador'),
        (6, 13, 'Santo Antônio (Padroeiro de Teresópolis)'),
        (7, 6, 'Aniversário de Teresópolis'),
        (9, 7, 'Independência do Brasil'),
        (10, 12, 'Nossa Senhora Aparecida'),
        (10, 15, 'Dia do Professor (Recesso Escolar)'),
        (11, 2, 'Finados'),
        (11, 15, 'Proclamação da República'),
        (11, 20, 'Dia Nacional de Zumbi e da Consciência Negra'),
        (12, 25, 'Natal'),
    ]
    
    pascoa = calcular_pascoa(ano)
    carnaval = pascoa - timedelta(days=47)
    paixao_cristo = pascoa - timedelta(days=2)
    corpus_christi = pascoa + timedelta(days=60)
    
    feriados = {
        carnaval: 'Carnaval',
        paixao_cristo: 'Sexta-feira Santa (Paixão de Cristo)',
        pascoa: 'Páscoa',
        corpus_christi: 'Corpus Christi'
    }
    
    for mes, dia, nome in feriados_fixos:
        feriados[datetime(ano, mes, dia).date()] = nome
        
    return feriados

@login_required
def gerar_dias_letivos(request):
    if request.method == 'POST':
        data_inicial_str = request.POST.get('data_inicial')
        data_final_str = request.POST.get('data_final')
        
        if not data_inicial_str or not data_final_str:
            messages.error(request, "Datas inválidas.")
            return redirect('calendario')
            
        try:
            data_inicial = datetime.strptime(data_inicial_str, '%Y-%m-%d').date()
            data_final = datetime.strptime(data_final_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Formato de data inválido.")
            return redirect('calendario')
            
        if data_inicial > data_final:
            messages.error(request, "A data inicial deve ser anterior ou igual à data final.")
            return redirect('calendario')

        # Buscar AnoLetivo corrente
        ano_corrente_obj = AnoLetivo.objects.filter(corrente=True).first()
        if not ano_corrente_obj:
            messages.error(request, "Nenhum Ano Letivo corrente configurado no sistema. Por favor, crie um no painel Admin.")
            return redirect('calendario')

        if data_inicial.year != ano_corrente_obj.ano or data_final.year != ano_corrente_obj.ano:
            messages.error(request, f"O ano das datas informadas difere do Ano Letivo corrente ({ano_corrente_obj.ano}).")
            return redirect('calendario')

        # Verificar se existem planejamentos
        tem_plano = PlanoAula.objects.filter(dia_letivo__ano_letivo=ano_corrente_obj).exists()
        tem_geral = AulaPlanejamentoGeral.objects.filter(dia_letivo__ano_letivo=ano_corrente_obj).exists()

        if tem_plano or tem_geral:
            messages.error(request, "Já existem planejamentos criados para o Ano Letivo corrente. A geração automática está bloqueada. Faça ajustes nos dias manualmente.")
            return redirect('calendario')

        # Verificar se já existem DiasLetivos criados para o ano
        dias_existentes = DiaLetivo.objects.filter(ano_letivo=ano_corrente_obj).count()
        if dias_existentes > 0:
            request.session['gerar_calendario_dados'] = {
                'data_inicial': data_inicial_str,
                'data_final': data_final_str
            }
            return redirect('confirmar_geracao_dias_letivos')
            
        # Se não existe, efetiva direto
        request.session['gerar_calendario_dados'] = {
            'data_inicial': data_inicial_str,
            'data_final': data_final_str
        }
        return redirect('efetivar_geracao_dias_letivos')
        
    return redirect('calendario')

@login_required
def confirmar_geracao_dias_letivos(request):
    dados = request.session.get('gerar_calendario_dados')
    if not dados:
        return redirect('calendario')
    
    ano_corrente = AnoLetivo.objects.filter(corrente=True).first()
    dias_existentes = DiaLetivo.objects.filter(ano_letivo=ano_corrente).count()
    
    return render(request, 'escola/confirmar_geracao.html', {
        'dados': dados,
        'ano': ano_corrente,
        'dias_existentes': dias_existentes
    })

@login_required
def efetivar_geracao_dias_letivos(request):
    dados = request.session.get('gerar_calendario_dados')
    if not dados:
        return redirect('calendario')
        
    data_inicial = datetime.strptime(dados['data_inicial'], '%Y-%m-%d').date()
    data_final = datetime.strptime(dados['data_final'], '%Y-%m-%d').date()
    
    ano_corrente_obj = AnoLetivo.objects.filter(corrente=True).first()
    
    # Deletar antigos
    DiaLetivo.objects.filter(ano_letivo=ano_corrente_obj).delete()
    
    delta = data_final - data_inicial
    feriados = get_feriados(ano_corrente_obj.ano)
    
    for i in range(delta.days + 1):
        dia = data_inicial + timedelta(days=i)
        if dia.weekday() < 5:
            is_feriado = dia in feriados
            nome_feriado = feriados.get(dia, '')
            
            eh_letivo = not is_feriado
            
            DiaLetivo.objects.create(
                data=dia,
                ano_letivo=ano_corrente_obj,
                eh_dia_letivo=eh_letivo,
                observacao=nome_feriado
            )
                
    dias_criados = DiaLetivo.objects.filter(ano_letivo=ano_corrente_obj, eh_dia_letivo=True).count()
    feriados_marcados = DiaLetivo.objects.filter(ano_letivo=ano_corrente_obj, eh_dia_letivo=False).count()
    
    if 'gerar_calendario_dados' in request.session:
        del request.session['gerar_calendario_dados']
    
    messages.success(request, f"Calendário gerado! {dias_criados} dias letivos reais criados e {feriados_marcados} dias marcados como 'Sem Aula' (feriados).")
    return redirect(f"/escola/?ano={data_inicial.year}&mes={data_inicial.month}")

@login_required
def toggle_dia_letivo(request, data_str):
    if request.method == 'POST':
        # data_str formato: YYYY-MM-DD
        partes = data_str.split('-')
        if len(partes) == 3:
            data_obj = date(int(partes[0]), int(partes[1]), int(partes[2]))
            ano_corrente = AnoLetivo.objects.filter(corrente=True).first()
            if not ano_corrente:
                messages.error(request, "É necessário configurar um Ano Letivo corrente no painel Admin primeiro.")
                return redirect('calendario')
                
            dia, created = DiaLetivo.objects.get_or_create(data=data_obj, defaults={'eh_dia_letivo': False, 'ano_letivo': ano_corrente})
            
            if 'alternar' in request.POST:
                if not created:
                    dia.eh_dia_letivo = not dia.eh_dia_letivo
                else:
                    dia.eh_dia_letivo = True
            
            if 'observacao' in request.POST:
                dia.observacao = request.POST.get('observacao')
                
            dia.save()
            return redirect(f"/escola/?ano={data_obj.year}&mes={data_obj.month}")
    return redirect('calendario')

import os
from django.core.files.storage import FileSystemStorage
from django.contrib import messages
from .models import Materia, NormaBNCC, Trimestre
from .services import processar_pdf_bncc

@login_required
def upload_bncc(request):
    trimestres = Trimestre.objects.all()
    if request.method == 'POST' and request.FILES.getlist('pdf_file'):
        pdf_files = request.FILES.getlist('pdf_file')
        tipo_materia = request.POST.get('tipo_materia') # 'G' ou 'E'
        trimestre_id = request.POST.get('trimestre_id')
        
        fs = FileSystemStorage()
        salvas_por_materia = defaultdict(int)
        total_processadas = 0
        erros = []
        
        for pdf_file in pdf_files:
            filename = fs.save(pdf_file.name, pdf_file)
            file_path = fs.path(filename)
            
            try:
                # Chama o serviço do LangChain
                normas_extraidas = processar_pdf_bncc(file_path, is_geral=(tipo_materia == 'G'))
                
                trimestre = None
                if tipo_materia == 'E' and trimestre_id:
                    trimestre = Trimestre.objects.get(id=trimestre_id)
                
                for item in normas_extraidas:
                    codigo = item.get('codigo')
                    descricao = item.get('descricao')
                    nome_materia = item.get('materia', 'Geral')
                    
                    if codigo and descricao:
                        # Encontra ou cria a matéria
                        materia_obj, _ = Materia.objects.get_or_create(nome=nome_materia, defaults={'tipo': tipo_materia})
                        
                        # Salva a norma
                        norma, created = NormaBNCC.objects.get_or_create(
                            codigo=codigo,
                            materia=materia_obj,
                            trimestre=trimestre,
                            defaults={'descricao': descricao}
                        )
                        salvas_por_materia[nome_materia] += 1
                        total_processadas += 1
            except Exception as e:
                erros.append(f"Erro no arquivo {pdf_file.name}: {str(e)}")
            finally:
                # Apaga o arquivo temporário
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
        if total_processadas > 0:
            detalhes = ", ".join([f"{qtd} de {mat}" for mat, qtd in salvas_por_materia.items()])
            messages.success(request, f'Processamento concluído com sucesso! {total_processadas} normas da BNCC foram processadas: {detalhes}.')
        elif not erros:
            messages.warning(request, "Nenhuma norma foi encontrada ou extraída deste arquivo PDF.")
            
        if erros:
            for err in erros:
                messages.error(request, err)
                
        return redirect('upload_bncc')
        
    return render(request, 'escola/upload_bncc.html', {'trimestres': trimestres})

from django.http import JsonResponse
from .models import Turma, PlanoAula
from django.shortcuts import get_object_or_404
from .services import gerar_plano_com_ia

@login_required
def configurar_plano(request):
    turmas = Turma.objects.all()
    materias = Materia.objects.all()
    trimestres = Trimestre.objects.all()
    dias = DiaLetivo.objects.filter(eh_dia_letivo=True).order_by('data')
    return render(request, 'escola/configurar_plano.html', {
        'turmas': turmas,
        'materias': materias,
        'trimestres': trimestres,
        'dias': dias
    })

@login_required
def api_get_normas(request):
    materia_id = request.GET.get('materia_id')
    trimestre_id = request.GET.get('trimestre_id')
    
    normas = NormaBNCC.objects.all()
    if materia_id:
        normas = normas.filter(materia_id=materia_id)
    if trimestre_id:
        normas = normas.filter(trimestre_id=trimestre_id)
        
    dados = [{'id': n.id, 'codigo': n.codigo, 'descricao': n.descricao} for n in normas]
    return JsonResponse({'normas': dados})

import json
from django.views.decorators.http import require_POST
from .services import sugerir_atividades_ia

@require_POST
@login_required
def api_sugerir_atividades(request):
    try:
        data = json.loads(request.body)
        turma_id = data.get('turma_id')
        tema = data.get('tema')
        normas_ids = data.get('normas_ids', [])
        
        turma = get_object_or_404(Turma, id=turma_id)
        normas = NormaBNCC.objects.filter(id__in=normas_ids)
        normas_texto = "\n".join([f"[{n.codigo}] {n.descricao}" for n in normas])
        
        if not tema or not normas_ids:
            return JsonResponse({'sucesso': False, 'erro': 'Preencha o tema e selecione as habilidades.'})
            
        sugestoes = sugerir_atividades_ia(turma.nome, tema, normas_texto)
        return JsonResponse({'sucesso': True, 'sugestoes': sugestoes})
    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': str(e)})

@login_required
def gerar_plano(request):
    if request.method == 'POST':
        turma_id = request.POST.get('turma')
        materia_id = request.POST.get('materia')
        dia_id = request.POST.get('dia_letivo')
        normas_ids = request.POST.getlist('normas')
        
        turma = get_object_or_404(Turma, id=turma_id)
        materia = get_object_or_404(Materia, id=materia_id)
        dia = get_object_or_404(DiaLetivo, id=dia_id)
        
        normas = NormaBNCC.objects.filter(id__in=normas_ids)
        normas_texto = "\n".join([f"[{n.codigo}] {n.descricao}" for n in normas])
        
        try:
            # Chama a IA
            resultado = gerar_plano_com_ia(turma.nome, materia.nome, normas_texto)
            
            # Passa pro template que permite edição
            context = {
                'turma': turma,
                'materia': materia,
                'dia_letivo': dia,
                'plano': resultado # dict vindo do JSON da IA
            }
            return render(request, 'escola/editar_plano_gerado.html', context)
        except Exception as e:
            messages.error(request, f"Erro ao gerar plano com IA: {str(e)}")
            return redirect('configurar_plano')
            
    return redirect('configurar_plano')

@login_required
def salvar_plano(request):
    if request.method == 'POST':
        turma_id = request.POST.get('turma_id')
        materia_id = request.POST.get('materia_id')
        dia_id = request.POST.get('dia_id')
        
        plano, created = PlanoAula.objects.update_or_create(
            turma_id=turma_id,
            materia_id=materia_id,
            dia_letivo_id=dia_id,
            defaults={
                'objeto_conhecimento': request.POST.get('objeto_conhecimento'),
                'habilidades_bncc': request.POST.get('habilidades_bncc'),
                'objetivos_especificos': request.POST.get('objetivos_especificos'),
                'recursos': request.POST.get('recursos'),
                'avaliacao': request.POST.get('avaliacao'),
            }
        )
        messages.success(request, "Plano de aula salvo com sucesso!")
        return redirect('visualizar_plano', plano_id=plano.id)
        
    return redirect('configurar_plano')

@login_required
def visualizar_plano(request, plano_id):
    plano = get_object_or_404(PlanoAula, id=plano_id)
    return render(request, 'escola/plano_aula.html', {
        'turma': plano.turma.nome,
        'componente': plano.materia.nome,
        'data': plano.dia_letivo.data.strftime('%d/%m/%Y'),
        'objeto': plano.objeto_conhecimento,
        'habilidades': plano.habilidades_bncc,
        'objetivos': plano.objetivos_especificos,
        'recursos': plano.recursos,
        'avaliacao': plano.avaliacao,
    })

from .models import AulaPlanejamentoGeral, DistribuicaoMateria
from .services import distribuir_normas_homogeneamente

@login_required
def planejamento_geral_config(request):
    turmas = Turma.objects.all()
    materias = Materia.objects.all()
    trimestres = Trimestre.objects.all()
    return render(request, 'escola/planejamento_geral_config.html', {
        'turmas': turmas,
        'materias': materias,
        'trimestres': trimestres
    })

@login_required
def planejamento_geral_gerar(request):
    if request.method == 'POST':
        turma_id = request.POST.get('turma')
        materia_id = request.POST.get('materia')
        trimestre_id = request.POST.get('trimestre')
        
        turma = get_object_or_404(Turma, id=turma_id)
        materia = get_object_or_404(Materia, id=materia_id)
        trimestre = get_object_or_404(Trimestre, id=trimestre_id)
        
        # Checar se já existe planejamento salvo
        if AulaPlanejamentoGeral.objects.filter(turma=turma, materia=materia, trimestre=trimestre).exists():
            messages.warning(request, "Já existe um planejamento salvo para esta Turma, Matéria e Trimestre. Para gerar um novo, exclua o atual.")
            return redirect('planejamento_geral_visualizar', turma_id=turma.id, materia_id=materia.id, trimestre_id=trimestre.id)

        # Pega dias letivos no trimestre
        dias_qs = DiaLetivo.objects.filter(
            eh_dia_letivo=True,
            data__gte=trimestre.data_inicial,
            data__lte=trimestre.data_final
        ).order_by('data')
        
        distribuicao = DistribuicaoMateria.objects.filter(turma=turma, materia=materia).first()
        dias = list(dias_qs)
        
        if distribuicao:
            if distribuicao.frequencia == 'FIXO':
                dias = [d for d in dias if d.data.weekday() == distribuicao.dia_semana]
            elif distribuicao.frequencia == 'RODIZIO':
                rodizio_deste_dia = DistribuicaoMateria.objects.filter(
                    turma=turma, 
                    frequencia='RODIZIO', 
                    dia_semana=distribuicao.dia_semana
                ).order_by('ordem_rodizio', 'materia__nome')
                
                materias_rodizio = list(rodizio_deste_dia.values_list('materia_id', flat=True))
                
                if materia.id in materias_rodizio:
                    idx_materia = materias_rodizio.index(materia.id)
                    total_rodizio = len(materias_rodizio)
                    
                    if dias_qs.exists():
                        ano_corrente = dias_qs.first().ano_letivo
                        todos_dias_rodizio = DiaLetivo.objects.filter(
                            eh_dia_letivo=True,
                            ano_letivo=ano_corrente
                        ).order_by('data')
                        
                        todos_dias_rodizio = [d for d in todos_dias_rodizio if d.data.weekday() == distribuicao.dia_semana]
                        
                        dias_da_materia = []
                        for i, d in enumerate(todos_dias_rodizio):
                            if (i % total_rodizio) == idx_materia:
                                dias_da_materia.append(d.id)
                                
                        dias = [d for d in dias if d.id in dias_da_materia]
        
        if not dias:
            messages.error(request, "Não há dias letivos cadastrados ou disponíveis para esta matéria neste trimestre, de acordo com a Grade Curricular.")
            return redirect('planejamento_geral_config')
            
        # Pega as normas da matéria para o trimestre (ou normas gerais sem trimestre)
        from django.db.models import Q
        normas = NormaBNCC.objects.filter(Q(trimestre=trimestre) | Q(trimestre__isnull=True), materia=materia)
        if not normas.exists():
            messages.error(request, "Não há normas da BNCC cadastradas para esta matéria no trimestre selecionado.")
            return redirect('planejamento_geral_config')
            
        try:
            from .services import distribuir_normas_homogeneamente
            distribuicao = distribuir_normas_homogeneamente(dias, list(normas))
            
            # Formatar para a tela de revisão
            plano_revisao = []
            for d in distribuicao:
                dia_obj = next((dia for dia in dias if str(dia.data) == str(d.get('data'))), None)
                if dia_obj:
                    codigos = d.get('normas_codigos', [])
                    norma_principal = codigos[0] if codigos else None
                    normas_objs = normas.filter(codigo__in=codigos)
                    plano_revisao.append({
                        'dia': dia_obj,
                        'tema': d.get('tema', ''),
                        'sugestao': d.get('sugestao', ''),
                        'norma_principal': norma_principal,
                        'normas': normas_objs
                    })
            
            context = {
                'turma': turma,
                'materia': materia,
                'trimestre': trimestre,
                'todas_normas': normas,
                'plano_revisao': plano_revisao
            }
            return render(request, 'escola/planejamento_geral_revisao.html', context)
        except Exception as e:
            messages.error(request, str(e))
            return redirect('planejamento_geral_config')
            
    return redirect('planejamento_geral_config')

@login_required
def planejamento_geral_salvar(request):
    if request.method == 'POST':
        turma_id = request.POST.get('turma_id')
        materia_id = request.POST.get('materia_id')
        trimestre_id = request.POST.get('trimestre_id')
        
        dias_ids = request.POST.getlist('dia_id[]')
        temas = request.POST.getlist('tema[]')
        sugestoes_lista = request.POST.getlist('sugestoes[]')
        
        # Limpa o planejamento anterior para essa mesma turma, materia e dia
        # Ou faz update. Vamos usar update_or_create
        for i, dia_id in enumerate(dias_ids):
            tema = temas[i] if i < len(temas) else ''
            sugestao = sugestoes_lista[i] if i < len(sugestoes_lista) else ''
            
            aula, created = AulaPlanejamentoGeral.objects.update_or_create(
                turma_id=turma_id,
                materia_id=materia_id,
                dia_letivo_id=dia_id,
                defaults={
                    'trimestre_id': trimestre_id,
                    'tema_aula': tema,
                    'sugestoes_atividades': sugestao
                }
            )
            # Salvar normas (ManyToMany)
            # Os checkboxes tem name "normas_dia_X" onde X é o dia_id
            normas_selecionadas = request.POST.getlist(f'normas_dia_{dia_id}')
            if normas_selecionadas:
                aula.normas.set(normas_selecionadas)
            else:
                aula.normas.clear()
                
        messages.success(request, "Planejamento Geral salvo com sucesso!")
        return redirect('planejamento_geral_visualizar', turma_id=turma_id, materia_id=materia_id, trimestre_id=trimestre_id)
        
    return redirect('planejamento_geral_config')

@login_required
def planejamento_geral_visualizar(request, turma_id, materia_id, trimestre_id):
    turma = get_object_or_404(Turma, id=turma_id)
    materia = get_object_or_404(Materia, id=materia_id)
    trimestre = get_object_or_404(Trimestre, id=trimestre_id)
    
    aulas = AulaPlanejamentoGeral.objects.filter(
        turma=turma,
        materia=materia,
        trimestre=trimestre
    ).order_by('dia_letivo__data')
    
    return render(request, 'escola/planejamento_geral_visualizar.html', {
        'turma': turma,
        'materia': materia,
        'trimestre': trimestre,
        'aulas': aulas
    })

@login_required
def planejamento_geral_excluir(request):
    if request.method == 'POST':
        turma_id = request.POST.get('turma_id')
        materia_id = request.POST.get('materia_id')
        trimestre_id = request.POST.get('trimestre_id')
        
        # Apaga todos os registros dessa tríade
        apagados, _ = AulaPlanejamentoGeral.objects.filter(
            turma_id=turma_id,
            materia_id=materia_id,
            trimestre_id=trimestre_id
        ).delete()
        
        from django.contrib import messages
        messages.success(request, f"Planejamento excluído com sucesso! Você pode agora gerar um novo.")
        return redirect('planejamento_geral_config')
    
    return redirect('planejamento_geral_config')

# --- Planejamento Diário ---
from .models import PlanoDia, AtividadeDisciplina, ArquivoAtividade
from .google_drive import upload_arquivo
from .services import extrair_texto_arquivo, resumir_arquivo_ia, gerar_plano_diario_completo_ia

@login_required
def plano_diario_abrir(request, turma_id, dia_id):
    turma = get_object_or_404(Turma, id=turma_id)
    dia = get_object_or_404(DiaLetivo, id=dia_id)
    
    # 1. Puxar informações do Planejamento Geral (aulas daquele dia para a turma)
    aulas_gerais = AulaPlanejamentoGeral.objects.filter(turma=turma, dia_letivo=dia).order_by('materia__nome')
    if not aulas_gerais.exists():
        # Redireciona para o fluxo genérico
        return redirect('plano_diario_generico_novo', turma_id=turma_id, dia_id=dia_id)
        
    trimestre = aulas_gerais.first().trimestre
    
    # 2. Criar ou Obter o PlanoDia
    plano_dia, created = PlanoDia.objects.get_or_create(
        turma=turma, 
        dia_letivo=dia,
        defaults={'trimestre': trimestre}
    )
    
    # 3. Criar os blocos de AtividadeDisciplina caso não existam e agrupar com aula geral
    atividades_com_aulas = []
    for aula in aulas_gerais:
        atividade, _ = AtividadeDisciplina.objects.get_or_create(
            plano_dia=plano_dia,
            materia=aula.materia
        )
        atividades_com_aulas.append({
            'atividade': atividade,
            'aula_geral': aula
        })
    
    context = {
        'plano': plano_dia,
        'turma': turma,
        'dia': dia,
        'atividades_com_aulas': atividades_com_aulas,
    }
    
    if plano_dia.finalizado:
        return redirect('plano_diario_visualizar', plano_id=plano_dia.id)
        
    return render(request, 'escola/plano_diario_edicao.html', context)

@require_POST
@login_required
def plano_diario_excluir(request, plano_id):
    plano_dia = get_object_or_404(PlanoDia, id=plano_id)
    turma_id = plano_dia.turma_id
    plano_dia.delete()
    messages.success(request, "Planejamento diário excluído com sucesso.")
    # Redirecionar de volta para o calendário mantendo a turma
    return redirect(f"/escola/?turma={turma_id}")

@require_POST
@login_required
def api_upload_atividade(request):
    atividade_id = request.POST.get('atividade_id')
    arquivo = request.FILES.get('arquivo')
    
    if not arquivo or not atividade_id:
        return JsonResponse({'sucesso': False, 'erro': 'Faltando arquivo ou atividade.'})
        
    atividade = get_object_or_404(AtividadeDisciplina, id=atividade_id)
    
    # Busca a primeira norma vinculada a essa materia no planejamento geral do dia
    aula_geral = AulaPlanejamentoGeral.objects.filter(
        turma=atividade.plano_dia.turma,
        dia_letivo=atividade.plano_dia.dia_letivo,
        materia=atividade.materia
    ).first()
    
    codigo_bncc = "SemBNCC"
    if aula_geral and aula_geral.normas.exists():
        codigo_bncc = aula_geral.normas.first().codigo
        
    # Salvar temporariamente
    from django.core.files.storage import FileSystemStorage
    fs = FileSystemStorage()
    filename = fs.save(arquivo.name, arquivo)
    caminho_local = fs.path(filename)
    
    # Extrair extensão para a lógica de texto e OCR
    extensao = os.path.splitext(filename)[1].replace('.', '')
    texto_extraido = extrair_texto_arquivo(caminho_local, extensao)
    
    # IA resume o documento e cria titulo curto
    resumo, titulo_curto = resumir_arquivo_ia(texto_extraido)
    
    # Gerar o nome padrão: atividade_<Matéria>_<Código_BNCC>_<TituloCurto>
    titulo_curto = titulo_curto.replace(' ', '_').replace('/', '_')[:30]
    materia_nome = atividade.materia.nome.replace(' ', '')
    nome_destino = f"atividade_{materia_nome}_{codigo_bncc}_{titulo_curto}.{extensao}"
    
    try:
        # Upload Google Drive
        drive_id, link = upload_arquivo(caminho_local, nome_destino)
        
        # Salvar BD
        arq = ArquivoAtividade.objects.create(
            atividade=atividade,
            drive_id=drive_id,
            link=link,
            nome_arquivo=nome_destino,
            texto_extraido=texto_extraido,
            resumo_ia=resumo
        )
        
        # Apaga o temp local
        os.remove(caminho_local)
        
        return JsonResponse({
            'sucesso': True, 
            'arquivo': {
                'id': arq.id,
                'nome': arq.nome_arquivo,
                'link': arq.link,
                'resumo': arq.resumo_ia
            }
        })
    except Exception as e:
        if os.path.exists(caminho_local):
            os.remove(caminho_local)
        return JsonResponse({'sucesso': False, 'erro': str(e)})

@require_POST
@login_required
def api_salvar_dinamica(request):
    try:
        data = json.loads(request.body)
        atividade_id = data.get('atividade_id')
        texto = data.get('texto')
        
        atividade = AtividadeDisciplina.objects.get(id=atividade_id)
        atividade.dinamica = texto
        atividade.save()
        return JsonResponse({'sucesso': True})
    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': str(e)})

@login_required
def plano_diario_gerar(request):
    if request.method == 'POST':
        plano_id = request.POST.get('plano_id')
        plano = get_object_or_404(PlanoDia, id=plano_id)
        
        aulas_gerais = AulaPlanejamentoGeral.objects.filter(turma=plano.turma, dia_letivo=plano.dia_letivo)
        atividades = AtividadeDisciplina.objects.filter(plano_dia=plano)
        
        # Montar "Contexto do Dia" String
        contexto = []
        contexto.append(f"TURMA: {plano.turma.nome} - {plano.turma.ano}")
        if plano.trimestre:
            contexto.append(f"TRIMESTRE: {plano.trimestre.nome}")
            
        for aula in aulas_gerais:
            contexto.append(f"\n--- DISCIPLINA: {aula.materia.nome} ---")
            contexto.append(f"Tema Planejado (Foco): {aula.tema_aula}")
            
            normas = aula.normas.all()
            if normas:
                contexto.append("Habilidades BNCC vinculadas:")
                for n in normas:
                    contexto.append(f" - {n.codigo}: {n.descricao}")
                    
            contexto.append(f"Sugestão prévia de atividade: {aula.sugestoes_atividades}")
            
            # Buscar a atividade e arquivos que o prof adicionou
            ativ = atividades.filter(materia=aula.materia).first()
            if ativ:
                if ativ.dinamica:
                    contexto.append(f"Dinâmica Cadastrada pelo Professor:\n{ativ.dinamica}")
                
                arquivos = ativ.arquivos.all()
                if arquivos:
                    contexto.append("Resumo dos Materiais Anexados nesta aula:")
                    for arq in arquivos:
                        contexto.append(f"  - {arq.nome_arquivo} (Resumo IA: {arq.resumo_ia})")
        
        contexto_str = "\n".join(contexto)
        
        try:
            resultado_json = gerar_plano_diario_completo_ia(contexto_str)
            
            # Atualiza o plano
            plano.objeto_conhecimento = resultado_json.get('objeto_conhecimento', '')
            plano.habilidades_bncc = resultado_json.get('habilidades_bncc', '')
            plano.objetivos_especificos = resultado_json.get('objetivos_especificos', '')
            plano.recursos = resultado_json.get('recursos', '')
            plano.avaliacao = resultado_json.get('avaliacao', 'A avaliação será realizada de forma contínua...')
            plano.componentes_curriculares = resultado_json.get('componentes_curriculares', '')
            plano.conteudo_ministrado = resultado_json.get('conteudo_ministrado', '')
            plano.save()
            
            messages.success(request, "Plano consolidado com sucesso através da IA!")
        except Exception as e:
            messages.error(request, f"Erro ao gerar com IA: {e}")
            
        return redirect('plano_diario_abrir', turma_id=plano.turma.id, dia_id=plano.dia_letivo.id)
    return redirect('calendario')

@login_required
def plano_diario_salvar(request, plano_id=None):
    if request.method == 'POST':
        plano_id = plano_id or request.POST.get('plano_id')
        plano = get_object_or_404(PlanoDia, id=plano_id)
        
        plano.objeto_conhecimento = request.POST.get('objeto_conhecimento', '')
        plano.habilidades_bncc = request.POST.get('habilidades_bncc', '')
        plano.objetivos_especificos = request.POST.get('objetivos_especificos', '')
        plano.recursos = request.POST.get('recursos', '')
        plano.avaliacao = request.POST.get('avaliacao', '')
        plano.componentes_curriculares = request.POST.get('componentes_curriculares', '')
        plano.conteudo_ministrado = request.POST.get('conteudo_ministrado', '')
        plano.save()
        
        # Pode ser chamada via AJAX ou submit normal
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'sucesso': True})
            
        messages.success(request, "Alterações salvas!")
        return redirect('plano_diario_abrir', turma_id=plano.turma.id, dia_id=plano.dia_letivo.id)

@login_required
def plano_diario_finalizar(request, plano_id=None):
    if request.method == 'POST':
        plano_id = plano_id or request.POST.get('plano_id')
        plano = get_object_or_404(PlanoDia, id=plano_id)
        
        plano.finalizado = True
        plano.save()
        messages.success(request, "Plano de Aula Diário finalizado e bloqueado para edições!")
        return redirect('plano_diario_visualizar', plano_id=plano.id)
        
@login_required
def plano_diario_visualizar(request, plano_id):
    plano = get_object_or_404(PlanoDia, id=plano_id)
    try:
        doc = plano.documento_pdf
    except Exception:
        doc = None
    return render(request, 'escola/plano_diario_finalizado.html', {'plano': plano, 'documento_pdf': doc})

import json

@login_required
def plano_diario_generico_novo(request, turma_id, dia_id):
    turma = get_object_or_404(Turma, id=turma_id)
    dia = get_object_or_404(DiaLetivo, id=dia_id)
    
    materias = Materia.objects.all()
    
    normas_por_materia = {}
    for m in materias:
        normas_por_materia[m.id] = list(NormaBNCC.objects.filter(materia=m).values('id', 'codigo', 'descricao'))
    
    context = {
        'turma': turma,
        'dia': dia,
        'materias': materias,
        'normas_por_materia_json': json.dumps(normas_por_materia)
    }
    return render(request, 'escola/plano_diario_generico.html', context)

@require_POST
@login_required
def plano_diario_generico_salvar(request):
    turma_id = request.POST.get('turma_id')
    dia_id = request.POST.get('dia_id')
    
    turma = get_object_or_404(Turma, id=turma_id)
    dia = get_object_or_404(DiaLetivo, id=dia_id)
    
    trimestre = Trimestre.objects.filter(data_inicial__lte=dia.data, data_final__gte=dia.data).first()
    if not trimestre:
        trimestre = Trimestre.objects.first()
        
    materias_selecionadas = request.POST.getlist('materias')
    
    for mat_id in materias_selecionadas:
        materia = get_object_or_404(Materia, id=mat_id)
        
        normas_ids = request.POST.getlist(f'normas_{mat_id}')
        obs = request.POST.get(f'obs_{mat_id}', '')
        
        # Cria ou atualiza o planejamento geral para esta matéria
        aula_geral, created = AulaPlanejamentoGeral.objects.get_or_create(
            turma=turma,
            materia=materia,
            dia_letivo=dia,
            defaults={
                'trimestre': trimestre,
                'tema_aula': 'Plano Genérico',
                'sugestoes_atividades': obs
            }
        )
        
        if created:
            if normas_ids:
                normas = NormaBNCC.objects.filter(id__in=normas_ids)
                aula_geral.normas.set(normas)
    
    messages.success(request, "Planejamento base criado! Agora preencha os detalhes e envie os anexos.")
    return redirect('plano_diario_abrir', turma_id=turma.id, dia_id=dia.id)

import os
from django.conf import settings
from django.template.loader import get_template
from xhtml2pdf import pisa
from .models import DocumentoPlanoAula
from .google_drive import upload_pdf_em_memoria

@login_required
def gerar_plano_pdf(request, plano_id):
    plano = get_object_or_404(PlanoDia, id=plano_id)
    
    # 1. Renderiza HTML com contexto
    template = get_template('escola/documentos/plano_aula_pdf.html')
    
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')
    # xhtml2pdf requires forward slashes on Windows for local paths to images
    logo_path = logo_path.replace('\\', '/')
    
    context = {
        'turma': plano.turma.nome,
        'data': plano.dia_letivo.data.strftime('%d/%m/%Y'),
        'componente': plano.componentes_curriculares,
        'objeto': plano.objeto_conhecimento,
        'habilidades': plano.habilidades_bncc,
        'objetivos': plano.objetivos_especificos,
        'recursos': plano.recursos,
        'avaliacao': plano.avaliacao,
        'logo_url': logo_path
    }
    
    html = template.render(context)
    
    import io
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), result)
    
    if not pdf.err:
        pdf_bytes = result.getvalue()
        
        nome_arquivo = f"Plano_de_Aula_Turma_{plano.turma.nome.replace(' ', '')}_{plano.dia_letivo.data.strftime('%d-%m-%Y')}.pdf"
        
        try:
            file_id, link = upload_pdf_em_memoria(pdf_bytes, nome_arquivo, folder_name="plano_aula_diario")
            
            # Salva no banco de dados
            DocumentoPlanoAula.objects.update_or_create(
                plano_dia=plano,
                defaults={
                    'drive_id': file_id,
                    'link_pdf': link,
                    'nome_arquivo': nome_arquivo
                }
            )
            
            messages.success(request, f"Documento gerado e salvo no Google Drive com sucesso!")
            return redirect('plano_diario_visualizar', plano_id=plano.id)
            
        except Exception as e:
            messages.error(request, f"Erro ao salvar no Drive: {str(e)}")
            return redirect('plano_diario_visualizar', plano_id=plano.id)
    else:
        messages.error(request, "Erro ao gerar PDF.")
        return redirect('plano_diario_visualizar', plano_id=plano.id)

# --- Controle de Alunos ---
from .models import RegistroAulaTurma, FrequenciaAluno, Aluno

@login_required
def controle_alunos_index(request):
    turmas = Turma.objects.all()
    # Pega os dias letivos recentes (últimos 30 dias até hoje + próximos 7 dias)
    hoje = timezone.now().date()
    data_inicio = hoje - timedelta(days=30)
    data_fim = hoje + timedelta(days=7)
    
    dias = DiaLetivo.objects.filter(eh_dia_letivo=True, data__gte=data_inicio, data__lte=data_fim).order_by('-data')
    
    return render(request, 'escola/controle_alunos_index.html', {
        'turmas': turmas,
        'dias': dias,
        'hoje': hoje
    })

@login_required
def controle_alunos_chamada(request, turma_id, dia_letivo_id):
    turma = get_object_or_404(Turma, id=turma_id)
    dia = get_object_or_404(DiaLetivo, id=dia_letivo_id)
    
    alunos = turma.alunos.all().order_by('nome')
    registro, created = RegistroAulaTurma.objects.get_or_create(turma=turma, dia_letivo=dia)
    
    # Buscar disciplinas previstas para o dia
    aulas_gerais = AulaPlanejamentoGeral.objects.filter(turma=turma, dia_letivo=dia)
    materias_previstas = [aula.materia.nome for aula in aulas_gerais]
    
    # Se for POST, salva os dados
    if request.method == 'POST':
        status_aula = request.POST.get('status_aula', 'M')
        motivo_cancelamento = request.POST.get('motivo_cancelamento', '')
        observacoes_gerais = request.POST.get('observacoes_gerais', '')
        
        # Validação extra do backend
        if status_aula == 'C' and not motivo_cancelamento.strip():
            messages.error(request, "Motivo do cancelamento é obrigatório quando a aula é cancelada.")
            return redirect('controle_alunos_chamada', turma_id=turma.id, dia_letivo_id=dia.id)
            
        registro.status = status_aula
        registro.motivo_cancelamento = motivo_cancelamento
        registro.observacoes_gerais = observacoes_gerais
        
        # Só lança presenças se a aula for ministrada
        if status_aula == 'M':
            presencas_marcadas = request.POST.getlist('presente')
            
            for aluno in alunos:
                aluno_id_str = str(aluno.id)
                presente = aluno_id_str in presencas_marcadas
                justificativa = request.POST.get(f'justificativa_{aluno.id}', '')
                observacao = request.POST.get(f'observacao_{aluno.id}', '')
                
                FrequenciaAluno.objects.update_or_create(
                    registro_aula=registro,
                    aluno=aluno,
                    defaults={
                        'presente': presente,
                        'justificativa': justificativa if not presente else '',
                        'observacao': observacao
                    }
                )
            registro.presenca_lancada = True
        else:
            registro.presenca_lancada = False
            # Se for cancelada, pode opcionalmente limpar as frequências ou ignorar.
            
        registro.save()
        messages.success(request, "Dados da aula salvos com sucesso!")
        return redirect('controle_alunos_chamada', turma_id=turma.id, dia_letivo_id=dia.id)
    
    # Montar a lista para o front-end
    lista_alunos = []
    
    # Calcular o total de aulas do trimestre/ano até agora
    ano_corrente = AnoLetivo.objects.filter(corrente=True).first()
    total_aulas_realizadas = RegistroAulaTurma.objects.filter(turma=turma, status='M').count()
    
    for aluno in alunos:
        frequencia = FrequenciaAluno.objects.filter(registro_aula=registro, aluno=aluno).first()
        
        total_faltas = FrequenciaAluno.objects.filter(aluno=aluno, presente=False).count()
        
        lista_alunos.append({
            'aluno': aluno,
            'frequencia': frequencia,
            'total_faltas': total_faltas,
            'total_aulas': total_aulas_realizadas if registro.status == 'M' else total_aulas_realizadas + 1
        })
        
    return render(request, 'escola/controle_alunos_chamada.html', {
        'turma': turma,
        'dia': dia,
        'registro': registro,
        'lista_alunos': lista_alunos,
        'materias_previstas': materias_previstas
    })

# --- Relatórios Trimestrais ---
from .models import RelatorioTrimestralAluno
from .services import gerar_relatorio_trimestral_ia

@login_required
def relatorio_index(request):
    turmas = Turma.objects.all()
    trimestres = Trimestre.objects.all()
    
    if request.method == 'POST':
        turma_id = request.POST.get('turma_id')
        trimestre_id = request.POST.get('trimestre_id')
        return redirect('relatorio_turma', turma_id=turma_id, trimestre_id=trimestre_id)
        
    return render(request, 'escola/relatorios_index.html', {'turmas': turmas, 'trimestres': trimestres})

@login_required
def relatorio_turma(request, turma_id, trimestre_id):
    turma = get_object_or_404(Turma, id=turma_id)
    trimestre = get_object_or_404(Trimestre, id=trimestre_id)
    
    alunos = turma.alunos.all().order_by('nome')
    lista_alunos = []
    
    for aluno in alunos:
        # Pega o último relatório gerado para este aluno neste trimestre
        relatorio = RelatorioTrimestralAluno.objects.filter(aluno=aluno, trimestre=trimestre).order_by('-versao').first()
        lista_alunos.append({
            'aluno': aluno,
            'relatorio': relatorio
        })
        
    return render(request, 'escola/relatorio_turma.html', {
        'turma': turma, 
        'trimestre': trimestre,
        'lista_alunos': lista_alunos
    })

@login_required
def relatorio_gerar_ia(request, aluno_id, trimestre_id):
    aluno = get_object_or_404(Aluno, id=aluno_id)
    trimestre = get_object_or_404(Trimestre, id=trimestre_id)
    turma = aluno.turma
    
    if not turma:
        messages.error(request, "Aluno não vinculado a nenhuma turma.")
        return redirect('relatorio_index')
    
    # 1. Compilar dossiê
    frequencias = FrequenciaAluno.objects.filter(
        aluno=aluno,
        registro_aula__dia_letivo__data__gte=trimestre.data_inicial,
        registro_aula__dia_letivo__data__lte=trimestre.data_final,
        registro_aula__status='M'
    )
    
    total_aulas = frequencias.count()
    total_faltas = frequencias.filter(presente=False).count()
    presencas = total_aulas - total_faltas
    
    observacoes_list = []
    for freq in frequencias:
        if freq.observacao.strip():
            observacoes_list.append(f"- {freq.registro_aula.dia_letivo.data.strftime('%d/%m')}: {freq.observacao}")
            
    # Planos de aula da turma
    planos = PlanoDia.objects.filter(
        turma=turma,
        dia_letivo__data__gte=trimestre.data_inicial,
        dia_letivo__data__lte=trimestre.data_final,
        finalizado=True
    )
    
    conteudos_list = []
    for plano in planos:
        if plano.conteudo_ministrado.strip():
            conteudos_list.append(f"- {plano.dia_letivo.data.strftime('%d/%m')} ({plano.componentes_curriculares}): {plano.conteudo_ministrado}")
            
    dossie = f"""
    ALUNO: {aluno.nome}
    TURMA: {turma.nome}
    TRIMESTRE: {trimestre.nome}
    
    -- FREQUÊNCIA --
    Aulas Ministradas: {total_aulas}
    Presenças: {presencas}
    Faltas: {total_faltas}
    
    -- OBSERVAÇÕES DIÁRIAS DO PROFESSOR --
    {chr(10).join(observacoes_list) if observacoes_list else "Nenhuma observação registrada."}
    
    -- CONTEÚDOS MINISTRADOS NO TRIMESTRE (TURMA) --
    {chr(10).join(conteudos_list) if conteudos_list else "Nenhum plano de aula finalizado."}
    """
    
    try:
        resultado_json = gerar_relatorio_trimestral_ia(dossie)
        
        ultima_versao = RelatorioTrimestralAluno.objects.filter(aluno=aluno, trimestre=trimestre).order_by('-versao').first()
        nova_versao = (ultima_versao.versao + 1) if ultima_versao else 1
        
        relatorio = RelatorioTrimestralAluno.objects.create(
            aluno=aluno,
            trimestre=trimestre,
            versao=nova_versao,
            visao_geral=resultado_json.get('visao_geral', ''),
            linguagem=resultado_json.get('linguagem', ''),
            matematica=resultado_json.get('matematica', ''),
            ciencias=resultado_json.get('ciencias', ''),
            conclusao=resultado_json.get('conclusao', '')
        )
        
        messages.success(request, f"Relatório gerado pela IA (Versão {nova_versao})! Revise os textos abaixo.")
        return redirect('relatorio_revisar', relatorio_id=relatorio.id)
        
    except Exception as e:
        messages.error(request, str(e))
        return redirect('relatorio_turma', turma_id=turma.id, trimestre_id=trimestre.id)

@login_required
def relatorio_revisar(request, relatorio_id):
    relatorio = get_object_or_404(RelatorioTrimestralAluno, id=relatorio_id)
    turma = relatorio.aluno.turma
    
    if request.method == 'POST':
        visao_geral = request.POST.get('visao_geral', '')
        linguagem = request.POST.get('linguagem', '')
        matematica = request.POST.get('matematica', '')
        ciencias = request.POST.get('ciencias', '')
        conclusao = request.POST.get('conclusao', '')
        
        novo_relatorio = RelatorioTrimestralAluno.objects.create(
            aluno=relatorio.aluno,
            trimestre=relatorio.trimestre,
            versao=relatorio.versao + 1,
            visao_geral=visao_geral,
            linguagem=linguagem,
            matematica=matematica,
            ciencias=ciencias,
            conclusao=conclusao
        )
        messages.success(request, "Alterações salvas em uma nova versão.")
        return redirect('relatorio_revisar', relatorio_id=novo_relatorio.id)
        
    # Busca histórico de versões
    versoes = RelatorioTrimestralAluno.objects.filter(aluno=relatorio.aluno, trimestre=relatorio.trimestre).exclude(id=relatorio.id).order_by('-versao')
        
    return render(request, 'escola/relatorio_revisao.html', {'relatorio': relatorio, 'turma': turma, 'versoes': versoes})

@login_required
def relatorio_gerar_pdf(request, relatorio_id):
    relatorio = get_object_or_404(RelatorioTrimestralAluno, id=relatorio_id)
    turma = relatorio.aluno.turma
    
    template = get_template('escola/documentos/relatorio_pdf.html')
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png').replace('\\', '/')
    
    # Calcular faltas e dias letivos
    frequencias = FrequenciaAluno.objects.filter(
        aluno=relatorio.aluno,
        registro_aula__dia_letivo__data__gte=relatorio.trimestre.data_inicial,
        registro_aula__dia_letivo__data__lte=relatorio.trimestre.data_final,
        registro_aula__status='M'
    )
    dias_letivos = frequencias.count()
    faltas = frequencias.filter(presente=False).count()
    
    meses = {
        1: 'janeiro', 2: 'fevereiro', 3: 'março', 4: 'abril', 5: 'maio', 6: 'junho',
        7: 'julho', 8: 'agosto', 9: 'setembro', 10: 'outubro', 11: 'novembro', 12: 'dezembro'
    }
    hoje = timezone.now()
    
    context = {
        'logo_url': logo_path,
        'nome': relatorio.aluno.nome,
        'nasc': relatorio.aluno.data_nascimento.strftime('%d/%m/%Y') if relatorio.aluno.data_nascimento else '',
        'ano_escolaridade': turma.ano,
        'turma': turma.nome,
        'turno': relatorio.aluno.get_turno_display(),
        'professor': request.user.get_full_name() or request.user.username,
        'dias_letivos': dias_letivos,
        'faltas': faltas,
        'trimestre': relatorio.trimestre.nome,
        'ano': relatorio.trimestre.data_inicial.year,
        'visao_geral': relatorio.visao_geral,
        'linguagem': relatorio.linguagem,
        'matematica': relatorio.matematica,
        'ciencias': relatorio.ciencias,
        'conclusao': relatorio.conclusao,
        'data_relatorio': f"Teresópolis, {hoje.day} de {meses[hoje.month]} de {hoje.year}."
    }
    html = template.render(context)
    
    import io
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), result)
    
    if not pdf.err:
        pdf_bytes = result.getvalue()
        nome_arquivo = f"Relatorio_{relatorio.aluno.nome.replace(' ', '')}_{relatorio.trimestre.nome}_v{relatorio.versao}.pdf"
        
        try:
            file_id, link = upload_pdf_em_memoria(pdf_bytes, nome_arquivo, folder_name="relatorios_trimestrais")
            relatorio.drive_id = file_id
            relatorio.link_pdf = link
            relatorio.save()
            
            messages.success(request, "Relatório em PDF gerado e salvo no Google Drive!")
            return redirect('relatorio_revisar', relatorio_id=relatorio.id)
        except Exception as e:
            messages.error(request, f"Erro no upload para o Drive: {e}")
            return redirect('relatorio_revisar', relatorio_id=relatorio.id)
    else:
        messages.error(request, "Erro ao gerar PDF.")
        return redirect('relatorio_revisar', relatorio_id=relatorio.id)
