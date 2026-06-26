import os
from pypdf import PdfReader
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from django.conf import settings
import json
import re

# Ideal é que o usuário defina a variável OPENROUTER_API_KEY no .env
# e a carreguemos com python-dotenv, ou a gente passe na inicialização
from dotenv import load_dotenv
load_dotenv()

def processar_pdf_bncc(pdf_path, is_geral=True):
    """
    Lê o PDF da BNCC e usa um LLM via OpenRouter para extrair as normas.
    Retorna uma lista de dicionários: [{'codigo': 'EF...', 'descricao': '...', 'materia': 'História'}]
    """
    try:
        reader = PdfReader(pdf_path)
        texto = ""
        # Limita as páginas lidas para não estourar o contexto (ou processa em batch, mas vamos ler as primeiras/principais para teste)
        for i, page in enumerate(reader.pages):
            texto += page.extract_text() + "\n"
            if i > 20: # Limite seguro para não estourar limites gratuitos inicialmente
                break
    except Exception as e:
        print(f"Erro ao ler PDF: {e}")
        return []

    # Configuração do LangChain com OpenRouter
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("API Key do OpenRouter não encontrada.")
        return []

    # O usuário pediu modelos de custo-benefício. Usando o gemini flash ou gpt-4o-mini via OpenRouter
    # Vamos usar o meta-llama/llama-3.1-8b-instruct ou google/gemini-flash-1.5 como fallback
    llm = ChatOpenAI(
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        model_name="google/gemini-2.5-flash",
        temperature=0.1
    )

    # Prompt para extrair os códigos BNCC e as descrições
    template = """
Você é um assistente especializado em pedagogia e na Base Nacional Comum Curricular (BNCC) do Brasil.
Abaixo está um trecho de um documento em PDF da BNCC ou currículo escolar.

Sua tarefa é extrair as normas (habilidades) mencionadas no texto.
Você deve retornar estritamente um array JSON válido contendo objetos com as seguintes chaves:
- "codigo": O código alfanumérico da norma (ex: EF15AR01)
- "descricao": O texto da habilidade
- "materia": O nome da matéria escolar correspondente (ex: Artes, História, Matemática, Língua Portuguesa)

Se não encontrar nenhuma norma, retorne um array vazio [].
Não inclua nenhum texto adicional, apenas o JSON puro.

TEXTO DO DOCUMENTO:
{texto}
    """

    prompt = PromptTemplate(
        input_variables=["texto"],
        template=template
    )

    try:
        chain = prompt | llm
        resposta = chain.invoke({"texto": texto[0:40000]}) # Enviando um chunk (ajustável)
        
        content = resposta.content
        
        # Limpar crases de markdown do JSON, se houver
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        
        dados = json.loads(content)
        return dados
    except Exception as e:
        print(f"Erro na IA/JSON: {e}")
        raise Exception(f"Falha na comunicação com a IA ou processamento: {str(e)}")

def gerar_plano_com_ia(turma_nome, materia_nome, normas_texto):
    """
    Usa a IA para gerar os campos do plano de aula com base na turma, matéria e normas selecionadas.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise Exception("API Key do OpenRouter não encontrada.")

    llm = ChatOpenAI(
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        model_name="google/gemini-2.5-flash",
        temperature=0.7
    )

    template = """
