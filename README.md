# ConectaPharma

**Saúde, tecnologia e solidariedade conectando vidas.**

O ConectaPharma é um MVP web acadêmico para facilitar a consulta de farmácias cadastradas, medicamentos e pontos públicos de atendimento em saúde. Esta versão foi ajustada para operar no modelo **gratuito e estático**, sem backend Python obrigatório em produção.

## Arquitetura atual

```text
Firebase Hosting
├── Frontend HTML/CSS/JavaScript
├── Firebase Authentication
├── Cloud Firestore
│   ├── users
│   ├── farmacias
│   ├── medications
│   ├── medicine_alerts
│   ├── contact_forms
│   ├── feedbacks
│   └── logs operacionais
└── OpenStreetMap/Overpass
    └── Consulta pública de farmácias, UBSs, postos de saúde e UPAs próximos
```

A versão publicada **não depende de FastAPI, Cloud Functions, Cloud Run, Google Places, Google Maps API, App Hosting, SQL Connect ou Data Connect**.

## O que foi alterado nesta versão

- Removidas chamadas obrigatórias para `http://localhost:8000` e `API_BASE_URL` no frontend.
- A plataforma autenticada consulta farmácias cadastradas diretamente na coleção `farmacias` do Firestore.
- Foi adicionada a subpágina `Frontend/cadastrar-farmacias.html` para cadastro manual de farmácias pelo administrador.
- O botão **Cadastrar Farmácias Manualmente** aparece somente na sessão administrativa.
- O catálogo de medicamentos usa diretamente a coleção `medications` do Firestore.
- O cadastro de farmácias e medicamentos é feito diretamente no Firestore e fica restrito ao administrador.
- A conta `claudiofranciscojunior2006@gmail.com` é administradora bootstrap.
- Usuários comuns acessam somente funcionalidades de uso comum.
- A busca de farmácias próximas, UBSs, postos de saúde e UPAs usa OpenStreetMap/Overpass diretamente no frontend.
- Google Maps/Google Places foi removido como fonte de dados.
- O backend Python permanece apenas como referência local/opcional, sem dependência para a versão online.


## Página inicial corporativa

A página `Frontend/index.html` foi redesenhada com uma diretriz visual corporativa e empresarial. A nova página inicial apresenta:

- posicionamento institucional do ConectaPharma;
- proposta de valor do MVP;
- missão, visão e valores;
- modelo de operação da plataforma;
- públicos atendidos;
- governança, segurança e uso gratuito com Firebase + OpenStreetMap;
- CTA direto para acesso à plataforma.

O indicador de farmácias cadastradas na página inicial consulta a coleção `farmacias` do Firestore quando disponível.

## Conta administradora

A conta abaixo possui acesso administrativo:

```text
claudiofranciscojunior2006@gmail.com
```

Ela pode acessar funcionalidades de gestão liberadas no frontend e autorizadas pelas regras do Firestore. Contas comuns recebem papel `USER`.

## Coleções principais do Firestore

### `users`

Documento com ID igual ao UID do Firebase Auth:

```json
{
  "uid": "UID_DO_FIREBASE_AUTH",
  "name": "Cláudio Júnior",
  "email": "claudiofranciscojunior2006@gmail.com",
  "role": "ADMIN",
  "provider": "google",
  "active": true,
  "lastLoginAt": "serverTimestamp"
}
```

### `farmacias`

```json
{
  "nome": "Farmácia Central",
  "endereco": "Av. Afonso Pena, 1000 - Centro, Belo Horizonte/MG",
  "bairro": "Centro",
  "cidade": "Belo Horizonte",
  "telefone": "(31) 99999-9999",
  "whatsapp": "5531999999999",
  "email": "contato@farmacia.com.br",
  "website": "https://www.farmacia.com.br",
  "horario_funcionamento": "Segunda a sexta, 08:00 às 18:00",
  "latitude": -19.9191,
  "longitude": -43.9386,
  "openstreetmap_url": "https://www.openstreetmap.org/?mlat=-19.9191&mlon=-43.9386#map=17/-19.9191/-43.9386",
  "ativo": true,
  "disponibilidade_farmaco": true,
  "origem": "manual_firestore",
  "createdAt": "serverTimestamp",
  "updatedAt": "serverTimestamp"
}
```

### `medications`

```json
{
  "nome": "Losartana 50mg",
  "categoria": "Anti-hipertensivo",
  "descricao": "Medicamento de uso contínuo.",
  "stock": 20,
  "requires_prescription": true,
  "active": true,
  "createdAt": "serverTimestamp",
  "updatedAt": "serverTimestamp"
}
```

## Regras de segurança

As regras estão em:

```text
Firebase/firestore.rules
```

Resumo das permissões:

- `users/{uid}`: cada usuário lê seu próprio documento; admin lê usuários.
- `farmacias`: leitura pública; escrita/edição/exclusão somente admin.
- `medications`: leitura pública; escrita/edição/exclusão somente admin.
- `medicine_alerts`: leitura pelo próprio usuário ou admin; gestão por admin.
- formulários e logs: criação pública/autenticada conforme o caso; leitura administrativa.

## Deploy no Firebase

Na pasta raiz do projeto:

```powershell
cd "D:\Acadêmico\Faculdade - PUC\3º Semestre - 01 2026\Introdução A Inovação Tecnológica\ConectaPharma"

firebase use conectapharma-33fd7
firebase deploy --only hosting,firestore:rules
```

Após publicar, teste com cache busting:

```text
https://conectapharma-33fd7.web.app/login.html?v=firebase-only
https://conectapharma-33fd7.web.app/cadastrar-farmacias.html?v=firebase-only
```

## Executar localmente

```powershell
cd "D:\Acadêmico\Faculdade - PUC\3º Semestre - 01 2026\Introdução A Inovação Tecnológica\ConectaPharma\Frontend"
python -m http.server 5500
```

Abra:

```text
http://127.0.0.1:5500/index.html
http://127.0.0.1:5500/login.html
http://127.0.0.1:5500/plataforma.html
```

## Enviar ao GitHub

```powershell
cd "D:\Acadêmico\Faculdade - PUC\3º Semestre - 01 2026\Introdução A Inovação Tecnológica\ConectaPharma"

git status
git add .
git commit -m "Migra MVP para Firebase Firestore e OpenStreetMap sem backend obrigatorio"
git push origin main
```

Depois do push, acompanhe:

```text
https://github.com/CFSJCODE/ConectaPharma/actions
```

## Observação sobre o backend Python

A pasta `Backend/` foi mantida para histórico, testes locais e prototipagem. A aplicação online hospedada no Firebase Hosting não depende dela. Para um MVP gratuito, a regra é:

```text
Produção: Firebase Hosting + Auth + Firestore + OpenStreetMap
Local/opcional: Backend Python somente para simulações e estudos
```
