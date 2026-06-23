# Farmácias abertas próximas — OpenStreetMap/Overpass

## Objetivo

Implementar a busca de farmácias abertas próximas usando somente recursos gratuitos, mantendo todo o processamento no backend.

## Arquitetura

```text
Frontend
↓
Solicita permissão de localização ao navegador
↓
Envia latitude/longitude ao FastAPI
↓
Backend consulta OpenStreetMap/Overpass
↓
Backend aplica cache em memória
↓
Backend calcula distância por Haversine
↓
Backend interpreta `opening_hours`
↓
Backend filtra abertas agora
↓
Backend ordena por proximidade
↓
Frontend renderiza JSON final
```

## Endpoint

```text
GET /api/v1/farmacias/proximas
```

Parâmetros:

| Parâmetro | Tipo | Padrão | Descrição |
|---|---:|---:|---|
| `lat` | float | obrigatório | Latitude do usuário |
| `lng` | float | obrigatório | Longitude do usuário |
| `radius_km` | float | `10` | Raio de busca entre 0 e 50 km |
| `open_now` | bool | `true` | Retornar apenas abertas agora |
| `limit` | int | `10` | Máximo de resultados entre 1 e 50 |
| `source` | string | `overpass` | `overpass` ou `mock` |

## Exemplo

```text
/api/v1/farmacias/proximas?lat=-19.9191&lng=-43.9386&radius_km=10&open_now=true&limit=10&source=overpass
```

## Política de processamento

O frontend não calcula distância, não filtra horário e não ordena resultados. A única operação local obrigatória é solicitar a permissão de localização ao usuário, pois essa autorização pertence ao navegador.

## Cache

O backend mantém cache em memória por coordenada arredondada e raio de busca. O TTL é configurado por:

```env
CONNECTAPHARMA_OVERPASS_CACHE_TTL_SECONDS=900
```

## Limitações

O OpenStreetMap depende da qualidade dos dados cadastrados pela comunidade. Alguns estabelecimentos podem não possuir `opening_hours`, telefone ou endereço completo. Quando o horário é desconhecido, o backend não classifica a farmácia como aberta em buscas com `open_now=true`.
