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
    """
    creds = None
    token_path = 'token.json'
    
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    # Se não houver credenciais válidas disponíveis, pede para o usuário logar.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            # Rodar o servidor localmente para receber o callback
            creds = flow.run_local_server(port=0)
        
        # Salva as credenciais para o próximo uso
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
            
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
