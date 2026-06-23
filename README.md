# ConectaPharma

**Saúde, tecnologia e solidariedade conectando vidas.**

O **ConectaPharma** é um protótipo web full-stack voltado à assistência farmacêutica em rede. A plataforma tem como objetivo conectar cidadãos, farmácias, unidades de distribuição, instituições parceiras, voluntários e agentes comunitários para facilitar o acesso a medicamentos, reduzir deslocamentos desnecessários e validar um modelo de apoio comunitário à saúde.

O projeto utiliza:

* **Frontend estático** em HTML, CSS e JavaScript;
* **Firebase Authentication** para login/cadastro com e-mail/senha e Google;
* **Cloud Firestore** para persistência de usuários, formulários, métricas e dados operacionais do MVP;
* **Firebase Hosting** para publicação do frontend;
* **GitHub Actions** para deploy automatizado no Firebase Hosting;
* **Backend FastAPI** para API complementar, simulações, alertas, farmácias mapeadas, logística e base de integração futura com RNDS/DATASUS.

---

## 1. Visão Geral

O ConectaPharma foi desenvolvido como MVP acadêmico e tecnológico para validar uma solução de impacto social no acesso a medicamentos.

O problema central é que muitos pacientes, especialmente idosos, pessoas com mobilidade reduzida, pacientes crônicos e famílias de baixa renda, enfrentam dificuldades para:

* Encontrar medicamentos disponíveis;
* Saber onde retirar medicamentos;
* Acompanhar reposições;
* Receber apoio para retirada ou entrega;
* Obter informações simples sobre uso e acesso;
* Reduzir deslocamentos desnecessários.

O MVP busca validar a solução por meio de:

* Acessos à plataforma;
* Pesquisas de medicamentos;
* Cliques em farmácias, endereços e contatos;
* Envio de formulários;
* Criação de alertas;
* Simulações de entrega comunitária;
* Feedbacks dos usuários.

---

## 2. Funcionalidades Principais

### 2.1 Autenticação

* Cadastro com e-mail e senha;
* Login com e-mail e senha;
* Login/cadastro com conta Google;
* Criação automática de documento do usuário no Firestore;
* Atualização de `lastLoginAt`;
* Controle inicial de papéis por `role`, como `USER` e `ADMIN`.

### 2.2 Plataforma Web

* Página inicial institucional;
* Tela de login/cadastro;
* Área autenticada do usuário;
* Dashboard inicial;
* Integração com Firebase;
* Integração opcional com backend FastAPI;
* Fallback visual quando a API local estiver indisponível.

### 2.3 Firestore

Coleções previstas ou utilizadas no MVP:

* `users`;
* `contact_forms`;
* `feedbacks`;
* `pharmacy_interest_forms`;
* `medicine_search_requests`;
* `search_logs`;
* `click_logs`;
* `form_submit_logs`;
* `medicine_alerts`;
* `delivery_simulations`;
* `institutions`;
* `medications`;
* `inventory`.

### 2.4 Backend FastAPI

O backend fornece uma API complementar para:

* Alertas simulados de consumo;
* Farmácias mapeadas;
* Simulação de logística;
* Verificação de sessão;
* Base de integração governamental;
* Endpoints de RNDS/DATASUS em modo `dry-run`.

### 2.5 Deploy

O projeto suporta:

* Deploy manual com Firebase CLI;
* Deploy automático com GitHub Actions;
* Preview automático em Pull Requests;
* Publicação do frontend estático via Firebase Hosting.

---

## 3. Estrutura do Projeto

```text
ConectaPharma/
├── Backend/
│   ├── backend_python.py
│   └── .env.example
├── Frontend/
│   ├── assets/
│   │   └── firebaseClient.js
│   ├── index.html
│   ├── login.html
│   ├── plataforma.html
│   └── .env.example
├── Firebase/
│   ├── firestore.rules
│   ├── firestore.indexes.json
│   └── README_FIREBASE.md
├── docs/
├── tests/
│   └── test_backend.py
├── .github/
│   └── workflows/
│       ├── firebase-hosting-merge.yml
│       └── firebase-hosting-pull-request.yml
├── .env.example
├── .firebaserc
├── .gitignore
├── firebase.json
├── requirements.txt
└── README.md
```

---

## 4. Configuração Firebase

### 4.1 Projeto Firebase

Projeto utilizado:

```text
conectapharma-33fd7
```

Região configurada para Firestore:

```text
southamerica-east1
```

Essa região corresponde ao Brasil/São Paulo e é a opção mais adequada para um MVP com usuários no Brasil.

---

## 5. Arquivos Firebase

A configuração principal do Firebase CLI fica na raiz:

```text
firebase.json
.firebaserc
```

Os arquivos auxiliares do Firestore ficam na pasta:

```text
Firebase/
```

### 5.1 `firebase.json`

O arquivo `firebase.json` deve apontar para o frontend e para os arquivos da pasta `Firebase/`:

