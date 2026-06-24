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
        model_name="google/gemini-flash-1.5",
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
        return []
