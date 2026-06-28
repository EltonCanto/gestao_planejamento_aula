import os
import django

# Setup django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from escola.google_drive import get_drive_service, upload_arquivo

def run_test():
    print("Iniciando teste do Google Drive API...")
    
    # 1. Testar Autenticação
    print("Obtendo serviço e verificando token (Isso pode abrir o navegador)...")
    service = get_drive_service()
    print("Serviço autenticado com sucesso!")
    
    # 2. Criar um arquivo de teste local
    file_path = "teste_upload_ia.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("Este é um arquivo de teste para verificar a integração com o Google Drive e Extração de Texto.\nFuncionalidade OK!")
        
    print(f"Arquivo local {file_path} criado.")
    
    # 3. Fazer o Upload
    print("Fazendo upload para o Google Drive...")
    try:
        drive_id, link = upload_arquivo(file_path, "teste_upload_ia.txt")
        print(f"Upload bem sucedido!\nID: {drive_id}\nLink: {link}")
    except Exception as e:
        print(f"Erro no upload: {e}")
        
    # 4. Limpar arquivo local
    if os.path.exists(file_path):
        os.remove(file_path)
        print("Arquivo local removido.")

if __name__ == "__main__":
    run_test()
