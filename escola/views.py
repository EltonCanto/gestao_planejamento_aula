from django.shortcuts import render, redirect
from django.views.generic import ListView
from django.utils import timezone
from .models import DiaLetivo, AnoLetivo, PlanoAula, AulaPlanejamentoGeral
import calendar
from datetime import date
from collections import defaultdict

def dashboard(request):
    return render(request, 'escola/dashboard.html')

class CalendarioView(ListView):
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
            
        context['calendario'] = calendario_estruturado
        context['mes_atual'] = mes_atual
        context['ano_atual'] = ano_atual
        context['prox_mes'] = prox_mes
        context['prox_ano'] = prox_ano
        context['ant_mes'] = ant_mes
        context['ant_ano'] = ant_ano
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

def planejamento_geral_config(request):
    turmas = Turma.objects.all()
    materias = Materia.objects.all()
    trimestres = Trimestre.objects.all()
    return render(request, 'escola/planejamento_geral_config.html', {
        'turmas': turmas,
        'materias': materias,
        'trimestres': trimestres
    })

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
