# Políticos do Amazonas: plataforma única

Site estático (GitHub Pages) que junta, por pessoa e por município, os levantamentos feitos só com dados públicos oficiais:

| Repositório | Conteúdo | Agente |
|---|---|---|
| [dossieprefeitosAM](https://github.com/leonzordhue/dossieprefeitosAM) | prefeitos, vices e vereadores (TSE 2000–2024), finanças municipais (FINBRA/SICONFI), IBGE, IDEB, emendas recebidas, bens, fotos | Proton |
| [deputadosfederais](https://github.com/leonzordhue/deputadosfederais) | deputados federais do AM desde 1999 | Claude |
| [senadorAM](https://github.com/leonzordhue/senadorAM) | senadores do AM | Claude |

A chave comum é o `pessoa_id` (sha1 do título de eleitor, 10 caracteres), definido no contrato `projetos/pesquisa/PLATAFORMA-POLITICOS-AM.md`. Quem foi vereador, prefeito e depois deputado aparece numa ficha só. Título e CPF não são publicados.

## Como atualizar

Os três repositórios ficam lado a lado em `projetos/pesquisa/`. Depois que algum deles gerar dados novos:

```
python -I scripts/montar.py
```

O script lê os CSV do contrato (`pessoas.csv`, `candidaturas*.csv`, `mandatos*.csv`, `resumo.csv`, indicadores), copia as fotos,
gera `data/` e grava `INTEGRIDADE.md` (checagens da junção, arquivos ainda não publicados e alertas). Nada é coletado aqui.

## Telas

- Busca por nome, nome de urna ou município.
- Pessoa: mandatos, todas as candidaturas, patrimônio declarado por eleição, atuação parlamentar e link para o dossiê.
- Município: prefeitos desde 2001, eleições, câmara por legislatura, finanças, pessoal/RCL, IDEB da rede municipal, emendas recebidas.
- Bancada federal e Estudos (reeleição, mulheres eleitas, partidos, LRF, IDEB por mandato, emendas por habitante).
