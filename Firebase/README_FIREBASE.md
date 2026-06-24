# ConectaPharma — Integração Firebase Free/Spark + FastAPI

## Resumo técnico

Esta versão integra o ConectaPharma ao Firebase no plano Free/Spark e conecta a autenticação do frontend com o backend FastAPI usando **Firebase ID Token**.

A autenticação principal passa a ser:

1. O usuário faz login/cadastro no navegador com Firebase Authentication.
2. O frontend obtém o Firebase ID Token com `user.getIdToken()`.
3. O frontend envia o token ao FastAPI no cabeçalho `Authorization: Bearer <token>`.
4. O backend valida a assinatura do token com o Firebase Admin SDK.
5. As rotas protegidas usam o usuário Firebase validado.

## Arquivos alterados

```txt
login.html
plataforma.html
backend_python.py
assets/firebaseClient.js
.env.example
README_FIREBASE.md
```

## Arquivos adicionados

```txt
requirements.txt
firestore.rules
firebase.json
.firebaserc
```

## Recursos Firebase utilizados

- Firebase App;
- Firebase Authentication;
- Login com e-mail e senha;
- Cadastro com e-mail e senha;
- Login/cadastro com GoogleAuthProvider;
- Cloud Firestore;
- Firebase Analytics, quando suportado pelo navegador;
- Firebase Hosting;
- Firebase Admin SDK no backend FastAPI para validação de ID Token.

## Recursos não utilizados

- Firebase Storage;
- Cloud Functions;
- Dados médicos sensíveis;
- Senhas no Firestore;
- Integração direta com SUS/gov.br.

## Configuração no Console Firebase

1. Acesse o projeto `conectapharma-33fd7`.
2. Ative **Authentication**.
3. Em **Sign-in method**, habilite:
   - Email/password;
   - Google.
4. Ative o **Cloud Firestore**.
5. Publique as regras do arquivo `firestore.rules`.
6. Ative o **Analytics**, se ainda não estiver ativo.
7. Em **Project settings > Service accounts**, gere uma chave privada JSON para o backend FastAPI.
8. Salve o JSON fora do repositório, por exemplo:

```txt
C:\\segredos\\conectapharma-service-account.json
```

Nunca versionar o JSON de service account.

## Configuração correta do Firebase Web SDK no frontend

O projeto atual usa HTML/JS estático, portanto a configuração do app Web do Firebase **não deve ser colada diretamente em `index.html`, `login.html` ou `plataforma.html`**.

O local correto é:

```txt
Frontend/assets/firebaseClient.js
```

Esse arquivo já centraliza `initializeApp`, `getAuth`, `getFirestore`, `getAnalytics`, autenticação, persistência de usuário e métricas. As páginas HTML importam esse módulo para evitar acoplamento direto do Firebase em cada tela.

O arquivo `.env.example` também foi preenchido com as mesmas variáveis para futura migração para Vite ou outro bundler:

```env
VITE_FIREBASE_API_KEY=valor_configurado
VITE_FIREBASE_AUTH_DOMAIN=conectapharma-33fd7.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=conectapharma-33fd7
VITE_FIREBASE_STORAGE_BUCKET=conectapharma-33fd7.firebasestorage.app
VITE_FIREBASE_APP_ID=valor_configurado
VITE_FIREBASE_MESSAGING_SENDER_ID=137881875886
VITE_FIREBASE_MEASUREMENT_ID=G-QEJ27VVTM7
```

## Variáveis de ambiente do backend

Configure o backend FastAPI com:

```env
CONNECTAPHARMA_FIREBASE_PROJECT_ID=conectapharma-33fd7
CONNECTAPHARMA_FIREBASE_CREDENTIALS_PATH=C:\\segredos\\conectapharma-service-account.json
CONNECTAPHARMA_FIREBASE_VERIFY_REVOKED=false
CONNECTAPHARMA_ALLOW_LEGACY_JWT=false
```

Alternativamente, é possível usar a variável padrão:

```env
GOOGLE_APPLICATION_CREDENTIALS=C:\\segredos\\conectapharma-service-account.json
```

## Execução local do frontend

Por usar módulos ES importados via CDN, não abra os arquivos diretamente por `file://`. Execute um servidor local dentro da pasta do projeto:

```bash
python -m http.server 5500
```

Depois acesse:

```txt
http://localhost:5500/index.html
```

## Execução local do backend

Instale as dependências:

```bash
pip install -r requirements.txt
```

Configure o caminho do service account:

```powershell
$env:CONNECTAPHARMA_FIREBASE_CREDENTIALS_PATH="C:\\segredos\\conectapharma-service-account.json"
$env:CONNECTAPHARMA_FIREBASE_PROJECT_ID="conectapharma-33fd7"
```

Execute a API:

```bash
uvicorn backend_python:app --host 127.0.0.1 --port 8000 --reload
```

Teste a API:

```txt
http://127.0.0.1:8000/docs
```

## Rotas protegidas por Firebase ID Token

As rotas que usam `Depends(get_current_user)` passam a validar Firebase ID Token:

