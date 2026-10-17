# Almanaque Político do Amazonas

Site estático (GitHub Pages, arquivo único `index.html` + `data/`) que junta, por pessoa, por partido e por município, os
levantamentos feitos só com dados públicos oficiais. No ar em https://leonzordhue.github.io/politicosAM/.

| Repositório | Conteúdo | Agente |
|---|---|---|
| [dossieprefeitosAM](https://github.com/leonzordhue/dossieprefeitosAM) | prefeitos, vices e vereadores (TSE 2000–2024), finanças municipais (FINBRA/SICONFI), IBGE, IDEB, SIOPE, SIOPS, IDHM, emendas recebidas, bens, TCE-AM, TCU, Câmaras (SAPL e Diário Oficial), fotos | Proton |
| [deputadosfederais](https://github.com/leonzordhue/deputadosfederais) | deputados federais do AM desde 1999 (proposições, cota, emendas) | Claude |
| [senadorAM](https://github.com/leonzordhue/senadorAM) | senadores do AM (matérias, CEAPS, emendas) | Claude |
| estaduaisAM (em preparação) | deputados estaduais (ALEAM) e governadores: mandatos, proposições, CEAP, emendas estaduais (SEFAZ-AM), bens | Claude |
| [leismunicipais](https://github.com/leonzordhue/leismunicipais) | leis dos 62 municípios em Markdown (Diário Oficial dos Municípios e SAPL das Câmaras) | Claude e Nexus |

A chave comum é o `pessoa_id` (sha1 do título de eleitor, 10 caracteres), definido no contrato `projetos/pesquisa/PLATAFORMA-POLITICOS-AM.md`.
Quem foi vereador, prefeito e depois deputado aparece numa ficha só. Título e CPF não são publicados.

## Como atualizar

Os repositórios ficam lado a lado em `projetos/pesquisa/`. Depois que algum deles gerar dados novos:

```
python -I scripts/montar.py
```

O script só lê o que os repositórios publicaram (CSV do contrato, cabeçalhos YAML das leis), copia as fotos, gera `data/` e grava
`INTEGRIDADE.md` (checagens da junção, arquivos que faltam e alertas). Nada é coletado aqui. Leva uns 5 minutos (lê ~20 mil leis).

Arquivos de apoio em `scripts/`: `am_municipios.geojson` (malha do IBGE, API v3), `am_rodovias.geojson` (Sistema Rodoviário
Estadual, SEINFRA-AM, via atlas-amazonas) e `am_regioes.json` (regiões imediata/intermediária e área, IBGE 2022).

## Telas

- **Início:** números gerais, mapa dos 62 municípios (partido do prefeito, IDHM, PIB por habitante, emendas por habitante,
  densidade, região; camada de rodovias estaduais) e quem governa o AM hoje.
- **Explorar:** as 53 mil candidaturas desde 1994 com filtros por nome, cargo, partido, município, região, ano, resultado e gênero.
- **Governo hoje:** governador, senadores, deputados federais e estaduais, prefeitos e vereadores em exercício; composição partidária.
- **Partidos:** candidaturas e eleitos por cargo e eleição, quem está no cargo hoje, trocas de partido entre eleições.
- **Gastos:** cota parlamentar (Câmara, Senado, ALEAM) por ano, por parlamentar e por categoria; emendas pagas por parlamentar.
- **Leis:** busca nas leis municipais por texto da ementa, município, assunto (classificação automática), tipo e ano.
- **Pessoa:** linha do tempo dos mandatos, candidaturas, patrimônio, atuação em cada Casa, proposições, cota, emendas,
  Câmara Municipal (projetos e votos), TCE-AM, TCU, Justiça Eleitoral.
- **Município:** quem governa hoje, região e área, prefeitos desde 2001, eleições, Câmara, leis, emendas federais e estaduais,
  finanças, pessoal/RCL, SIOPE, SIOPS, IDHM, IDEB, atos e interinos.
- **Estudos:** reeleição, mulheres eleitas, partidos, LRF, IDEB por mandato, emendas por habitante, patrimônio, leis por assunto,
  cota média por Casa, troca de partido.

## Visual

Identidade SEINFRA (azul `#002D72`, dourado `#F5A623`, fonte Outfit) sobre a linguagem *corporate-trust* (superfícies claras,
um acento, tabelas como peça central, sem enfeite). Gráficos pelo método *dataviz*: paleta categórica em ordem fixa, no mapa
no máximo 3 cores + cinza, escala sequencial de um tom, modo escuro próprio.
