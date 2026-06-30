import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
import io

# Escopos necessários para ler/escrever arquivos no Drive
SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDENTIALS_FILE = 'client_secret_515767878524-kidm2nv1qbc2rp4gcj6r52rghch7mojh.apps.googleusercontent.com.json'

def get_drive_service():
    """
    Obtém o serviço do Google Drive autenticado.
    Se o token.json não existir, inicia o fluxo de autenticação via browser.
    Agora suporta Variáveis de Ambiente para facilitar o deploy no Portainer.
    """
    import json
    
    creds = None
    token_path = 'token.json'
    
    # 1. Tenta carregar o token da variável de ambiente (Deploy Portainer)
    env_token = os.getenv('GOOGLE_DRIVE_TOKEN_JSON')
    if env_token:
        try:
            token_info = json.loads(env_token)
            creds = Credentials.from_authorized_user_info(token_info, SCOPES)
        except Exception as e:
            print("Erro ao carregar token da variável de ambiente:", e)

    # 2. Fallback para arquivo local se a variável não existir
    if not creds and os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    # Se não houver credenciais válidas disponíveis, atualiza ou pede login.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            env_secret = os.getenv('GOOGLE_DRIVE_CLIENT_SECRET_JSON')
            if env_secret:
                try:
                    client_config = json.loads(env_secret)
                    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
                except Exception as e:
                    print("Erro ao carregar client secret da variável:", e)
                    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            else:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                
            # Rodar o servidor localmente para receber o callback (só funciona localmente)
            creds = flow.run_local_server(port=0)
        
        # Salva as credenciais para o próximo uso
        try:
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        except Exception:
            pass # Ignora silenciosamente se for readonly
            
    return build('drive', 'v3', credentials=creds)

def get_or_create_folder(service, folder_name="Atividade_pedagogia"):
    """
    Busca por uma pasta com o nome especificado. Se não encontrar, cria a pasta.
    (Nota: com o escopo drive.file, ele só enxerga pastas criadas pelo próprio app. 
    Se não achar a pasta que o usuário criou manualmente, ele criará uma nova com o mesmo nome).
    """
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    items = results.get('files', [])
    
    if not items:
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')
    else:
        return items[0].get('id')

def upload_arquivo(file_path, nome_destino):
    """
    Sobe o arquivo para a pasta 'Atividade_pedagogia' do Google Drive.
    Altera as permissões para Qualquer Pessoa com o link poder ler.
    Retorna uma tupla (file_id, link_compartilhado).
    """
    service = get_drive_service()
    
    # Obtém o ID da pasta alvo
    folder_id = get_or_create_folder(service, "Atividade_pedagogia")
    
    file_metadata = {
        'name': nome_destino,
        'parents': [folder_id]
    }
    # MIME type vazio faz com que a API tente adivinhar
    media = MediaFileUpload(file_path, resumable=True)
    
    # Upload do arquivo
    file = service.files().create(
        body=file_metadata, 
        media_body=media, 
        fields='id, webViewLink'
    ).execute()
    
    file_id = file.get('id')
    link = file.get('webViewLink')
    
    # Configurar permissão para visualização pública
    permission = {
        'type': 'anyone',
        'role': 'reader',
    }
    service.permissions().create(
        fileId=file_id,
        body=permission,
        fields='id'
    ).execute()
    
    return file_id, link

def upload_pdf_em_memoria(pdf_bytes, nome_destino, folder_name="plano_aula_diario"):
    """
    Sobe um PDF (bytes) diretamente da memória para o Google Drive.
    Altera as permissões para Qualquer Pessoa com o link poder ler.
    Retorna uma tupla (file_id, link_compartilhado).
    """
    service = get_drive_service()
    
    # Obtém o ID da pasta alvo
    folder_id = get_or_create_folder(service, folder_name)
    
    file_metadata = {
        'name': nome_destino,
        'parents': [folder_id],
        'mimeType': 'application/pdf'
    }
    
    fh = io.BytesIO(pdf_bytes)
    media = MediaIoBaseUpload(fh, mimetype='application/pdf', resumable=True)
    
    # Upload do arquivo
    file = service.files().create(
        body=file_metadata, 
        media_body=media, 
        fields='id, webViewLink'
    ).execute()
    
    file_id = file.get('id')
    link = file.get('webViewLink')
    
    # Configurar permissão para visualização pública
    permission = {
        'type': 'anyone',
        'role': 'reader',
    }
    service.permissions().create(
        fileId=file_id,
        body=permission,
        fields='id'
    ).execute()
    
    return file_id, link
