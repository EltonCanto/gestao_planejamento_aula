from django.db import models

class AnoLetivo(models.Model):
    ano = models.IntegerField(unique=True)
    corrente = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.corrente:
            AnoLetivo.objects.filter(corrente=True).update(corrente=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ano} {'(Corrente)' if self.corrente else ''}"

class Escola(models.Model):
    nome = models.CharField(max_length=255)
    endereco = models.TextField()
    email = models.EmailField()

    def __str__(self):
        return self.nome

class Trimestre(models.Model):
    nome = models.CharField(max_length=50) # Ex: 1º Trimestre
    data_inicial = models.DateField()
    data_final = models.DateField()

    def __str__(self):
        return f"{self.nome} ({self.data_inicial.strftime('%d/%m/%Y')} - {self.data_final.strftime('%d/%m/%Y')})"

class Turma(models.Model):
    nome = models.CharField(max_length=50) # Ex: 2B
    ano = models.CharField(max_length=100) # Ex: Segundo Ano do Ensino Fundamental

    def __str__(self):
        return f"{self.nome} - {self.ano}"

class Professor(models.Model):
    nome = models.CharField(max_length=255)
    funcao = models.CharField(max_length=100)
    turmas = models.ManyToManyField(Turma, related_name='professores')

    def __str__(self):
        return self.nome

class Aluno(models.Model):
    TURNOS = (
        ('M', 'Matutino'),
        ('V', 'Vespertino'),
        ('N', 'Noturno'),
    )
    numero = models.IntegerField()
    nome = models.CharField(max_length=255)
    data_nascimento = models.DateField()
    turma = models.ForeignKey(Turma, on_delete=models.CASCADE, related_name='alunos')
    turno = models.CharField(max_length=1, choices=TURNOS)

    def __str__(self):
        return f"{self.numero} - {self.nome} ({self.turma})"

class TemaPeriodo(models.Model):
    tema = models.CharField(max_length=255) # Ex: Carnaval, Páscoa, Dia da Mulher
    data_inicial = models.DateField()
    data_final = models.DateField()

    def __str__(self):
        return self.tema

class DiaLetivo(models.Model):
    data = models.DateField(unique=True)
    ano_letivo = models.ForeignKey(AnoLetivo, on_delete=models.CASCADE, related_name='dias', null=True)
    eh_dia_letivo = models.BooleanField(default=True, help_text="Desmarque para feriados, férias ou dias sem aula.")
    observacao = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        status = "Aula" if self.eh_dia_letivo else "Sem aula"
        return f"{self.data.strftime('%d/%m/%Y')} - {status}"

class Materia(models.Model):
    TIPOS = (
        ('G', 'Geral'),
        ('E', 'Específica'),
    )
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=1, choices=TIPOS)

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"

class NormaBNCC(models.Model):
    codigo = models.CharField(max_length=20)
    descricao = models.TextField()
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name='normas')
    trimestre = models.ForeignKey(Trimestre, on_delete=models.SET_NULL, null=True, blank=True, related_name='normas_bncc')
    
    def __str__(self):
        return f"{self.codigo} - {self.materia.nome}"

class PlanoAula(models.Model):
    turma = models.ForeignKey(Turma, on_delete=models.CASCADE, related_name='planos')
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name='planos')
    dia_letivo = models.ForeignKey(DiaLetivo, on_delete=models.CASCADE, related_name='planos')
    
    objeto_conhecimento = models.TextField(blank=True)
    habilidades_bncc = models.TextField(blank=True)
    objetivos_especificos = models.TextField(blank=True)
    recursos = models.TextField(blank=True)
    avaliacao = models.TextField(blank=True)
    
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['turma', 'materia', 'dia_letivo']

    def __str__(self):
        return f"Plano: {self.turma.nome} - {self.materia.nome} ({self.dia_letivo.data.strftime('%d/%m/%Y')})"

class AulaPlanejamentoGeral(models.Model):
    turma = models.ForeignKey(Turma, on_delete=models.CASCADE, related_name='aulas_gerais')
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name='aulas_gerais')
    trimestre = models.ForeignKey(Trimestre, on_delete=models.CASCADE, related_name='aulas_gerais')
    dia_letivo = models.ForeignKey(DiaLetivo, on_delete=models.CASCADE, related_name='aulas_gerais')
    
    tema_aula = models.CharField(max_length=255, blank=True)
    normas = models.ManyToManyField(NormaBNCC, blank=True)
    sugestoes_atividades = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['turma', 'materia', 'dia_letivo']
        ordering = ['dia_letivo__data']

    def __str__(self):
        return f"Aula: {self.turma.nome} - {self.materia.nome} em {self.dia_letivo.data.strftime('%d/%m/%Y')}"

class DistribuicaoMateria(models.Model):
    FREQUENCIA_CHOICES = (
        ('TODOS', 'Todos os dias'),
        ('FIXO', 'Dia Fixo'),
        ('RODIZIO', 'Rodízio'),
    )
    DIA_SEMANA_CHOICES = (
        (0, 'Segunda-feira'),
        (1, 'Terça-feira'),
        (2, 'Quarta-feira'),
        (3, 'Quinta-feira'),
        (4, 'Sexta-feira'),
    )

    turma = models.ForeignKey(Turma, on_delete=models.CASCADE, related_name='distribuicoes')
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name='distribuicoes')
    frequencia = models.CharField(max_length=10, choices=FREQUENCIA_CHOICES, default='TODOS')
    dia_semana = models.IntegerField(choices=DIA_SEMANA_CHOICES, null=True, blank=True)
    ordem_rodizio = models.IntegerField(default=1, help_text="Se for rodízio, defina a ordem (1, 2, 3...) entre as matérias que dividem o mesmo dia.")

    class Meta:
        unique_together = ['turma', 'materia']
        verbose_name = 'Distribuição de Matéria'
        verbose_name_plural = 'Distribuições de Matérias'

    def __str__(self):
        return f"{self.turma.nome} - {self.materia.nome} ({self.get_frequencia_display()})"

