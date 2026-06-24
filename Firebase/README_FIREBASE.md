# Firebase — ConectaPharma

Esta versão do ConectaPharma usa uma arquitetura gratuita baseada em:

```text
Firebase Hosting + Firebase Authentication + Cloud Firestore + OpenStreetMap/Overpass
```

Não há backend Python obrigatório em produção.

## Projeto Firebase

```text
Project ID: conectapharma-33fd7
Hosting: https://conectapharma-33fd7.web.app
Firestore region: southamerica-east1
```

## Serviços utilizados

- **Firebase Hosting**: publica os arquivos da pasta `Frontend/`.
- **Firebase Authentication**: login/cadastro por e-mail/senha e Google.
- **Cloud Firestore**: usuários, farmácias cadastradas, medicamentos, alertas, formulários e logs.
- **Firestore Rules**: controle real de permissões administrativas e de usuários comuns.

## Serviços não utilizados nesta versão

- Cloud Functions
- Cloud Run
- App Hosting
- Data Connect
- SQL Connect
- Google Places
- Google Maps API
- Backend público FastAPI

## Arquivos importantes

```text
firebase.json
.firebaserc
Firebase/firestore.rules
Firebase/firestore.indexes.json
Frontend/assets/firebaseClient.js
```

## Publicar regras e hosting

```powershell
firebase use conectapharma-33fd7
firebase deploy --only hosting,firestore:rules
```

## Administrador bootstrap

A conta abaixo é reconhecida como administradora pelas regras de segurança:

```text
claudiofranciscojunior2006@gmail.com
```

Ao autenticar, o frontend grava/atualiza o documento correspondente em `users/{uid}` com `role: "ADMIN"`. Contas comuns ficam como `role: "USER"`.

## Coleções operacionais

- `users`
- `farmacias`
- `medications`
- `medicine_alerts`
- `contact_forms`
- `feedbacks`
- `pharmacy_interest_forms`
- `medicine_search_requests`
- `search_logs`
- `click_logs`
- `form_submit_logs`
- `auth_logs`

## Segurança

- Farmácias e medicamentos podem ser lidos publicamente.
- Criação, edição e exclusão de dados operacionais são restritas a admin.
- Usuários comuns não acessam gestão operacional.
- Chaves privadas, service accounts, senhas e arquivos `.env` não devem ser versionados.
