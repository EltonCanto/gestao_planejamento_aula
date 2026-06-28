# 🚀 Guia de Implantação (Deploy) na Hostinger com Docker & Portainer

Este documento descreve as etapas para realizar a implantação (deploy) da aplicação **Gestão de Planejamento de Aula** em um ambiente de produção (Hostinger) usando o Portainer, seguindo as melhores práticas de DevOps, escalabilidade e segurança.

---

## 1. Preparação da Infraestrutura (Hostinger)

1. Acesse o **Painel da sua VPS** na Hostinger.
2. Certifique-se de que o sistema operacional instalado possui suporte ao Docker (ex: *Ubuntu com Docker e Portainer pré-instalados*).
3. Faça login na interface do **Portainer** (geralmente via `https://ip-do-servidor:9443`).

---

## 2. Configurando o Portainer (Stack / GitHub)

O Portainer permite clonar o seu repositório do GitHub e manter a aplicação sempre atualizada.

### Passo 2.1: Criar a Stack
1. No Portainer, selecione o seu ambiente (`local`).
2. No menu lateral, vá em **Stacks** e clique em **Add stack**.
3. Dê o nome de `gestao-aulas` para a stack.
4. Escolha a opção **Repository**.
5. Em **Repository URL**, cole o link do seu projeto: `https://github.com/EltonCanto/gestao_planejamento_aula.git`.
6. Em **Repository reference**, digite `refs/heads/master` (ou `main`, se mudou a branch).
7. Em **Compose path**, deixe como está: `docker-compose.yml`.

### Passo 2.2: Variáveis de Ambiente (Segurança)
A aplicação agora exige credenciais secretas para funcionar, garantindo que suas senhas **nunca** fiquem no GitHub.

Ainda na tela de criação da Stack no Portainer, role para baixo até **Environment variables** e clique em **Advanced mode**. Cole o seguinte modelo e substitua pelos seus dados reais (veja `.env.example`):

```env
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=cole-uma-chave-aleatoria-e-longa-aqui-12345
DJANGO_ALLOWED_HOSTS=ip-do-servidor,seu-dominio.com.br
OPENROUTER_API_KEY=sua-chave-aqui
```

### Passo 2.3: Implantar
Por fim, clique em **Deploy the stack**.
O Portainer irá baixar o repositório, construir (build) a imagem Docker usando o `Dockerfile`, executar o script `entrypoint.sh` (que migra o banco de dados e coleta os arquivos estáticos) e subirá o sistema!

Acesse a aplicação via: `http://ip-do-servidor`.

---

## 3. Volumes Persistentes (Sem Perda de Dados)

O `docker-compose.yml` criou 3 volumes de armazenamento de segurança:
* **gestao_aulas_db**: Armazena o banco de dados `db.sqlite3`.
* **gestao_aulas_media**: Armazena uploads e relatórios PDFs/DOCX.
* **gestao_aulas_google_auth**: Armazena o `token.json` da sua conta do Google Drive para que você não precise relogar.

Se o container for excluído ou atualizado, os dados **estarão seguros nesses volumes**.

---

## 4. Atualização da Aplicação (Update)

Sempre que você criar um novo recurso ou consertar um bug e der um `git push` para o GitHub, siga estes passos para atualizar o servidor sem quedas longas:

1. Acesse a **Stack** `gestao-aulas` no Portainer.
2. Vá até a aba **Editor**.
3. Clique no botão **Pull and redeploy**.
4. O Portainer baixará as alterações do GitHub, fará um novo build veloz (usando cache local do pip) e reiniciará a aplicação perfeitamente com os novos recursos!

---

## 5. Backups

O arquivo `scripts/backup.sh` foi criado para facilitar a compactação de tudo que importa.

**Para fazer backup manualmente via Portainer:**
1. Vá na aba **Containers**, encontre o container da sua aplicação (`gestao_aulas_web`).
2. Clique no ícone de **Console** (Exec console) do lado direito e conecte-se.
3. No terminal preto que abrirá, digite: `bash scripts/backup.sh`
4. Ele gerará um arquivo na pasta `/app/backups/backup_data_hora.tar.gz`. Você pode extrair esse arquivo do servidor via SSH (SFTP).

> **Recuperação de Desastres:** Se tudo for perdido, instale uma nova Stack do zero no Portainer, entre no Console do container, e substitua os arquivos da pasta `/app/db/` e `/app/media/` pelos arquivos do seu backup `.tar.gz`. Reinicie o container e pronto!
