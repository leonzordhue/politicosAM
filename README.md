# Almanaque Político do Amazonas

Governador, senadores, deputados federais e estaduais, prefeitos e vereadores do Amazonas: candidaturas, mandatos,
patrimônio declarado, gastos de cota, emendas, leis municipais, finanças e indicadores dos 62 municípios.

Dados públicos oficiais (TSE, Câmara dos Deputados, Senado Federal, ALEAM, Tesouro Nacional, IBGE, INEP, FNDE, Ministério
da Saúde, CGU, SEFAZ-AM, TCE-AM, TCU, Câmaras Municipais e Diário Oficial dos Municípios). Cada seção do site indica a fonte.

https://leonzordhue.github.io/politicosAM/

## Base de dados (`base/`)

Tabelas em CSV (UTF-8, vírgula) que alimentam o site, reunidas num só lugar. A chave `pessoa_id` liga a mesma pessoa entre as tabelas.

- `prefeitos-vereadores/`: candidaturas, mandatos, bens declarados, sucessões, julgamentos, atos dos prefeitos, matérias e votações das Câmaras, finanças e indicadores dos 62 municípios.
- `deputados-estaduais/`: deputados estaduais e governadores (candidaturas, mandatos, bens, cota parlamentar, emendas, proposições), com um perfil por deputado, por governador e por legislatura.
- `vereadores-manaus/`: Câmara Municipal de Manaus (cota dos vereadores, servidores e remunerações, demonstrativos orçamentários).
- `deputados-am-camara/`: emendas parlamentares (Portal da Transparência) e leis da bancada do AM na Câmara dos Deputados.

CPFs aparecem mascarados (`123.***.***-45`). Os títulos de eleitor não são publicados.
