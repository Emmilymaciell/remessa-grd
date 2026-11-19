# Sanitização desta versão pública

Esta é uma cópia sanitizada de um sistema em uso real num contrato de infraestrutura. Nenhum dado do cliente está aqui; tudo o que aparece como exemplo é inventado.

## O que foi removido

- Logotipo do parceiro (terceiro).
- Arquivos de proveniência/governança interna (`PROVENANCE.md`, `OWNERSHIP.md`).

## O que foi trocado

- Nome da certificadora → `Certificadora`; nome do programa → `Programa`; parceiro → `Parceiro`.
- Rodovias reais → `RD-101`…`RD-104`.
- Numeração real das GRDs → `001/2026` (fictícia).
- Caminho local → variável `REMESSA_BASE_DIR` (padrão `./entrega`).

## O que é fictício

- Não há dado versionado; as fases 1 e 2 criam pastas e GRDs `.xlsx` a partir de uma pasta vazia.

## Como verificar

Sem suíte automatizada. Smoke:

```bat
py -m pip install -r requirements.txt
py fase1_criar_pastas_disciplinas.py
py fase2_gerar_grd_por_rodovia.py
```

Tudo acontece em `.\entrega\` (ignorada pelo Git).

Varreduras da versão pública (2026-11-19): gitleaks `dir` sem achados; busca por caminho local, e-mail, nomes do cliente e links privados sem ocorrências.
