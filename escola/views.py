from django.shortcuts import render, redirect
from django.views.generic import ListView
from django.utils import timezone
from .models import DiaLetivo
import calendar
from datetime import date

def dashboard(request):
    return render(request, 'escola/dashboard.html')

class CalendarioView(ListView):
    model = DiaLetivo
    template_name = 'escola/calendario.html'
    context_object_name = 'dias'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoje = timezone.now().date()
        mes_atual = hoje.month
        ano_atual = hoje.year
        
        # Pega todos os dias do banco
        dias_bd = {dia.data: dia for dia in DiaLetivo.objects.filter(data__year=ano_atual)}
        
        # Gera o calendário do mês atual para exibição
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
                        'eh_letivo': dia_bd.eh_dia_letivo if dia_bd else (dia.weekday() < 5), # Por padrão sab/dom não letivo
                        'observacao': dia_bd.observacao if dia_bd else '',
                        'no_banco': bool(dia_bd)
                    })
                else:
                    semana_estruturada.append(None) # Dias de outros meses
            calendario_estruturado.append(semana_estruturada)
            
        context['calendario'] = calendario_estruturado
        context['mes_atual'] = mes_atual
        context['ano_atual'] = ano_atual
        return context

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
        total_salvas = 0
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
                        NormaBNCC.objects.get_or_create(
                            codigo=codigo,
                            materia=materia_obj,
                            trimestre=trimestre,
                            defaults={'descricao': descricao}
                        )
                        total_salvas += 1
            except Exception as e:
                erros.append(f"Erro no arquivo {pdf_file.name}: {str(e)}")
            finally:
                # Apaga o arquivo temporário
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
        if total_salvas > 0:
            messages.success(request, f'Processamento concluído. {total_salvas} normas foram extraídas e salvas no banco.')
        if erros:
            for err in erros:
                messages.error(request, err)
                
        return redirect('upload_bncc')
        
    return render(request, 'escola/upload_bncc.html', {'trimestres': trimestres})

