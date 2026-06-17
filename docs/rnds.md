# Integração RNDS/DATASUS

## É possível conectar ao Meu SUS Digital?

Não como uma API pública simples do aplicativo. O caminho oficial para sistemas de saúde é a RNDS, acessada por portfólios do Portal de Serviços DATASUS. O Meu SUS Digital é a experiência do cidadão; a troca sistêmica de dados acontece via serviços governamentais como RNDS, CNS, BNAFAR/SOA-Bnafar e outros portfólios habilitados.

Para uma solução farmacêutica como o ConectaPharma, o portfólio mais aderente deve ser confirmado no Portal de Serviços DATASUS. A FAQ pública da RNDS lista `SOA-Bnafar (Integração à Base Nacional de Dados de Ações e Serviços da Assistência Farmacêutica)` entre os portfólios disponíveis.

## Requisitos oficiais esperados

- CNES válido do estabelecimento.
- Solicitação de credencial no Portal de Serviços DATASUS.
- Aprovação para ambiente de homologação.
- Testes e evidências para posterior liberação em produção.
- Certificado digital ICP-Brasil.
- Autenticação mTLS/Two-way SSL para obter `access_token`.
- Uso do token nas chamadas ao EHR Services/RNDS.
- Adequação LGPD, autorização, rastreabilidade e mínimo necessário de dados.

## Como o código ficou preparado

O backend possui um adaptador em `Backend/backend_python.py`:

- `GET /api/v1/integracoes/rnds/status`: mostra se a integração está em `dry-run` ou pronta para envio real.
- `POST /api/v1/integracoes/rnds/dispensacao`: monta um Bundle FHIR R4 preliminar de dispensação farmacêutica.

Quando `CONNECTAPHARMA_RNDS_ENABLED=false`, nenhuma chamada externa é feita. Isso é o comportamento correto para desenvolvimento, apresentação acadêmica e publicação no GitHub.

Quando `CONNECTAPHARMA_RNDS_ENABLED=true`, o backend espera as variáveis:

```env
CONNECTAPHARMA_RNDS_AUTH_URL=
CONNECTAPHARMA_RNDS_SERVICES_URL=
CONNECTAPHARMA_RNDS_DOCUMENT_ENDPOINT=/fhir/r4/Bundle
CONNECTAPHARMA_RNDS_CLIENT_CERT_PATH=
CONNECTAPHARMA_RNDS_CLIENT_KEY_PATH=
CONNECTAPHARMA_ESTABELECIMENTO_CNES=
```

## Observação sobre certificado

O código usa `httpx` com certificado de cliente. Se o credenciamento entregar um arquivo `.pfx/.p12`, pode ser necessário converter para PEM antes de usar localmente. Guarde certificados e chaves fora do Git; `.gitignore` já bloqueia `certs/`, `*.pfx`, `*.p12`, `*.pem`, `*.key` e `*.crt`.

## Próximo passo real

Com a credencial oficial em mãos, valide o modelo exato exigido pelo portfólio aprovado. O Bundle atual é uma estrutura técnica inicial para homologação e deve ser ajustado ao manual técnico vigente do serviço liberado ao integrador.
