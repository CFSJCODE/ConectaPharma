# Integração Google Maps Platform / Places API

O ConectaPharma possui integração opcional com **Google Places API (New)** para localizar farmácias próximas com dados mais completos e confiáveis, como endereço formatado, telefone, avaliação, número de avaliações, status operacional, URL do Google Maps e horário de funcionamento quando disponível.

## Arquitetura

```text
Frontend
  → solicita localização ao navegador
  → envia latitude/longitude ao backend
Backend FastAPI
  → consulta Google Places API quando configurada
  → calcula distância
  → filtra abertura atual
  → ordena por proximidade
  → retorna JSON normalizado ao frontend
Frontend
  → apenas renderiza os dados
```

A chave do Google Maps **não deve ser colocada no frontend**. Ela deve existir somente em variável de ambiente do backend.

## Requisitos

1. Criar ou usar um projeto no Google Cloud.
2. Habilitar billing no projeto.
3. Habilitar **Places API (New)**.
4. Criar uma API key.
5. Restringir a API key para uso apenas na **Places API**.
6. Definir a chave no backend.

## Variáveis de ambiente

Adicione ao `.env` do backend:

```env
CONNECTAPHARMA_GOOGLE_PLACES_ENABLED=true
CONNECTAPHARMA_GOOGLE_MAPS_API_KEY=SUA_CHAVE_GOOGLE_MAPS
CONNECTAPHARMA_GOOGLE_PLACES_NEARBY_URL=https://places.googleapis.com/v1/places:searchNearby
CONNECTAPHARMA_GOOGLE_PLACES_TEXT_URL=https://places.googleapis.com/v1/places:searchText
CONNECTAPHARMA_GOOGLE_PLACES_TIMEOUT_SECONDS=10
CONNECTAPHARMA_GOOGLE_PLACES_CACHE_TTL_SECONDS=900
CONNECTAPHARMA_GOOGLE_PLACES_RESPONSE_CACHE_TTL_SECONDS=60
CONNECTAPHARMA_GOOGLE_PLACES_MAX_RESULT_COUNT=20
CONNECTAPHARMA_GOOGLE_PLACES_LANGUAGE_CODE=pt-BR
CONNECTAPHARMA_GOOGLE_PLACES_REGION_CODE=BR
```

## Endpoint de farmácias próximas

```text
GET /api/v1/farmacias/proximas
```

Exemplo:

```text
/api/v1/farmacias/proximas?lat=-19.9191&lng=-43.9386&radius_km=10&open_now=true&limit=10&source=google
```

Modos aceitos:

```text
source=auto      tenta Google Places e usa OpenStreetMap como fallback
source=google    prioriza Google Places; usa fallback se a chave não existir ou a API falhar
source=overpass  usa OpenStreetMap/Overpass
source=mock      usa base local de demonstração
```

## Endpoint de estabelecimentos de saúde

```text
GET /api/v1/estabelecimentos-saude/proximos
```

Exemplo:

```text
/api/v1/estabelecimentos-saude/proximos?lat=-19.9191&lng=-43.9386&radius_km=5&kind=all&open_now=false&limit=12&source=auto
```

Para estabelecimentos de saúde, o backend usa filtro semântico para priorizar UBSs, UPAs, postos de saúde, centros de saúde e pronto atendimento, evitando farmácias, laboratórios e consultórios privados genéricos.

## Fallback

Se a chave do Google não estiver configurada ou a Places API falhar, o backend usa OpenStreetMap/Overpass como fallback gratuito. Isso preserva a demonstração do MVP sem expor credenciais e sem quebrar a interface.

## Segurança

Nunca versionar:

```text
.env
GOOGLE_MAPS_API_KEY
CONNECTAPHARMA_GOOGLE_MAPS_API_KEY
service-account.json
firebase-adminsdk*.json
credentials.json
```