```txt
GET  /api/v1/auth/me
POST /api/v1/saude/consumo/simulacao
POST /api/v1/logistica/entrega
GET  /api/v1/logistica/entrega/{tracking_id}
GET  /api/v1/integracoes/rnds/status
POST /api/v1/integracoes/rnds/dispensacao
```

As rotas públicas de demonstração permanecem acessíveis para manter o live demo da landing page:

```txt
GET /api/v1/alertas
GET /api/v1/farmacias/mapa
```

## Fluxo de autenticação atualizado

### `login.html`

- Usa `signInWithEmail()` para login com e-mail/senha;
- Usa `signUpWithEmail()` para cadastro;
- Usa `signInWithGoogle()` para login/cadastro Google;
- Persiste usuário em `users/{uid}` no Firestore;
- Salva uma sessão mínima em `sessionStorage`;
- Armazena o Firebase ID Token em `sessionStorage` apenas para integração imediata com o backend.

### `plataforma.html`

- Usa `onAuthStateChange()` para validar sessão Firebase;
- Obtém o token com `getCurrentIdToken()`;
- Envia `Authorization: Bearer <Firebase ID Token>` para o FastAPI;
- Valida sessão em `/api/v1/auth/me`;
- Exibe fallback local se a API estiver offline ou sem Firebase Admin configurado;
- Usa `signOutUser()` no logout.

### `backend_python.py`

- Inicializa Firebase Admin SDK com service account;
- Valida Firebase ID Token com `firebase_auth.verify_id_token()`;
- Converte claims Firebase em usuário compatível com o modelo atual;
- Mantém JWT legado apenas se `CONNECTAPHARMA_ALLOW_LEGACY_JWT=true`;
- Não grava senhas e não depende mais do backend para login/cadastro principal.

## Coleções Firestore previstas

### `users/{uid}`

```js
{
  uid: string,
  name: string,
  email: string,
  photoURL: string | null,
  provider: 'email' | 'google',
  role: 'USER' | 'ADMIN',
  createdAt: serverTimestamp,
  lastLoginAt: serverTimestamp,
  active: true
}
```

### Formulários

```txt
contact_forms
feedbacks
pharmacy_interest_forms
medicine_search_requests
```

### Métricas

```txt
search_logs
click_logs
form_submit_logs
auth_logs
alert_logs
delivery_simulation_logs
```

### Dados operacionais públicos

```txt
medications
institutions
inventory
```

## Deploy Firebase Hosting

Instale ou atualize a Firebase CLI:

```bash
npm install -g firebase-tools
```

Autentique:

```bash
firebase login
```

Publique regras e hosting:

```bash
firebase deploy --only firestore:rules
firebase deploy --only hosting
```

Ou publique tudo:

```bash
firebase deploy
```

## Observações de segurança

- A chave `apiKey` do Firebase Web SDK identifica o projeto no cliente; ela não é uma chave privada.
- A proteção real depende das regras do Firestore, domínios autorizados no Firebase Authentication e restrições de API key no Google Cloud Console.
- O JSON de service account do Firebase Admin SDK é privado e nunca deve ir para GitHub.
- Nenhuma senha é gravada no Firestore.
- O MVP não deve coletar CPF, cartão SUS, diagnóstico, receita, laudo ou justificativa médica.
- `CONNECTAPHARMA_ALLOW_LEGACY_JWT=false` deve ser mantido quando a autenticação oficial for Firebase.

## Checklist de validação

1. Login com e-mail/senha funciona.
2. Cadastro com e-mail/senha funciona.
3. Login com Google funciona.
4. Documento `users/{uid}` é criado/atualizado.
5. `lastLoginAt` é atualizado.
6. `plataforma.html` obtém Firebase ID Token.
7. `/api/v1/auth/me` valida o token no backend.
8. Rotas protegidas aceitam `Authorization: Bearer <Firebase ID Token>`.
9. Logout encerra sessão Firebase.
10. O fallback visual continua funcionando quando o backend está offline.

## Farmácias próximas com OpenStreetMap/Overpass

A funcionalidade de farmácias abertas próximas usa exclusivamente OpenStreetMap/Overpass como fonte externa gratuita. A arquitetura implementada é:

```text
Frontend → FastAPI → OpenStreetMap/Overpass → FastAPI processa → Frontend renderiza
```

O frontend apenas solicita permissão de localização e envia `lat`/`lng` ao backend. O FastAPI executa:

- consulta gratuita à Overpass API;
- cache em memória;
- cálculo de distância por Haversine;
- interpretação básica de `opening_hours`;
- filtro `open_now=true`;
- ordenação por distância crescente.

Endpoint:

```text
GET /api/v1/farmacias/proximas?lat=-19.9191&lng=-43.9386&radius_km=10&open_now=true&limit=10&source=overpass
```

Para teste sem chamada externa:

```text
GET /api/v1/farmacias/proximas?lat=-19.9191&lng=-43.9386&radius_km=10&open_now=true&limit=10&source=mock
```
