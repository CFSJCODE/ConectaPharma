# ConectaPharma

**Saúde, tecnologia e solidariedade conectando vidas.**

O **ConectaPharma** é uma plataforma web de apoio ao acesso a medicamentos, farmácias cadastradas e serviços públicos de saúde. O MVP foi estruturado para pacientes, familiares, cuidadores, comunidade e instituições parceiras, com foco em consulta simples, redução de deslocamentos desnecessários e organização do cuidado.

A versão atual é uma aplicação frontend hospedável no **Firebase Hosting**, integrada ao **Firebase Authentication**, **Cloud Firestore** e consultas públicas via **OpenStreetMap/Overpass**.

---

## Estado atual da implementação

A aplicação foi reorganizada para abandonar o modelo institucional **single page**. A página inicial passou a atuar como porta de entrada objetiva, enquanto o conteúdo público foi separado em páginas independentes.

Também foram aplicadas correções de autenticação, autorização, carregamento da plataforma, menu, cadastro de medicamentos e restrição de cadastro manual de farmácias.

### Principais entregas recentes

- Separação da apresentação pública em múltiplas páginas HTML.
- Padronização do menu público com todas as páginas principais.
- Correção do menu da área autenticada para manter os itens em uma única linha.
- Correção do botão **Sair**, que podia ficar escondido/cortado no cabeçalho.
- Correção dos estados de carregamento infinito em:
  - `Verificando seu acesso...`
  - `Carregando alertas...`
  - `Carregando catálogo...`
- Otimização da validação de sessão do Firebase Auth.
- Carregamento paralelo de alertas, farmácias e medicamentos.
- Fallback visual para falhas ou lentidão do Firebase/Firestore.
- Liberação do cadastro de medicamentos para qualquer conta autenticada.
- Restrição do cadastro manual de farmácias exclusivamente à conta administrativa.
- Ocultação real dos botões administrativos para usuários comuns.
- Atualização textual para linguagem corporativa e direta ao usuário final.
- Integração de busca por farmácias e serviços públicos próximos usando OpenStreetMap/Overpass.

---

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

A versão publicada **não depende** de FastAPI, Cloud Functions, Cloud Run, Google Places, Google Maps API, App Hosting, SQL Connect ou Data Connect.

A pasta `Backend/` permanece no repositório apenas como referência local, histórico técnico e base de prototipagem.

---

## Stack técnica

- **HTML5**
- **CSS3**
- **JavaScript modular**
- **Firebase Hosting**
- **Firebase Authentication**
- **Cloud Firestore**
- **Firestore Security Rules**
- **OpenStreetMap/Overpass API**
- **Backend Python opcional/local**

---

## Estrutura de páginas

### Área pública

```text
Frontend/index.html
Frontend/como-funciona.html
Frontend/sobre.html
Frontend/seguranca.html
Frontend/parceiros.html
Frontend/jornadas.html
Frontend/impacto-social.html
Frontend/login.html
```

Descrição das páginas:

| Página | Finalidade |
|---|---|
| `index.html` | Entrada institucional, proposta de valor e atalhos para a navegação pública. |
| `como-funciona.html` | Explicação do fluxo de consulta, organização e uso da plataforma. |
| `sobre.html` | Missão, visão, valores e posicionamento do MVP. |
| `seguranca.html` | Privacidade, autenticação, localização opcional e regras de acesso. |
| `parceiros.html` | Rede de parceiros institucionais, públicos, privados e comunitários. |
| `jornadas.html` | Pessoas atendidas, personas e cenários de uso. |
| `impacto-social.html` | Benefícios esperados e impacto social do projeto. |
| `login.html` | Entrada com autenticação por conta Google ou e-mail/senha. |

### Área autenticada

```text
Frontend/plataforma.html
Frontend/cadastrar-farmacias.html
```

| Página | Finalidade |
|---|---|
| `plataforma.html` | Área interna para consulta de farmácias, catálogo de medicamentos, cadastro de medicamentos, alertas e buscas por proximidade. |
| `cadastrar-farmacias.html` | Cadastro manual de farmácias, restrito à conta administrativa. |

---

## Regras de acesso

A autenticação utiliza Firebase Authentication.

Conta administrativa única:

```text
claudiofranciscojunior2006@gmail.com
```

### Matriz de permissões

