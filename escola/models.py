from django.db import models

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