Você é um professor experiente elaborando um plano de aula.
Com base nas informações abaixo, crie um plano de aula preenchendo os seguintes blocos obrigatórios de um documento padrão.
O retorno deve ser estritamente um JSON válido, sem markdown envolta (sem ```json), com as seguintes chaves:
- "objeto_conhecimento": Texto sobre qual é o tema ou objeto do conhecimento da aula.
- "habilidades_bncc": As próprias normas e como elas se aplicam resumidamente na aula.
- "objetivos_especificos": O que os alunos devem aprender ou ser capazes de fazer.
- "recursos": Materiais e recursos necessários.
- "avaliacao": Como será a avaliação do aprendizado.

Turma: {turma}
Componente Curricular: {materia}
Normas BNCC a serem trabalhadas:
{normas}

Retorne apenas o JSON. Use quebras de linha (\\n) dentro das strings se quiser formatar os textos em tópicos.
"""

    prompt = PromptTemplate(
        input_variables=["turma", "materia", "normas"],
        template=template
    )

    chain = prompt | llm
    
    try:
        resposta = chain.invoke({"turma": turma_nome, "materia": materia_nome, "normas": normas_texto})
        content = resposta.content
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        dados = json.loads(content)
        return dados
    except Exception as e:
        print(f"Erro na geração do plano via IA: {e}")
        raise Exception(f"Falha na IA ao gerar plano: {str(e)}")

def distribuir_normas_homogeneamente(dias_lista, normas_lista):
    """
    Distribui as normas homogeneamente (round-robin) nos dias e usa IA
    apenas para criar os temas e sugestões baseados na norma alocada para cada dia.
    dias_lista: lista de dicionários ou objetos com 'id' e 'data' (string)
    normas_lista: lista de objetos com 'codigo' e 'descricao'
    """
    if not normas_lista or not dias_lista:
        return []

    # 1. Distribuição programática (Round-Robin)
    alocacao = []
    total_normas = len(normas_lista)
    
    for i, dia in enumerate(dias_lista):
        norma_idx = i % total_normas
        norma_alocada = normas_lista[norma_idx]
        
        # O dicionário de alocação que vamos mandar pra IA
        alocacao.append({
            "dia_data": str(dia.data),
            "norma_codigo": norma_alocada.codigo,
            "norma_descricao": norma_alocada.descricao
        })

    # 2. Chama a IA para gerar os Temas e as Sugestões
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise Exception("API Key do OpenRouter não encontrada.")

    llm = ChatOpenAI(
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        model_name="google/gemini-2.5-flash",
        temperature=0.7
    )

    alocacao_texto = json.dumps(alocacao, indent=2, ensure_ascii=False)

    template = """
Você é um especialista em pedagogia. 
Abaixo está um JSON contendo uma lista de dias letivos e a habilidade da BNCC (código e descrição) que já foi alocada para aquele dia.
Para cada dia, crie:
1. Um "tema" curto e coerente para a aula, derivado diretamente da habilidade BNCC selecionada.
2. Uma "sugestao" prática de atividade para a aula, baseada nesse tema e nessa habilidade.

Retorne ESTRITAMENTE um array JSON com objetos. Não escreva mais nada além do JSON.
Formato de saída esperado:
[
  {{
    "data": "A mesma data fornecida",
    "tema": "Título curto do tema da aula",
    "sugestao": "Sugestão de atividade prática",
    "normas_codigos": ["O código da norma fornecido"]
  }}
]

DADOS DE ENTRADA:
{alocacao}
"""

    prompt = PromptTemplate(
        input_variables=["alocacao"],
        template=template
    )

    chain = prompt | llm
    
    try:
        resposta = chain.invoke({"alocacao": alocacao_texto})
        content = resposta.content
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        dados = json.loads(content)
        return dados
    except Exception as e:
        print(f"Erro na IA ao gerar temas e sugestões: {e}")
        raise Exception(f"Falha na IA ao gerar planejamento: {str(e)}")

def sugerir_atividades_ia(turma_nome, tema, normas_texto):
    """
    Usa a IA para sugerir 3 atividades para uma aula específica.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise Exception("API Key do OpenRouter não encontrada.")

    llm = ChatOpenAI(
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        model_name="google/gemini-2.5-flash",
        temperature=0.7
    )

    template = """
Você é um especialista em pedagogia.
O professor precisa de 3 sugestões de atividades curtas e práticas para uma aula.

Turma: {turma}
Tema da Aula: {tema}
Normas BNCC (Habilidades) Selecionadas:
{normas}

Por favor, forneça exatamente 3 sugestões de atividades. Numeradas de 1 a 3. Cada sugestão deve ser um parágrafo curto. Retorne APENAS o texto das sugestões.
"""

    prompt = PromptTemplate(
        input_variables=["turma", "tema", "normas"],
        template=template
    )

    chain = prompt | llm
    
    try:
        resposta = chain.invoke({"turma": turma_nome, "tema": tema, "normas": normas_texto})
        return resposta.content.strip()
    except Exception as e:
        print(f"Erro na geração de sugestões via IA: {e}")
        raise Exception(f"Falha na IA ao sugerir atividades: {str(e)}")
