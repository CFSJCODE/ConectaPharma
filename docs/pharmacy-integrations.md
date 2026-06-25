# ConectaPharma — Integração com farmácias, APIs oficiais e webhooks

## Objetivo

Implementar uma camada de integração para farmácias e redes parceiras sem alterar a essência visual da plataforma. O ConectaPharma permanece como plataforma de busca, disponibilidade informativa, mapa, alertas e encaminhamento para canais oficiais.

## Posição operacional

O MVP não deve executar checkout próprio, pagamento, dispensação, avaliação de receita ou venda direta de medicamento. A farmácia responsável continua sendo o canal oficial de venda, orientação farmacêutica e cumprimento regulatório.

## Arquitetura

```txt
Farmácia / ERP / e-commerce
        ↓
API oficial, webhook assinado ou CSV/JSON autorizado
        ↓
Integration Gateway
        ↓
Normalização, validação, idempotência e logs
        ↓
Firestore
        ↓
Frontend ConectaPharma
```

## Coleções Firestore

### `pharmacy_inventory`

Armazena disponibilidade pública e normalizada.

```json
{
  "pharmacyId": "demo_droga_raia_bh",
  "medicineId": "demo_losartana_50mg",
  "externalSku": "789000000001",
  "ean": "789000000001",
  "commercialName": "Losartana Potássica 50mg",
  "activeIngredient": "Losartana Potássica",
  "concentration": "50mg",
  "pharmaceuticalForm": "Comprimido",
  "availabilityStatus": "available",
  "quantityInternal": 12,
  "quantityPublic": "available",
  "price": 19.9,
  "officialProductUrl": "https://canal-oficial-da-farmacia.example/produto",
  "source": "webhook",
  "integrationProvider": "rd_marketplace_demo",
  "lastSyncAt": "2026-06-24T20:10:00-03:00"
}
```

### `integration_logs`

Armazena rastreabilidade técnica.

```json
{
  "partnerId": "rd_marketplace_demo",
  "pharmacyId": "demo_droga_raia_bh",
  "eventType": "stock.updated",
  "level": "info",
  "message": "Evento processado com sucesso.",
  "source": "webhook"
}
```

### `webhook_events`

Armazena idempotência e auditoria de eventos recebidos.

```json
{
  "eventId": "evt_20260624_000001",
  "partnerId": "rd_marketplace_demo",
  "pharmacyId": "demo_droga_raia_bh",
  "eventType": "stock.updated",
  "status": "processed",
  "payloadHash": "sha256-do-payload"
}
```

## Regras de acesso implementadas

### Usuário comum

Pode:

- consultar `pharmacy_inventory` publicamente;
- visualizar disponibilidade pública;
- acessar links oficiais.

Não pode:

- criar inventário;
- alterar estoque;
- visualizar logs técnicos;
- criar eventos de webhook.

### Administrador

A conta `claudiofranciscojunior2006@gmail.com` pode:

- criar, atualizar e remover inventário normalizado;
- criar logs técnicos;
- criar eventos de webhook simulados;
- visualizar logs e eventos.

### Farmácia parceira

O suporte a farmácia parceira por `custom claims` deve ser ativado no próximo ciclo com claims do tipo:

```json
{
  "role": "pharmacy",
  "pharmacyId": "pharmacy_001"
}
```

Neste branch, a regra implantável mantém a política atual do projeto: escrita sensível restrita ao administrador por e-mail.

## Página visual adicionada

Arquivo:

```txt
Frontend/integracoes.html
```

A página apresenta:

- matriz visual de redes e plataformas;
- arquitetura de API/webhook/CSV;
- regras de acesso por perfil;
- console visual do endpoint de webhook;
- simulação administrativa de evento `stock.updated`;
- leitura de inventário integrado e logs técnicos.

## Gateway backend adicionado

Arquivo:

```txt
Backend/integration_gateway.py
```

Endpoint principal:

```txt
POST /api/v1/integrations/webhooks/{partner_id}/stock
```

Cabeçalhos esperados:

```txt
x-conectapharma-signature: sha256=<assinatura_hmac>
x-conectapharma-timestamp: <unix_timestamp>
```

Payload esperado:

```json
{
  "eventId": "evt_20260624_000001",
  "eventType": "stock.updated",
  "partnerId": "rd_marketplace_demo",
  "pharmacyId": "demo_droga_raia_bh",
  "externalSku": "789000000001",
  "ean": "789000000001",
  "commercialName": "Losartana Potássica 50mg",
  "activeIngredient": "Losartana Potássica",
  "concentration": "50mg",
  "pharmaceuticalForm": "Comprimido",
  "availabilityStatus": "available",
  "quantity": 12,
  "price": 19.9,
  "officialProductUrl": "https://canal-oficial-da-farmacia.example/produto",
  "updatedAt": "2026-06-24T20:10:00-03:00"
}
```

## Execução local do gateway

O módulo foi criado como roteador FastAPI complementar. Para ativá-lo no backend principal:

```python
from integration_gateway import router as integration_router

app.include_router(integration_router)
```

Configure o segredo HMAC no ambiente:

```bash
CONNECTAPHARMA_WEBHOOK_SECRET="troque-este-segredo"
CONNECTAPHARMA_WEBHOOK_MAX_SKEW_SECONDS=300
```

## Estratégia por rede

| Rede/plataforma | Modo recomendado | Observação |
|---|---|---|
| Drogaria Araujo | API privada, webhook autorizado ou CSV | Requer parceria formal. |
| Droga Raia / Drogasil | Marketplace, API oficial ou integradora | Requer credenciais e escopos autorizados. |
| Pacheco / Drogaria São Paulo | API privada, ERP/integrador ou CSV | Requer parceria B2B. |
| Farmácias locais | Painel manual, CSV/JSON e logs | Melhor caminho para validação inicial. |
| VTEX / Nuvemshop | Adaptador por plataforma | Depende de app key, token e escopos. |

## Próximas etapas recomendadas

1. Migrar a escrita real de webhooks para Cloud Functions ou backend FastAPI com Admin SDK.
2. Implementar idempotência real por `eventId` antes de atualizar `pharmacy_inventory`.
3. Criar `integration_credentials` somente no backend/Secret Manager, nunca acessível por frontend.
4. Ativar `custom claims` para perfis `admin` e `pharmacy`.
5. Adicionar importador CSV/JSON com validação de schema.
6. Criar adaptadores específicos: `VtexAdapter`, `NuvemshopAdapter`, `RdMarketplaceAdapter`, `DpspPrivateAdapter`, `AraujoPrivateAdapter`.
