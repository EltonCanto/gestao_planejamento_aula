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

# --- Novas Funcionalidades para Planejamento Diário ---

import docx
from PIL import Image
import pytesseract

def extrair_texto_arquivo(caminho_arquivo, extensao):
    """
    Lê o arquivo local (após o upload) e extrai o texto baseando-se na extensão.
    Retorna o texto extraído.
    """
    extensao = extensao.lower()
    texto = ""
    try:
        if extensao == 'pdf':
            reader = PdfReader(caminho_arquivo)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    texto += t + "\n"
        elif extensao in ['doc', 'docx']:
            doc = docx.Document(caminho_arquivo)
            for para in doc.paragraphs:
                texto += para.text + "\n"
        elif extensao in ['jpg', 'jpeg', 'png']:
            img = Image.open(caminho_arquivo)
            texto = pytesseract.image_to_string(img, lang='por') # 'por' requer tesseract-ocr-por instalado
    except Exception as e:
        print(f"Erro ao extrair texto do arquivo {caminho_arquivo}: {e}")
    
    return texto.strip()

def resumir_arquivo_ia(texto_extraido):
    """
    Usa a IA para ler o texto bruto do documento e criar um resumo curto e um título em poucas palavras.
    Retorna uma tupla: (resumo, titulo_curto)
    """
    if not texto_extraido:
        return "Nenhum texto extraído do documento.", "Sem_Titulo"
        
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return "Resumo indisponível (Sem API Key)", "Sem_API_Key"

    llm = ChatOpenAI(
        openai_api_key=api_key,
        openai_api_base="https://openrouter.ai/api/v1",
        model_name="google/gemini-2.5-flash",
        temperature=0.3
    )
    
    template = """
    Analise o texto abaixo, extraído de um material didático.
    Retorne APENAS um JSON válido contendo:
    {{
       "titulo_curto": "Um título em poucas palavras, sem acentos ou caracteres especiais, ideal para nome de arquivo (ex: FracoesMatematica)",
       "resumo": "Um resumo bem simples e direto em no máximo 2 linhas sobre o material didático."
    }}
    
    CONTEÚDO:
    {texto}
    """
    
    prompt = PromptTemplate(input_variables=["texto"], template=template)
    chain = prompt | llm
    
    try:
        resposta = chain.invoke({"texto": texto_extraido[:15000]}) # Limite de segurança
        content = resposta.content.strip()
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        dados = json.loads(content)
        return dados.get('resumo', 'Resumo indisponível'), dados.get('titulo_curto', 'Atividade')
    except Exception as e:
        print(f"Erro ao resumir arquivo: {e}")
        return "Erro ao gerar resumo pela IA.", "ErroIA"

def gerar_plano_diario_completo_ia(contexto_str):
    """
    Envia todo o contexto do dia para a IA e pede a geração estruturada do plano em JSON.
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
Você é um professor coordenador experiente. Sua tarefa é consolidar o plano de aula DIÁRIO de uma turma, unificando as diversas disciplinas que ocorrerão no mesmo dia.

Você receberá abaixo o "Contexto do Dia", contendo:
- Informações da Turma e Trimestre.
- As disciplinas que serão lecionadas no dia.
- O tema central de cada disciplina (Planejamento Geral).
- Os códigos da BNCC que foram vinculados.
- As dinâmicas cadastradas pelo professor.
- O resumo dos arquivos/materiais anexados.

Com base NISSO e PRIORIZANDO as informações fornecidas, preencha os 7 campos pedagógicos obrigatórios abaixo e retorne APENAS um JSON válido contendo:

{{
  "objeto_conhecimento": "Descreva os objetos de conhecimento coerentes com os temas, dinâmicas e arquivos. Use o padrão oficial.",
  "habilidades_bncc": "Liste AS MESMAS habilidades passadas no contexto (código e descrição). NÃO use formato de lista (array) do JSON, retorne um texto corrido quebrando linha entre uma habilidade e outra. Exemplo: 'EF02MA01.RJ: Texto...\\nEF02CI01: Texto...'",
  "objetivos_especificos": "No máximo 6 objetivos específicos. NÃO use formato de lista/array JSON. Retorne um texto corrido separando cada objetivo por quebra de linha (\\n). Comece cada objetivo com um verbo no infinitivo.",
  "recursos": "Lista de recursos (ex: Caderno, Lápis, Projetor). NÃO inclua os nomes dos arquivos anexados aqui (eles já aparecem na seção Anexos). NÃO use array JSON. Retorne em texto corrido separando cada recurso por uma quebra de linha (\\n).",
  "avaliacao": "A avaliação será realizada de forma contínua, observando a participação dos alunos, a leitura, a escrita correta das palavras e a aplicação das habilidades desenvolvidas nas atividades propostas.",
  "componentes_curriculares": "Os componentes curriculares abordados no dia. Retorne como um texto único com ' e ' ligando os itens se houver mais de um. Exemplo: 'Matemática e Ciências da Natureza'.",
  "conteudo_ministrado": "Seja direto e conciso, com um texto mais reduzido mantendo o tom profissional da área de pedagogia."
}}

ATENÇÃO: Mantenha o texto da "avaliacao" EXATAMENTE como escrito acima, a menos que haja algo muito específico no contexto que exija mudança.

CONTEXTO DO DIA:
{contexto}
"""
    prompt = PromptTemplate(input_variables=["contexto"], template=template)
    chain = prompt | llm
    
    try:
        resposta = chain.invoke({"contexto": contexto_str})
        content = resposta.content
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        return json.loads(content)
    except Exception as e:
        print(f"Erro na IA ao gerar plano diário: {e}")
        raise Exception(f"Falha na IA ao gerar plano diário completo: {str(e)}")