```json
{
  "firestore": {
    "database": "(default)",
    "location": "southamerica-east1",
    "rules": "Firebase/firestore.rules",
    "indexes": "Firebase/firestore.indexes.json"
  },
  "hosting": {
    "public": "Frontend",
    "ignore": [
      "firebase.json",
      "**/.*",
      "**/node_modules/**"
    ]
  },
  "auth": {
    "providers": {
      "emailPassword": true,
      "googleSignIn": {
        "oAuthBrandDisplayName": "ConectaPharma",
        "supportEmail": "claudiofranciscojunior2006@gmail.com"
      }
    }
  }
}
```

### 5.2 Configuração do Firebase Web SDK

A configuração pública do Firebase Web App está centralizada em:

```text
Frontend/assets/firebaseClient.js
```

Esse arquivo concentra a integração com:

* Firebase App;
* Firebase Authentication;
* GoogleAuthProvider;
* Cloud Firestore;
* Firebase Analytics, quando suportado;
* Funções auxiliares de login, cadastro, logout, logs e métricas.

---

## 6. Variáveis de Ambiente

O projeto possui arquivos de exemplo:

```text
.env.example
Frontend/.env.example
Backend/.env.example
```

Copie o arquivo de exemplo antes de rodar localmente:

```powershell
Copy-Item .env.example .env
```

### 6.1 Variáveis gerais

```env
CONNECTAPHARMA_SECRET_KEY=
CONNECTAPHARMA_ALLOW_LEGACY_JWT=false
CONNECTAPHARMA_FIREBASE_PROJECT_ID=conectapharma-33fd7
CONNECTAPHARMA_FIREBASE_CREDENTIALS_PATH=
GOOGLE_APPLICATION_CREDENTIALS=
```

### 6.2 Firebase Admin no backend

Para que o backend valide Firebase ID Tokens, gere uma chave de service account no Firebase Console e configure uma das variáveis:

```env
CONNECTAPHARMA_FIREBASE_CREDENTIALS_PATH=C:\caminho\seguro\service-account.json
```

ou:

```env
GOOGLE_APPLICATION_CREDENTIALS=C:\caminho\seguro\service-account.json
```

Nunca envie esse arquivo JSON para o GitHub.

---

## 7. Como Rodar Localmente

### 7.1 Backend FastAPI

Na raiz do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Depois execute:

```powershell
cd Backend
python backend_python.py
```

A API ficará disponível em:

```text
http://127.0.0.1:8000
```

Documentação interativa:

```text
http://127.0.0.1:8000/docs
```

### 7.2 Frontend

Em outro terminal, execute:

```powershell
cd Frontend
python -m http.server 5500
```

Acesse:

```text
http://127.0.0.1:5500/index.html
```

Não abra os arquivos diretamente com `file://`, pois o projeto usa módulos JavaScript e integração com Firebase.

---

## 8. Autenticação

O fluxo principal de autenticação utiliza Firebase Authentication.

Provedores habilitados:

* Email/Password;
* Google Sign-In.

No Firebase Console, confira em:

```text
Authentication > Sign-in method
```

Domínios autorizados recomendados:

```text
localhost
127.0.0.1
conectapharma-33fd7.web.app
conectapharma-33fd7.firebaseapp.com
```

---

## 9. Cloud Firestore

O Firestore é usado para persistência operacional e métricas do MVP.

### 9.1 Regras de segurança

Arquivo:

```text
Firebase/firestore.rules
```

As regras foram projetadas para:

* Permitir que usuários autenticados leiam e atualizem apenas o próprio documento;
* Permitir envio público de formulários e logs básicos;
* Impedir leitura pública de formulários, logs e métricas;
* Restringir leitura administrativa a usuários com `role == "ADMIN"`;
* Permitir leitura pública de medicamentos, instituições e estoque;
* Restringir escrita em dados operacionais a administradores;
* Impedir exclusão por usuários comuns.

### 9.2 Indexes

Arquivo:

```text
Firebase/firestore.indexes.json
```

---

## 10. Deploy Manual no Firebase

### 10.1 Login

```powershell
firebase login
```

### 10.2 Selecionar projeto

```powershell
firebase use conectapharma-33fd7
```

### 10.3 Deploy do Firestore

```powershell
firebase deploy --only firestore
```

### 10.4 Deploy do Hosting

```powershell
firebase deploy --only hosting
```

URL de produção:

```text
https://conectapharma-33fd7.web.app
```

---

## 11. GitHub Actions

O projeto foi configurado com GitHub Actions para Firebase Hosting.

Arquivos principais:

```text
.github/workflows/firebase-hosting-merge.yml
.github/workflows/firebase-hosting-pull-request.yml
```

### 11.1 Produção

O workflow de merge publica automaticamente no canal `live` do Firebase Hosting quando houver alteração enviada para a branch:

```text
main
```

### 11.2 Pull Requests

O workflow de pull request cria uma URL temporária de preview para validação antes do merge.

