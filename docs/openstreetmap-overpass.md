# OpenStreetMap / Overpass no ConectaPharma

Esta versão usa OpenStreetMap/Overpass como fonte gratuita para consultas públicas de proximidade.

## Fluxo implementado

```text
Usuário clica em usar localização
↓
Navegador solicita permissão de geolocalização
↓
Frontend envia consulta ao Overpass API
↓
Frontend normaliza endereço, telefone, site, horário e coordenadas
↓
Frontend calcula distância por Haversine
↓
Frontend filtra farmácias abertas, UBSs, postos de saúde e UPAs
↓
Frontend renderiza os resultados
```

## Farmácias próximas

A consulta considera tags como:

```text
amenity=pharmacy
healthcare=pharmacy
shop=chemist
```

Quando disponíveis, são exibidos:

- nome;
- endereço;
- telefone;
- WhatsApp;
- site;
- e-mail;
- bandeira/rede;
- operador;
- horário de funcionamento;
- distância;
- link do OpenStreetMap.

## Estabelecimentos de saúde

A busca de saúde é limitada a:

- UBS;
- postos de saúde;
- centros de saúde;
- UPAs;
- pronto atendimento;
- serviços públicos similares.

São excluídos do fluxo de saúde genérico:

- farmácias;
- laboratórios;
- dentistas;
- veterinários;
- óticas;
- consultórios privados genéricos sem indicação pública/SUS.

## Limitações

O OpenStreetMap depende de dados cadastrados pela comunidade. Alguns locais podem não possuir horário, telefone ou endereço completo. Quando `opening_hours` está ausente, o sistema mostra o horário como não informado.

## Por que não usar Google Places nesta versão

Google Places/Google Maps Platform exige billing habilitado e pode gerar cobrança por uso. Como o requisito do MVP é manter apenas soluções gratuitas e sem risco de cobrança, a fonte de dados externa foi padronizada em OpenStreetMap/Overpass.
