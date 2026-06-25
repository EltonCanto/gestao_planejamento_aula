from django.shortcuts import render, redirect
from django.views.generic import ListView
from django.utils import timezone
from .models import DiaLetivo
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
                        'eh_letivo': dia_bd.eh_dia_letivo if dia_bd else (dia.weekday() < 5),
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
            
        delta = data_final - data_inicial
        dias_criados = 0
        feriados_marcados = 0
        
        # Gera o cache de feriados para os anos envolvidos
        anos = set([data_inicial.year, data_final.year])
        feriados = {}
        for ano in anos:
            feriados.update(get_feriados(ano))
        
        for i in range(delta.days + 1):
            dia = data_inicial + timedelta(days=i)
            # Segunda=0, Domingo=6.
            if dia.weekday() < 5:
                is_feriado = dia in feriados
                nome_feriado = feriados.get(dia, '')
                
                eh_letivo = not is_feriado
                
                obj, created = DiaLetivo.objects.get_or_create(
                    data=dia,
                    defaults={
                        'eh_dia_letivo': eh_letivo,
                        'observacao': nome_feriado
                    }
                )
                
                # Se ja existia, a gente atualiza caso seja feriado e estava marcado como aula
                if not created and is_feriado and obj.eh_dia_letivo:
                    obj.eh_dia_letivo = False
                    obj.observacao = nome_feriado
                    obj.save()
                    feriados_marcados += 1
                elif created:
                    if is_feriado:
                        feriados_marcados += 1
                    else:
                        dias_criados += 1
                    
        messages.success(request, f"Calendário gerado! {dias_criados} dias úteis letivos criados e {feriados_marcados} feriados municipais/nacionais adicionados como 'Sem Aula'.")
        return redirect(f"/escola/?ano={data_inicial.year}&mes={data_inicial.month}")
        
    return redirect('calendario')

def toggle_dia_letivo(request, data_str):
    if request.method == 'POST':
        # data_str formato: YYYY-MM-DD
        partes = data_str.split('-')
        if len(partes) == 3:
            data_obj = date(int(partes[0]), int(partes[1]), int(partes[2]))
            dia, created = DiaLetivo.objects.get_or_create(data=data_obj)
            if not created:
                dia.eh_dia_letivo = not dia.eh_dia_letivo
                dia.save()
            else:
                # Se acabou de criar, e final de semana for padrão falso, vamos inverter
                dia.eh_dia_letivo = False if data_obj.weekday() >= 5 else False
                dia.save()
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

from .models import AulaPlanejamentoGeral
from .services import distribuir_normas_ia

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
        
        # Pega dias letivos no trimestre
        dias = DiaLetivo.objects.filter(
            eh_dia_letivo=True,
            data__gte=trimestre.data_inicial,
            data__lte=trimestre.data_final
        ).order_by('data')
        
        if not dias.exists():
            messages.error(request, "Não há dias letivos cadastrados para este trimestre.")
            return redirect('planejamento_geral_config')
            
        # Pega as normas da matéria para o trimestre
        normas = NormaBNCC.objects.filter(materia=materia, trimestre=trimestre)
        if not normas.exists():
            messages.error(request, "Não há normas da BNCC cadastradas para esta matéria no trimestre selecionado.")
            return redirect('planejamento_geral_config')
            
        dias_texto = "\n".join([str(d.data) for d in dias])
        normas_texto = "\n".join([f"[{n.codigo}] {n.descricao}" for n in normas])
        
        try:
            distribuicao = distribuir_normas_ia(dias_texto, normas_texto)
            # distribuicao é uma lista de dicts: [{'data': '...', 'tema': '...', 'normas_codigos': ['...']}]
            
            # Formatar para a tela de revisão
            plano_revisao = []
            for d in distribuicao:
                dia_obj = dias.filter(data=d.get('data')).first()
                if dia_obj:
                    codigos = d.get('normas_codigos', [])
                    normas_objs = normas.filter(codigo__in=codigos)
                    plano_revisao.append({
                        'dia': dia_obj,
                        'tema': d.get('tema', ''),
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
        
        # Limpa o planejamento anterior para essa mesma turma, materia e dia
        # Ou faz update. Vamos usar update_or_create
        for i, dia_id in enumerate(dias_ids):
            tema = temas[i] if i < len(temas) else ''
            
            aula, created = AulaPlanejamentoGeral.objects.update_or_create(
                turma_id=turma_id,
                materia_id=materia_id,
                dia_letivo_id=dia_id,
                defaults={
                    'trimestre_id': trimestre_id,
                    'tema_aula': tema
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
