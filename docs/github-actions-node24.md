# GitHub Actions com Node 24

Este projeto usa Firebase Hosting como canal oficial de publicação. Os workflows foram atualizados para evitar a ação legada `FirebaseExtended/action-hosting-deploy@v0`, que ainda pode gerar avisos de depreciação do Node 20.

## Workflows ativos

- `.github/workflows/firebase-hosting-merge.yml`
  - Executa em push para `main`.
  - Publica `hosting` e `firestore:rules`.
  - Usa `actions/checkout@v5`, `actions/setup-node@v5` e `google-github-actions/auth@v3`.

- `.github/workflows/firebase-hosting-pull-request.yml`
  - Executa em pull requests internas.
  - Publica canal temporário de preview do Firebase Hosting.

- `.github/workflows/pages.yml`
  - Fica manual-only para evitar deploy automático no GitHub Pages.
  - O ambiente oficial do projeto é Firebase Hosting.

## Secret utilizado

O workflow reaproveita o secret já criado pelo Firebase CLI:

```txt
FIREBASE_SERVICE_ACCOUNT_CONECTAPHARMA_33FD7
```

Esse secret deve conter o JSON da service account com permissão de deploy no projeto `conectapharma-33fd7`.

## Commit recomendado

```txt
ci(actions): atualiza workflows para Node 24
```