class PlanoDia(models.Model):
    turma = models.ForeignKey(Turma, on_delete=models.CASCADE, related_name='planos_dia')
    dia_letivo = models.ForeignKey(DiaLetivo, on_delete=models.CASCADE, related_name='planos_dia')
    trimestre = models.ForeignKey(Trimestre, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Textos pedagógicos consolidados gerados pela IA (ou editados manualmente)
    objeto_conhecimento = models.TextField(blank=True)
    habilidades_bncc = models.TextField(blank=True)
    objetivos_especificos = models.TextField(blank=True)
    recursos = models.TextField(blank=True)
    avaliacao = models.TextField(blank=True)
    componentes_curriculares = models.TextField(blank=True)
    conteudo_ministrado = models.TextField(blank=True)
    
    finalizado = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['turma', 'dia_letivo']
        ordering = ['dia_letivo__data']

    def __str__(self):
        return f"Plano Dia: {self.turma.nome} em {self.dia_letivo.data.strftime('%d/%m/%Y')}"

class AtividadeDisciplina(models.Model):
    plano_dia = models.ForeignKey(PlanoDia, on_delete=models.CASCADE, related_name='atividades')
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    dinamica = models.TextField(blank=True)
    
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Atividade {self.materia.nome} - {self.plano_dia}"

class ArquivoAtividade(models.Model):
    atividade = models.ForeignKey(AtividadeDisciplina, on_delete=models.CASCADE, related_name='arquivos')
    drive_id = models.CharField(max_length=255, blank=True, null=True)
    link = models.URLField(blank=True, null=True)
    nome_arquivo = models.CharField(max_length=255)
    
    texto_extraido = models.TextField(blank=True)
    resumo_ia = models.TextField(blank=True)
    
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome_arquivo

class RegistroAulaTurma(models.Model):
    """Controla o status geral da aula para uma turma em um dia letivo"""
    STATUS_AULA = (
        ('P', 'Pendente'),
        ('M', 'Ministrada'),
        ('C', 'Cancelada'),
    )
    
    turma = models.ForeignKey(Turma, on_delete=models.CASCADE, related_name='registros_aula')
    dia_letivo = models.ForeignKey(DiaLetivo, on_delete=models.CASCADE, related_name='registros_aula')
    
    status = models.CharField(max_length=1, choices=STATUS_AULA, default='P')
    motivo_cancelamento = models.TextField(blank=True)
    observacoes_gerais = models.TextField(blank=True)
    
    presenca_lancada = models.BooleanField(default=False) # Mantido por compatibilidade temporária
    
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['turma', 'dia_letivo']
        verbose_name = 'Registro de Aula da Turma'
        verbose_name_plural = 'Registros de Aulas das Turmas'

    def __str__(self):
        return f"Registro: {self.turma.nome} - {self.dia_letivo.data.strftime('%d/%m/%Y')} (Status: {self.get_status_display()})"

class FrequenciaAluno(models.Model):
    """Registro individual de frequência e observação pedagógica"""
    registro_aula = models.ForeignKey(RegistroAulaTurma, on_delete=models.CASCADE, related_name='frequencias')
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name='frequencias')
    
    presente = models.BooleanField(default=True)
    justificativa = models.TextField(blank=True, help_text="Obrigatório se presente=False")
    observacao = models.TextField(blank=True)
    
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['registro_aula', 'aluno']
        verbose_name = 'Frequência do Aluno'
        verbose_name_plural = 'Frequências dos Alunos'

    def __str__(self):
        status = "Presente" if self.presente else "Ausente"
        return f"{self.aluno.nome} - {self.registro_aula.dia_letivo.data.strftime('%d/%m/%Y')} ({status})"

class DocumentoPlanoAula(models.Model):
    plano_dia = models.OneToOneField(PlanoDia, on_delete=models.CASCADE, related_name='documento_pdf')
    drive_id = models.CharField(max_length=255)
    link_pdf = models.URLField()
    nome_arquivo = models.CharField(max_length=255)
    gerado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome_arquivo

class RelatorioTrimestralAluno(models.Model):
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name='relatorios')
    trimestre = models.ForeignKey(Trimestre, on_delete=models.CASCADE)
    versao = models.IntegerField(default=1)
    
    visao_geral = models.TextField()
    linguagem = models.TextField()
    matematica = models.TextField()
    ciencias = models.TextField()
    conclusao = models.TextField()
    
    drive_id = models.CharField(max_length=255, null=True, blank=True)
    link_pdf = models.URLField(null=True, blank=True)
    
    gerado_em = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['aluno', 'trimestre', 'versao']
        ordering = ['-versao']

    def __str__(self):
        return f"Relatório: {self.aluno.nome} - {self.trimestre.nome} (v{self.versao})"
