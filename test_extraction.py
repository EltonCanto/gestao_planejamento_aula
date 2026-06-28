import os
import django

# Setup django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from escola.services import extrair_texto_arquivo, resumir_arquivo_ia

def run_test():
    print("Testando extração de texto e resumo IA...")
    
    file_path = "dummy.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("Este é um documento escolar sobre a importância da preservação da água no planeta Terra.")
        
    # Como não temos um OCR fake configurado na extração para .txt, vamos chamar o resumo IA direto
    # Mas a função extrair_texto_arquivo não cobre .txt. Vou simular.
    texto = "Este é um documento escolar sobre a importância da preservação da água no planeta Terra."
    
    print("\nTexto extraído (Simulado para TXT):", texto)
    
    print("\nChamando a IA para resumir o conteúdo...")
    resumo = resumir_arquivo_ia(texto)
    print("Resumo da IA:", resumo)
    
    if os.path.exists(file_path):
        os.remove(file_path)

if __name__ == "__main__":
    run_test()
