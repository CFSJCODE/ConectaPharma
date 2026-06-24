# Farmácias abertas próximas — OpenStreetMap/Overpass (fonte principal gratuita)

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
Backend consulta OpenStreetMap/Overpass (fonte principal gratuita)
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

## Otimizações de desempenho

A integração com Overpass foi ajustada para reduzir latência e proteger o serviço público contra requisições redundantes:

- `httpx.AsyncClient` é reutilizado pelo backend para manter conexões HTTP abertas.
- O cache bruto do Overpass usa `CONNECTAPHARMA_OVERPASS_CACHE_TTL_SECONDS`.
- O cache de resposta final usa `CONNECTAPHARMA_OVERPASS_RESPONSE_CACHE_TTL_SECONDS`.
- Requisições simultâneas com a mesma região e raio usam bloqueio assíncrono por chave, evitando efeito de rajada.
- O backend limita e ordena os resultados por proximidade com seleção parcial, não ordenação completa desnecessária.
- O frontend possui cache temporário de sessão e apenas renderiza os dados retornados pelo backend.

Esses ajustes mantêm o uso gratuito e respeitoso do OpenStreetMap/Overpass (fonte principal gratuita), sem Cloud Functions e sem Cloud SQL.


## Correção de `Failed to fetch` em hospedagem estática

Quando o frontend roda em `https://conectapharma-33fd7.web.app`, chamadas para `http://localhost:8000` não funcionam porque o backend local não está disponível para o navegador do usuário. Para corrigir isso, a plataforma agora usa a seguinte ordem:

1. Se `window.CONNECTAPHARMA_API_BASE_URL` estiver configurado ou se o frontend estiver em `localhost`, consulta o backend FastAPI.
2. Se o backend estiver indisponível, consulta OpenStreetMap/Overpass (fonte principal gratuita) diretamente como fonte principal gratuita.
3. Exibe link de rota pelo **OpenStreetMap** sem usar APIs pagas.

Para usar um backend público, publique o FastAPI em um provedor compatível e configure antes do carregamento da plataforma:

```html
<script>
  window.CONNECTAPHARMA_API_BASE_URL = 'https://sua-api-publica.example.com/api/v1';
</script>
```
