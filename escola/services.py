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

def distribuir_normas_ia(dias_texto, normas_texto):
    """
    Usa a IA para distribuir as normas ao longo dos dias letivos disponíveis.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise Exception("API Key do OpenRouter não encontrada.")

    llm = ChatOpenAI(
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        model_name="google/gemini-2.5-flash",
        temperature=0.4
    )

    template = """
Você é um especialista em pedagogia encarregado de montar o Planejamento Geral de um trimestre.
Abaixo eu forneço uma lista de dias letivos disponíveis e uma lista de normas (habilidades) da BNCC.
Você deve alocar logicamente as habilidades ao longo desses dias letivos.
Você não precisa colocar normas em TODOS os dias (você pode reservar dias para revisão ou avaliações, se achar prudente, ou distribuir uniformemente).

Retorne ESTRITAMENTE um array JSON com objetos. Cada objeto representa um dia e deve ter o formato:
{{
  "data": "YYYY-MM-DD",  // (Usando a exata string da data fornecida)
  "tema": "Título ou tema da aula",
  "normas_codigos": ["CODIGO1", "CODIGO2"] // Apenas os códigos das normas BNCC associadas
}}

DIAS LETIVOS:
{dias}

NORMAS BNCC (Habilidades):
{normas}

Retorne apenas o JSON.
"""

    prompt = PromptTemplate(
        input_variables=["dias", "normas"],
        template=template
    )

    chain = prompt | llm
    
    try:
        resposta = chain.invoke({"dias": dias_texto, "normas": normas_texto})
        content = resposta.content
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        dados = json.loads(content)
        return dados
    except Exception as e:
        print(f"Erro na geração do planejamento geral via IA: {e}")
        raise Exception(f"Falha na IA ao distribuir normas: {str(e)}")