### 11.3 Secret do GitHub

O Firebase CLI criou no GitHub o secret:

```text
FIREBASE_SERVICE_ACCOUNT_CONECTAPHARMA_33FD7
```

Esse secret é usado pelo workflow para publicar no Firebase Hosting.

Não exponha nem copie esse JSON para arquivos versionados.

---

## 12. GitHub Pages

O fluxo principal de deploy do projeto passou a ser o **Firebase Hosting**.

Caso ainda exista workflow antigo para GitHub Pages, ele pode ser mantido apenas como alternativa secundária ou removido para evitar duplicidade de publicação.

URL Firebase recomendada:

```text
https://conectapharma-33fd7.web.app
```

URL GitHub Pages, caso continue ativa:

```text
https://cfsjcode.github.io/ConectaPharma/
```

---

## 13. Integração com Meu SUS Digital / RNDS

O app Meu SUS Digital não deve ser tratado como uma API pública direta para protótipos.

A integração oficial com dados e serviços digitais do SUS depende de fluxos institucionais, credenciamento, CNES, homologação, certificado digital ICP-Brasil e acesso via portfólios oficiais, como RNDS/DATASUS.

O backend está preparado com endpoints para essa integração em modo seguro:

```text
GET /api/v1/integracoes/rnds/status
POST /api/v1/integracoes/rnds/dispensacao
```

Por padrão, os endpoints operam em modo:

```text
dry-run
```

Nesse modo, o backend monta a estrutura localmente, mas não envia dados reais ao DATASUS.

Para envio real, configure as variáveis `CONNECTAPHARMA_RNDS_*` no `.env` com credenciais, certificados e URLs aprovadas.

Mais detalhes podem ser documentados em:

```text
docs/rnds.md
```

---

## 14. Testes

Execute na raiz do projeto:

```powershell
python -m pytest
```

---

## 15. Segurança e Privacidade

O ConectaPharma não deve armazenar:

* CPF;
* CNS/cartão SUS;
* Diagnóstico;
* Receita médica;
* Laudos;
* Dados clínicos sensíveis;
* Senhas;
* Chaves privadas;
* Certificados digitais;
* JSON de service account do Firebase.

Arquivos que não devem ser enviados ao GitHub:

```text
.env
*.env
service-account.json
firebase-adminsdk*.json
credentials.json
secrets/
.firebase/
```

O repositório deve versionar somente arquivos de exemplo:

```text
.env.example
Frontend/.env.example
Backend/.env.example
```

---

## 16. Preparar Commit e Push

Verifique o estado do repositório:

```powershell
git status
```

Adicione os arquivos:

```powershell
git add .
```

Crie o commit:

```powershell
git commit -m "Atualiza documentação e configuração Firebase do ConectaPharma"
```

Envie para o GitHub:

```powershell
git push origin main
```

---

## 17. Limpeza Recomendada

Caso tenham sido criados arquivos acidentais durante o `firebase init`, remova-os do versionamento.

Arquivos que não devem permanecer versionados:

```text
n
.firebase/
Firebase/.firebaserc
Firebase/firebase.json
Firebase/requirements.txt
```

A estrutura correta é:

```text
.firebaserc
firebase.json
requirements.txt
Firebase/firestore.rules
Firebase/firestore.indexes.json
Firebase/README_FIREBASE.md
```

Se algum desses arquivos já tiver sido commitado por engano, use:

```powershell
git rm n
git rm -r --cached .firebase
git rm Firebase/.firebaserc
git rm Firebase/firebase.json
git rm Firebase/requirements.txt
```

Depois atualize o `.gitignore`:

```gitignore
.firebase/
.env
*.env
!.env.example
*service-account*.json
*firebase-adminsdk*.json
credentials.json
secrets/
```

---

## 18. Comandos Úteis

### Deploy completo

```powershell
firebase deploy
```

### Deploy somente Hosting

```powershell
firebase deploy --only hosting
```

### Deploy somente Firestore

```powershell
firebase deploy --only firestore
```

### Ver projeto Firebase atual

```powershell
firebase use
```

### Ver status Git

```powershell
git status
```

### Ver workflows

```powershell
dir .github\workflows
```

---

## 19. Status Atual do Projeto

* Firebase Authentication configurado;
* Firestore criado em `southamerica-east1`;
* Firestore Rules publicadas;
* Firebase Hosting publicado;
* GitHub Actions configurado;
* Secret de deploy criado no GitHub;
* Frontend publicado via Firebase Hosting;
* Backend preparado para validação de Firebase ID Token;
* RNDS/DATASUS mantido como integração futura em modo `dry-run`.

---

## 20. Licença e Uso

Este projeto foi desenvolvido para fins acadêmicos, validação de MVP e demonstração de impacto social aplicado à saúde pública, tecnologia e solidariedade comunitária.

Não utilize dados reais de pacientes sem base legal, consentimento adequado, avaliação ética e conformidade com a LGPD.
