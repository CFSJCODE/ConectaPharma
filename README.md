# ConectaPharma

Protótipo full-stack para assistência farmacêutica em rede. O frontend é estático (`Frontend/`) e o backend é uma API FastAPI (`Backend/backend_python.py`) com autenticação JWT, alertas de consumo, farmácias mapeadas, logística de entrega e base preparada para integração governamental via RNDS/DATASUS.

## Estrutura

```text
ConectaPharma/
├── Backend/
│   └── backend_python.py
├── Frontend/
│   ├── index.html
│   ├── login.html
│   └── plataforma.html
├── tests/
│   └── test_backend.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Como rodar localmente

Crie e ative um ambiente virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Copie o exemplo de ambiente, ajuste a chave local e rode a API:

```powershell
Copy-Item .env.example .env
$env:CONNECTAPHARMA_SECRET_KEY="troque-esta-chave-localmente"
cd Backend
python backend_python.py
```

A API fica em `http://127.0.0.1:8000` e a documentação interativa em `http://127.0.0.1:8000/docs`.

Para abrir o frontend, use um servidor estático na pasta `Frontend`:

```powershell
cd Frontend
python -m http.server 5500
```

Depois acesse `http://127.0.0.1:5500/index.html`.

Usuário de desenvolvimento:

- E-mail: `admin@conectapharma.com`
- Senha: `admin123`

## Testes

```powershell
python -m pytest
```

## GitHub Pages

O site estático é publicado pelo workflow `.github/workflows/pages.yml`. Ele usa a pasta `Frontend/` como raiz do GitHub Pages, então `Frontend/index.html` vira a página inicial publicada em:

```text
https://cfsjcode.github.io/ConectaPharma/
```

No GitHub, confira em `Settings > Pages` se a fonte de build está configurada como `GitHub Actions`. A publicação roda automaticamente a cada push na branch `main` quando houver alteração em `Frontend/` ou no próprio workflow.

## Integração com Meu SUS Digital / RNDS

O app Meu SUS Digital não deve ser tratado como uma API pública direta para protótipos. A integração oficial com dados e serviços digitais do SUS acontece por portfólios do Portal de Serviços DATASUS/RNDS, mediante credenciamento, CNES, homologação e certificado digital ICP-Brasil.

Este projeto foi preparado com endpoints seguros para essa integração:

- `GET /api/v1/integracoes/rnds/status`
- `POST /api/v1/integracoes/rnds/dispensacao`

Por padrão, esses endpoints rodam em `dry-run`: montam o documento localmente e não enviam nada ao DATASUS. Para envio real, configure as variáveis `CONNECTAPHARMA_RNDS_*` no `.env` com as credenciais e URLs aprovadas no Portal de Serviços DATASUS.

Mais detalhes estão em `docs/rnds.md`.

## Preparar para GitHub

Este repositório já inclui `.gitignore` para evitar envio de ambiente virtual, cache, logs, `.env` e certificados. Para publicar:

```powershell
git init
git add .
git commit -m "Preparar ConectaPharma para GitHub"
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/SEU-REPOSITORIO.git
git push -u origin main
```

Não envie `.env`, certificados digitais, chaves privadas ou dados reais de pacientes.