# --- Relatório Trimestral (Documento) ---

def gerar_relatorio_trimestral_ia(dossie_aluno_str):
    """
    Usa a IA para ler o dossiê (histórico completo de frequência, observações, planos ministrados e 
    atividades) do aluno durante o trimestre e gera um relatório estruturado.
    Retorna um dicionário com 5 chaves correspondentes às seções do documento.
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
Você é um professor especializado em pedagogia do Ensino Fundamental. Sua tarefa é escrever um "Relatório Descritivo Individual" de um aluno ao final de um trimestre.

Você receberá um DOSSIÊ do aluno contendo:
- Frequência (presenças/faltas)
- Observações diárias registradas
- Resumo dos planos de aula (conteúdos ministrados e BNCC) que a turma teve
- Avaliações e notas (se existirem)

Com base SOMENTE nestes dados (é proibido inventar informações que contrariem o dossiê, mas você deve inferir o comportamento e o desenvolvimento com base no contexto pedagógico), preencha as seguintes 5 seções do relatório. Use linguagem técnica, acolhedora, objetiva e adequada ao Ensino Fundamental. 
NUNCA reutilize textos genéricos, personalize o máximo possível baseando-se nas observações do dossiê.

Retorne APENAS um JSON válido contendo as seguintes chaves (o valor de cada chave deve ser um texto contínuo bem estruturado, usando quebras de linha \\n para parágrafos):

{{
  "visao_geral": "Introdução geral. Resuma a frequência, participação, comportamento, responsabilidade e evolução do aluno.",
  "linguagem": "Análise sobre oralidade, leitura, escrita, produção textual e desenvolvimento (se houver dados. Se não houver muitos dados, seja genérico mas embasado nas aulas de linguagem).",
  "matematica": "Análise sobre raciocínio lógico, resolução de problemas, números e evolução matemática.",
  "ciencias": "Análise sobre Ciências Humanas e da Natureza (Ciências, História, Geografia). Curiosidade, interação.",
  "conclusao": "Conclusão com evolução, principais conquistas, desafios existentes e recomendações pedagógicas."
}}

ATENÇÃO: Se o dossiê estiver muito vazio, informe nas seções de forma polida que os registros daquele eixo foram limitados, mas tente extrair o máximo do comportamento geral.

DOSSIÊ DO ALUNO:
{dossie}
"""

    prompt = PromptTemplate(input_variables=["dossie"], template=template)
    chain = prompt | llm
    
    try:
        resposta = chain.invoke({"dossie": dossie_aluno_str})
        content = resposta.content.strip()
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*', '', content)
        return json.loads(content)
    except Exception as e:
        print(f"Erro na IA ao gerar relatório trimestral: {e}")
        raise Exception(f"Falha na IA ao gerar relatório trimestral: {str(e)}")

def gerar_resumo_dashboard_ia(dados_texto):
    """
    Recebe um dump de dados do dashboard em texto/JSON e pede à IA um resumo gerencial.
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
Você é um consultor pedagógico analisando os dados de um Dashboard Escolar.
Com base nos dados fornecidos abaixo, crie um Resumo Executivo destacando:
1. Principais avanços da turma (ou do aluno, se filtrado).
2. Principais dificuldades ou pontos de atenção (ex: faltas, planos pendentes).
3. Habilidades da BNCC que precisam ser reforçadas (se houver dados).
4. Recomendações pedagógicas curtas e objetivas.

Use formatação em Markdown (com negritos e bullet points).
Mantenha o texto profissional, encorajador e direto ao ponto.
Não invente dados, baseie-se estritamente no que foi fornecido.

DADOS DO DASHBOARD:
{dados}
    """

    prompt = PromptTemplate(
        input_variables=["dados"],
        template=template
    )

    chain = prompt | llm
    
    try:
        resposta = chain.invoke({"dados": dados_texto})
        return resposta.content
    except Exception as e:
        print(f"Erro na IA ao gerar resumo do dashboard: {e}")
        raise Exception(f"Falha na comunicação com a IA: {str(e)}")