| Recurso | Conta comum autenticada | Conta administrativa |
|---|---:|---:|
| Entrar na plataforma | Sim | Sim |
| Consultar farmácias cadastradas | Sim | Sim |
| Consultar medicamentos | Sim | Sim |
| Cadastrar medicamentos | Sim | Sim |
| Consultar farmácias próximas via localização | Sim | Sim |
| Consultar UBSs, postos e UPAs próximos | Sim | Sim |
| Ver botão de cadastro manual de farmácias | Não | Sim |
| Acessar `cadastrar-farmacias.html` | Não | Sim |
| Cadastrar farmácias manualmente | Não | Sim |
| Alterar/excluir dados administrativos | Não | Sim |

### Regra crítica de negócio

O cadastro de medicamentos **não** é administrativo. Ele deve permanecer disponível para qualquer usuário autenticado.

O cadastro manual de farmácias é a função administrativa restrita.

A autorização administrativa não deve depender de `localStorage`, `sessionStorage`, documentos antigos em `users/{uid}` ou campo local `role`. A referência operacional da interface é o e-mail autenticado.

---

## Firestore

### Coleção `users`

Documento com ID igual ao UID do Firebase Auth:

```json
{
  "uid": "UID_DO_FIREBASE_AUTH",
  "name": "Nome do usuário",
  "email": "usuario@exemplo.com",
  "role": "USER",
  "provider": "google",
  "active": true,
  "createdAt": "serverTimestamp",
  "lastLoginAt": "serverTimestamp",
  "updatedAt": "serverTimestamp"
}
```

### Coleção `farmacias`

```json
{
  "nome": "Farmácia Central",
  "name": "Farmácia Central",
  "endereco": "Av. Afonso Pena, 1000 - Centro, Belo Horizonte/MG",
  "address": "Av. Afonso Pena, 1000 - Centro, Belo Horizonte/MG",
  "bairro": "Centro",
  "cidade": "Belo Horizonte",
  "estado": "MG",
  "telefone": "(31) 99999-9999",
  "phone": "(31) 99999-9999",
  "whatsapp": "5531999999999",
  "email": "contato@farmacia.com.br",
  "website": "https://www.farmacia.com.br",
  "horario_funcionamento": "Segunda a sexta, 08:00 às 18:00",
  "opening_hours_label": "Segunda a sexta, 08:00 às 18:00",
  "latitude": -19.9191,
  "longitude": -43.9386,
  "openstreetmap_url": "https://www.openstreetmap.org/?mlat=-19.9191&mlon=-43.9386#map=17/-19.9191/-43.9386",
  "maps_url": "https://www.openstreetmap.org/?mlat=-19.9191&mlon=-43.9386#map=17/-19.9191/-43.9386",
  "ativo": true,
  "disponibilidade_farmaco": true,
  "origem": "manual_firestore",
  "source": "manual_firestore",
  "createdBy": "UID_DO_ADMIN",
  "updatedBy": "UID_DO_ADMIN",
  "createdAt": "serverTimestamp",
  "updatedAt": "serverTimestamp"
}
```

### Coleção `medications`

```json
{
  "nome": "Losartana 50mg",
  "categoria": "Anti-hipertensivo",
  "descricao": "Medicamento de uso contínuo.",
  "dose_diaria_comprimidos": 1,
  "stock": 20,
  "requires_prescription": true,
  "active": true,
  "createdBy": "UID_DO_USUARIO",
  "updatedBy": "UID_DO_USUARIO",
  "createdAt": "serverTimestamp",
  "updatedAt": "serverTimestamp"
}
```

### Coleção `medicine_alerts`

Usada para alertas e acompanhamento. A leitura deve ser limitada ao próprio usuário ou ao administrador, conforme as regras do Firestore.

---

## Regras de segurança

As regras estão em:

```text
Firebase/firestore.rules
```

Resumo das permissões esperadas:

- `users/{uid}`: cada usuário lê seu próprio documento; administrador pode ler usuários.
- `farmacias`: leitura pública; criação, edição e exclusão somente pela conta `claudiofranciscojunior2006@gmail.com`.
- `medications`: leitura pública; criação por contas autenticadas; atualização/exclusão conforme regra administrativa definida no Firestore.
- `medicine_alerts`: leitura pelo próprio usuário ou administrador; gestão por administrador.
- formulários e logs: criação conforme o caso; leitura administrativa.

---

## Comportamento da área autenticada

A página `Frontend/plataforma.html` possui:

- validação de sessão com Firebase Auth;
- identificação do usuário autenticado;
- controle visual de elementos administrativos;
- carregamento paralelo de dados;
- timeout para impedir carregamento infinito;
- renderização de estados vazios quando não houver dados;
- formulário de cadastro de medicamentos liberado para contas autenticadas;
- botão de cadastro manual de farmácias visível somente para administrador;
- menu superior em linha única com botão **Sair** visível.

Estados corrigidos:

```text
Verificando seu acesso...
Carregando alertas...
Carregando catálogo...
```

Esses estados agora possuem fallback e não devem permanecer indefinidamente na interface.

---

## Menu e responsividade

O cabeçalho da área autenticada foi ajustado para manter os itens principais em uma única linha:

```text
Início | Como funciona | Sobre | Segurança | Parceiros | Pessoas atendidas | Impacto social | Sair
```

Correções aplicadas:

- `header` com layout em grade para separar identidade visual e navegação.
- menu com `flex-wrap: nowrap`.
- itens com largura flexível controlada.
- botão **Sair** com largura mínima e estilo próprio.
- redução responsiva de fonte, espaçamento e padding.
- rolagem horizontal apenas em telas estreitas, preservando uma única linha.

---

## Consulta por proximidade

A plataforma pode consultar:

- farmácias próximas;
- UBSs;
- postos de saúde;
- centros de saúde;
- UPAs.

A localização é solicitada somente com consentimento do usuário. A consulta usa dados públicos do OpenStreetMap/Overpass.

---

## Executar localmente

Na pasta do frontend:

```powershell
cd "D:\Acadêmico\Faculdade - PUC\3º Semestre - 01 2026\Introdução A Inovação Tecnológica\ConectaPharma\Frontend"
python -m http.server 5500
```

Acesse:

```text
http://127.0.0.1:5500/index.html
http://127.0.0.1:5500/login.html
http://127.0.0.1:5500/plataforma.html
```

Páginas públicas disponíveis localmente:

```text
http://127.0.0.1:5500/como-funciona.html
http://127.0.0.1:5500/sobre.html
http://127.0.0.1:5500/seguranca.html
http://127.0.0.1:5500/parceiros.html
http://127.0.0.1:5500/jornadas.html
http://127.0.0.1:5500/impacto-social.html
```

---

## Deploy no Firebase

Na raiz do projeto:

```powershell
firebase use conectapharma-33fd7
firebase deploy --only hosting
```

Quando alterar regras do Firestore:

```powershell
firebase deploy --only firestore:rules
```

Deploy completo:

```powershell
firebase deploy --only hosting,firestore:rules
```

Após publicar, teste com cache busting:

```text
https://conectapharma-33fd7.web.app/index.html?v=latest
https://conectapharma-33fd7.web.app/login.html?v=latest
https://conectapharma-33fd7.web.app/plataforma.html?v=latest
https://conectapharma-33fd7.web.app/cadastrar-farmacias.html?v=latest
```

---

## Checklist de validação

### Conta comum

- Login funciona.
- Área interna abre sem travar em carregamento.
- Menu aparece em uma única linha.
- Botão **Sair** aparece corretamente.
- Consulta de farmácias funciona ou exibe estado vazio.
- Catálogo de medicamentos funciona ou exibe estado vazio.
- Cadastro de medicamentos fica disponível.
- Botão **Cadastrar farmácias manualmente** não aparece.
- Acesso direto a `cadastrar-farmacias.html` deve ser bloqueado.

### Conta administrativa

- Login funciona com `claudiofranciscojunior2006@gmail.com`.
- Indicador de perfil responsável aparece.
- Botão **Cadastrar farmácias manualmente** aparece.
- Página `cadastrar-farmacias.html` é acessível.
- Cadastro manual de farmácias funciona conforme regras do Firestore.
- Cadastro de medicamentos continua disponível.

---

## Comandos Git úteis

```powershell
git status
git add .
git commit -m "fix(frontend): ajusta menu e documenta versao atual"
git push origin main
```

---

## Observação sobre o backend Python

A pasta `Backend/` foi mantida para histórico, testes locais e prototipagem. A aplicação online hospedada no Firebase Hosting não depende dela.

```text
Produção: Firebase Hosting + Auth + Firestore + OpenStreetMap
Local/opcional: Backend Python somente para simulações e estudos
```
