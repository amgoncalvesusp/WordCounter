# Contador de Palavras

Software desktop standalone para contagem padronizada de palavras em PDFs, análise de proposições legislativas em CSV e análise de séries anuais para pesquisas sobre a Teoria do Equilíbrio Pontuado (PET). Desenvolvido para apoiar pesquisas acadêmicas em políticas públicas, com suporte a Mensagens ao Congresso Nacional e outros documentos institucionais.

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20343113.svg)](https://doi.org/10.5281/zenodo.20343113)
![Linguagem](https://img.shields.io/badge/Python-3.11%2B-blue)
![Plataforma](https://img.shields.io/badge/Plataforma-Windows-lightgrey)
![GUI](https://img.shields.io/badge/GUI-PyQt6-brightgreen)
![OCR](https://img.shields.io/badge/OCR-Tesseract-yellow)

---

## Visão geral

O Contador de Palavras realiza, em lote, a extração e contagem de palavras em PDFs seguindo um conjunto explícito de regras de contagem. Para cada documento, retorna:

- **Contagem total**: todo o texto extraído (capa, sumário, expediente, corpo principal etc.)
- **Contagem do corpus analítico**: apenas o conteúdo substantivo, com exclusão automática de elementos pré-textuais
- **Metadados detectados**: ano, presidente (no caso de Mensagens), tipo de documento
- **Indicadores de confiabilidade**: páginas com texto, páginas problemáticas, uso de OCR, grau de confiança
- **Contagem opcional de termos e expressões** definidos pelo pesquisador

Os resultados são apresentados em interface gráfica e exportáveis em planilhas XLSX com resumo, evidências e parâmetros conforme a análise selecionada. As abas **PDFs**, **Legislativo**, **Séries PET** e **Como usar** separam os fluxos. A interface e a documentação integrada estão disponíveis em português brasileiro.

## Principais funcionalidades

- Interface gráfica em PyQt6 com drag-and-drop para múltiplos PDFs e pastas
- Processamento assíncrono (não trava a interface) com barra de progresso por arquivo e geral
- OCR automático via Tesseract para PDFs escaneados (idioma português)
- Detecção heurística de páginas pré-textuais (ficha catalográfica, sumário, expediente, lista de ministros etc.)
- Detecção automática de metadados (ano, tipo de documento) a partir do conteúdo do PDF
- Detecção de presidente **opcional** e configurável via `data/presidents.json` (adaptável a outros países/períodos)
- Busca de palavras e expressões com curinga `*` (plural, masculino/feminino), alternativas com `|` e busca literal entre aspas
- Análise de sentimento em português (LeIA / VADER-PT) por sentença, com detalhamento exportável para análise de conteúdo e núcleos de significação
- Métricas textuais: legibilidade (Flesch-PT), diversidade lexical (TTR / Guiraud) e frequência de palavras-chave (com aba detalhada no XLSX)
- Concordância KWIC: contexto ao redor de cada ocorrência dos termos de busca (aba "Concordância (KWIC)"), a unidade de contexto da análise de conteúdo
- Perfil de política climática: matriz de setores, instrumentos, evidências textuais e lacunas do que cada documento reporta como política climática
- Importação offline de CSV legislativo, com mapeamento de colunas, filtros por tipo/período e deduplicação por Casa/identificador
- Busca booleana legislativa com `AND`, `OR`, `NOT`, parênteses, alternativas `|`, frases e curingas
- Classificação por proposição com evidências, revisão manual e índice anual de atenção climática por Casa
- Análise de mudanças anuais com excesso de curtose amostral corrigido, curtose correspondente e L-curtose
- Exportação em XLSX formatado com cabeçalho estilizado, congelamento de painéis e linhas alternadas
- Aba **Como usar** e atalho F1 com instruções práticas, fórmulas e interpretação das análises
- Aplicação totalmente offline; nenhum dado é enviado a serviços externos

---

## Instalação

### Opção 1: Usuário final (executável)

> O executável compilado (`.exe`) está disponível em **Releases**.

### Opção 2: Desenvolvimento (a partir do código)

**Requisitos:**

- Python 3.11 ou superior
- Windows 10/11 (testado); Linux/macOS provavelmente compatíveis com ajustes
- Tesseract-OCR instalado (opcional, apenas para PDFs escaneados)

**Passos:**

```bash
git clone https://github.com/<usuario>/WordCounter.git
cd WordCounter
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m src.main
```

### Tesseract (OCR)

Necessário apenas se você for processar PDFs escaneados (apenas imagem).

1. Baixe a versão para Windows em: <https://github.com/UB-Mannheim/tesseract/wiki>
2. Durante a instalação, marque o pacote de idioma **português** (`por`)
3. Mantenha o caminho padrão `C:\Program Files\Tesseract-OCR` para detecção automática

O software detecta o Tesseract na inicialização e habilita/desabilita a opção de OCR conforme disponibilidade.

---

## Como usar

### PDFs: fluxo básico

1. **Adicionar PDFs**: arraste arquivos para a área pontilhada ou clique em *Adicionar Arquivos*. Pastas também são aceitas (todos os PDFs da pasta são incluídos).
2. **(Opcional) Definir termos de busca**: digite, no painel direito, um termo por linha. Use `*` para variações (`climátic*`), `|` para agrupar variantes na mesma coluna e aspas para busca literal.
3. **(Opcional) Marcar OCR**: ative se houver PDFs escaneados (apenas imagem).
4. **Processar**: clique em *▶ Processar PDFs*.
5. **Exportar**: ao final, clique em *⬇ Exportar XLSX* para salvar os resultados.
6. **Enviar à PET**: após processar, escolha **Palavras do corpus**, **Palavras do PDF** ou **Ocorrências no corpus: &lt;termo&gt;** e clique em **Enviar contagens para PET**. A série é enviada na unidade **Contagem**.

Para corpora que não sejam Mensagens Presidenciais, desative **Detectar presidente**. Confira os anos detectados e as páginas excluídas antes de analisar a série.

O envio à PET exige **um PDF por ano válido e único**. Anos ausentes ou duplicados precisam ser preparados ou ajustados manualmente nos pares ano/valor da aba **Séries PET**; o programa não agrega PDFs automaticamente. As contagens enviadas não representam proporção de texto climático. A cobertura da taxonomia também não é transformada automaticamente em atenção climática.

### Legislativo: importar CSV e obter atenção anual

1. Baixe a produção completa do período na fonte oficial. Use a aba **Legislativo** para adicionar o CSV; a importação não faz coleta automática por API.
2. Confira a amostra e escolha a Casa, o identificador, a data/ano de apresentação, o tipo e as colunas textuais disponíveis, como `ementa`, `ementaDetalhada`, `keywords`, indexação ou resumo. Prefira a data de apresentação: o ano da numeração pode representar outro evento.
3. Defina os tipos e o período. Confira `PLS` e `PLC` em séries históricas, além de `PL`, `PEC`, `PLP` e `MPV`. Numerador e denominador usam o mesmo recorte.
4. Escreva uma regra booleana e processe. Exemplo:

   ```text
   ("mudanças climáticas" OR "mudanças do clima") OR (carbono AND emiss*)
   ```

5. Confira os termos, campos e trechos encontrados. Revise amostras tanto dos identificados quanto dos não identificados; registre decisões manuais e, se necessário, restaure a classificação automática.
6. Exporte as proposições, evidências, revisões, resumo anual e parâmetros. Para analisar mudanças, envie uma Casa por vez à aba **Séries PET**.

**Regras da busca:** `NOT` tem precedência sobre `AND`, que tem precedência sobre `OR`; `|` equivale a `OR`. Parênteses deixam a regra explícita. Condições de um `AND` podem estar em campos diferentes da mesma proposição, mas uma frase não atravessa colunas. A busca ignora acentos e caixa. Fora de aspas, `*` aceita variações; dentro de aspas, `*` e `|` são literais. A sintaxe booleana pertence ao fluxo legislativo; o campo de termos dos PDFs mantém uma expressão por linha.

**Índice de atenção climática anual (%) = 100 × proposições climáticas únicas ÷ total de proposições únicas do recorte.** Exemplo: 80 proposições climáticas entre 4.000 elegíveis = 2%. Dez ocorrências na mesma proposição continuam contando uma proposição.

A deduplicação usa Casa e identificador. Casas diferentes permanecem separadas, evitando somar automaticamente a mesma matéria durante a tramitação bicameral. Duplicatas com ano ou tipo conflitante precisam de correção antes da análise.

Sem texto para buscar, o registro fica **pendente**. Pendentes permanecem no total; enquanto existirem, o percentual definitivo fica indisponível. O **mínimo identificado (%)** mostra os positivos já identificados divididos pelo total do recorte, incluindo os pendentes. Preencha os textos ou revise os registros antes de formar uma série definitiva. A decisão automática e as evidências são preservadas após revisão.

**Limites do indicador:** identifica correspondência às regras, não verdade temática definitiva. “Não identificado” não comprova ausência de conteúdo climático. Projetos contrários a uma política climática também podem indicar atenção; a medida não equivale a apoio, aprovação ou implementação.

**Fontes:** a [Câmara disponibiliza arquivos por ano de apresentação](https://dadosabertos.camara.leg.br/swagger/api.html?tab=staticfile). No [catálogo do Senado](https://www12.senado.leg.br/dados-abertos/conjuntos?grupo=projetos-e-materias&portal=Legislativo), alguns CSVs incluem apenas matérias atualmente em tramitação: não representam toda a produção histórica. A [identificação de projetos mudou em 2019](https://www12.senado.leg.br/manualdecomunicacao/estilos/pl); confira a cobertura histórica e as siglas antes de comparar anos.

### Séries PET: calcular e interpretar mudanças

1. Na aba **Séries PET**, receba o resumo de uma Casa ou importe um CSV com ano e valor. Também é possível digitar um par `ano;valor` por linha, por exemplo `2020;2,0`.
2. Dê nome à série e escolha a unidade: percentual, contagem ou outra unidade. Não misture conceitos entre anos.
3. Escolha a mudança: **diferença** ou **variação relativa**. Calcule e confira níveis, transições válidas e avisos.
4. Exporte a série, mudanças, estatísticas e parâmetros para auditoria.

| Medida | Cálculo e interpretação |
|---|---|
| Diferença | Valor atual − anterior. De 2% para 3% = **+1 ponto percentual**; contagens mantêm a unidade original. |
| Variação relativa | `100 × (atual − anterior) / anterior`. De 2% para 3% = **+50%**. Base zero gera transição indefinida, sem pseudocontagem. |
| Excesso de curtose | Estimador amostral corrigido, compatível com `CURT` do Excel. Referência da distribuição normal: **0**. Sensível a mudanças extremas. |
| Curtose correspondente | Excesso corrigido + 3. Referência normal: **3**. Confira a convenção antes de comparar com publicações. |
| L-curtose | Razão entre momentos-L amostrais `l4/l2`. Referência normal: aproximadamente **0,1226**. Menos sensível a extremos; não é curtose de dados logaritmizados. |

As estatísticas são calculadas sobre as **mudanças entre anos consecutivos**, não sobre os níveis de atenção. Anos ausentes não viram zeros e não são conectados como se a mudança fosse anual. Com menos de quatro mudanças válidas ou mudanças constantes, as estatísticas ficam indisponíveis. O aviso de menos de 20 mudanças é uma cautela heurística sobre séries curtas, não um tamanho mínimo universal nem um teste de significância.

Curtose elevada pode ser compatível com mudanças pontuadas, mas não confirma a PET nem identifica sua causa. As referências da distribuição normal não são limiares de significância. Examine a sequência temporal, eventos, cobertura, zeros, lacunas e sensibilidade à classificação. A análise não comprova atenção desproporcional às necessidades sociais sem medir também essas necessidades.

Para **Mensagens ao Congresso**, importe uma série cujo indicador esteja definido e validado. Contagem de termos não se converte automaticamente em percentual de texto climático, pois expressões podem se sobrepor ou repetir. A cobertura da taxonomia do perfil climático também é uma medida diferente da atenção textual ou legislativa.

Referências: [Microsoft — função CURT](https://support.microsoft.com/pt-pt/excel/functions/kurt-function); [Baumgartner e colaboradores — Punctuated Equilibrium in Comparative Perspective](https://fbaum.unc.edu/articles/Comp_friction/PE_in_Comparative_Perspective_AJPS_Identified.pdf); [Kaplaner e Steinebach — discussão dos limites da curtose e L-curtose](https://doi.org/10.1017/pan.2021.25).

### Sintaxe da busca de termos

| Entrada                                 | Comportamento                                                              |
|-----------------------------------------|----------------------------------------------------------------------------|
| `clima`                                 | Palavra inteira, accent-insensitive e case-insensitive                     |
| `climátic*`                             | Curinga: completa o fim da palavra (*climática, climático, climáticas...*) |
| `mudanç* climátic*`                     | Sequência de palavras, com curinga em qualquer uma delas                   |
| `mudanç* d* clima \| mudanç* climátic*` | Alternativas somadas em **uma única coluna** do relatório                  |
| `"efeito estufa"`                       | Busca literal da expressão; `*` e `\|` viram caracteres comuns             |
| `# comentário`                          | Linha ignorada                                                             |
| (linha em branco)                       | Ignorada                                                                   |

Não é preciso digitar cada flexão: o curinga `*` cobre plural, masculino e
feminino, e o `|` agrupa variantes distintas sob o mesmo rótulo. As aspas só
são necessárias quando se quer a expressão literal, sem variações.

**Exemplo:**

```text
# Cada linha vira uma coluna no relatório

# As quatro variantes de "mudança climática" em uma única coluna:
mudanç* d* clima | mudanç* climátic*

# Variações de gênero e número com o curinga *:
climátic*
sustentáve* | sustentabilidade

# Palavras simples:
carbono
desmatamento
mitigação
adaptação

# Expressões literais, sem variações:
"efeito estufa"
"perdas e danos"
```

A busca é insensível a acentos e maiúsculas/minúsculas. Cada termo retorna duas contagens: uma considerando o PDF completo e outra considerando apenas o corpus analítico.

### Regras de contagem de palavras

**Contam como palavra:**

- Sequências de letras (incluindo acentuadas): *política*, *açúcar*
- Palavras hifenizadas como unidade lexical: *cooperação-internacional*
- Siglas formadas por letras: *ONU*, *FMI*, *SUS*, *PIB*
- Abreviações com letras

**Não contam:**

- Números isolados (*2024*, *15*)
- Algarismos romanos como marcadores de capítulo (*III*, *IV*, *XIV*)
- Pontuação e símbolos
- Caracteres soltos provenientes de erro de OCR

### Detecção do corpus analítico

O software identifica automaticamente, com base em palavras-chave e heurísticas, páginas a serem excluídas da contagem do corpus analítico:

- Capa e folha de rosto
- Ficha catalográfica (ISBN, CDD, CDU, Biblioteca da Presidência)
- Sumário ou Índice (detectado também por padrão de linhas pontilhadas)
- Expediente
- Listas de ministros e autoridades
- Páginas em branco

A aba *Páginas Excluídas* do arquivo XLSX exportado contém a lista completa e o motivo de cada exclusão, permitindo auditoria manual.

### Concordância (KWIC)

Para cada termo de busca, a opção **Concordância (KWIC)** (*Keyword-In-Context*,
ligada por padrão) registra o **contexto** ao redor de cada ocorrência — algumas
palavras à esquerda, o termo, e algumas palavras à direita. Diferente da
contagem, é uma saída **qualitativa**: permite ler cada ocorrência em seu
contexto, a *unidade de contexto* da análise de conteúdo de Bardin.

- Requer ao menos um termo de busca; usa a mesma correspondência da busca de
  termos (sem distinção de acentos, frases de várias palavras suportadas).
- A grafia original das palavras de contexto é preservada na exportação.
- Resultados na aba **"Concordância (KWIC)"** do XLSX: nº do documento, arquivo,
  página, termo, contexto à esquerda, ocorrência e contexto à direita.

Referência: Bardin, L. (2011). *Análise de Conteúdo*. São Paulo: Edições 70.

### Perfil de política climática

A opção **Perfil de política climática** (ligada por padrão) cria uma "imagem"
do que o documento reporta como política climática. A análise usa uma taxonomia
editável em `src/core/data/climate_policy_taxonomy.json`, com setores
(energia, transportes, agropecuária, florestas, indústria, resíduos, adaptação,
governança etc.) e instrumentos (planejamento, regulação, comando e controle,
financiamento, instrumentos econômicos, informação/monitoramento, pesquisa e
cooperação internacional).

A classificação distingue:

- **Reportado direto**: setor ou instrumento aparece em trecho com âncora
  climática, como clima, carbono, emissões, mitigação ou adaptação.
- **Menção indireta**: setor ou instrumento aparece no corpus analítico, mas sem
  enquadramento climático claro no mesmo trecho.
- **Não reportado**: item esperado na taxonomia não aparece como política
  climática no documento.

Essa saída não afirma que a política existe ou inexiste fora do relatório. Ela
registra o que foi reportado no documento, preservando a ressalva metodológica
de que instrumentos multissetoriais podem ter relação direta com clima, mas não
serem incluídos no reporte.

No XLSX, a opção adiciona as abas **"Politica Climatica"**,
**"Evidencias Climaticas"** e **"Lacunas Climaticas"**.

### Métricas textuais

Conjunto de medidas (caixa "Métricas textuais", ligada por padrão) calculadas
sobre o corpus analítico e exportadas no XLSX. Voltadas à análise de conteúdo e
à identificação de núcleos de significação.

- **Legibilidade — Flesch adaptado ao português:**
  `ILF = 248,835 − 1,015 × (palavras/frases) − 84,6 × (sílabas/palavras)`.
  Classes: Muito fácil (≥75), Fácil (50–75), Difícil (25–50), Muito difícil (<25).
  A contagem de sílabas usa heurística de grupos vocálicos (aproximada).
- **Diversidade lexical:** TTR (tipos/tokens) e Índice de Guiraud
  (tipos/√tokens), mais estável quanto ao tamanho do texto.
- **Frequência de palavras-chave:** palavras de conteúdo mais frequentes, após
  remoção de stopwords (lista editável em `data/stopwords_pt.txt`). As 10 mais
  frequentes vão para a tabela; as 30 mais frequentes, para a aba
  **"Frequência de Palavras"** — base quantitativa da análise de conteúdo.

**Referências metodológicas:**

- Martins, T. B. F. et al. (1996). *Readability formulas applied to textbooks in
  Brazilian Portuguese*. Notas do ICMC-USP, n. 28.
- Guiraud, P. (1954). *Les caractères statistiques du vocabulaire*. Paris: PUF.
- Templin, M. (1957). *Certain language skills in children*. University of
  Minnesota Press.
- Bardin, L. (2011). *Análise de Conteúdo*. São Paulo: Edições 70.

### Detecção de presidente (opcional)

A identificação do chefe de Estado é **opcional** (caixa de seleção "Detectar
presidente", ligada por padrão). Desative-a para corpora genéricos — a coluna
"Presidente" é então omitida da tabela e do XLSX.

A lista é externa ao código, em `src/core/data/presidents.json`, e pode ser
editada para adaptar a ferramenta a outros países ou períodos:

```json
{
  "presidents": [
    {
      "canonical": "Nome Oficial",
      "start": 2023,
      "end": 2026,
      "variants": ["Nome Oficial", "Apelido"]
    }
  ]
}
```

- `start`/`end`: anos do mandato (AAAA), usados para desambiguar pelo ano do documento.
- `variants`: grafias buscadas (sem distinção de maiúsculas) no início do documento.

Se o arquivo estiver ausente ou inválido, a detecção apenas retorna vazio — o
restante da análise continua normalmente.

### Grau de confiança

| Grau   | Critério                                                              |
|--------|-----------------------------------------------------------------------|
| Alto   | ≥95% das páginas com texto extraído; pouco ou nenhum OCR              |
| Médio  | 80–95% das páginas com texto; ou uso intensivo de OCR                 |
| Baixo  | Menos de 80% das páginas com texto extraído                           |

### Análise de sentimento

A análise de sentimento usa um modelo **baseado em regras e léxico** (VADER), o
que garante **transparência e reprodutibilidade**: cada escore é rastreável até a
palavra e a regra que o produziram — propriedade desejável em pesquisa
qualitativa interpretativa, ao contrário de modelos de "caixa-preta".

- **Método:** VADER (*Valence Aware Dictionary and sEntiment Reasoner*) — léxico
  validado por juízes humanos combinado a heurísticas de negação, intensificadores,
  ênfase em maiúsculas e pontuação. Produz um escore `compound` normalizado em
  `[-1, +1]`.
- **Adaptação ao português:** **LeIA** (*Léxico para Inferência Adaptada*), fork do
  VADER para o português brasileiro (léxico e regras vendorizados no projeto,
  licença MIT, totalmente offline).
- **Unidade de análise:** a **sentença**. Cada sentença recebe escore e classe
  (Positivo `compound ≥ 0,05`; Negativo `≤ -0,05`; Neutro caso contrário). Por
  documento, são reportados a classe geral, o composto médio e o percentual de
  sentenças positivas/negativas/neutras.
- **Saída para análise qualitativa:** o XLSX inclui a aba **"Sentimento
  (Sentenças)"** com cada sentença, página, escore e classe. Esse detalhamento
  fornece as **unidades de registro** da Análise de Conteúdo (Bardin) e os
  **pré-indicadores afetivos** dos Núcleos de Significação (Aguiar & Ozella),
  permitindo agrupar trechos carregados de afeto em indicadores e núcleos.

A análise pode ser ligada/desligada por uma caixa de seleção na interface.

**Referências metodológicas:**

- Hutto, C. J. & Gilbert, E. E. (2014). *VADER: A Parsimonious Rule-based Model for
  Sentiment Analysis of Social Media Text*. ICWSM-14. Ann Arbor, MI.
- Almeida, R. J. de A. *LeIA — Léxico para Inferência Adaptada*.
  <https://github.com/rafjaa/LeIA>
- Bardin, L. (2011). *Análise de Conteúdo*. São Paulo: Edições 70.
- Aguiar, W. M. J. & Ozella, S. (2006; 2013). *Núcleos de significação como
  instrumento para a apreensão da constituição dos sentidos* / *Apreensão dos
  sentidos: aprimorando a proposta dos núcleos de significação*.

### Atalhos de teclado

| Atalho        | Ação                          |
|---------------|-------------------------------|
| `Ctrl+O`      | Adicionar PDFs                |
| `Ctrl+E`      | Exportar XLSX                 |
| `Ctrl+Q`      | Sair                          |
| `F1`          | Abrir documentação integrada  |

---

## Estrutura do projeto

```text
WordCounter/
├── src/
│   ├── main.py                  # entry point
│   ├── core/
│   │   ├── word_counter.py      # regras de contagem (regex Unicode)
│   │   ├── corpus_filter.py     # detecção de páginas a excluir
│   │   ├── metadata_detector.py # detecção de ano/presidente/documento
│   │   ├── term_search.py       # busca de termos e expressões
│   │   ├── ocr_engine.py        # wrapper Tesseract + fallback
│   │   ├── pdf_processor.py     # orquestrador
│   │   └── exporter.py          # exportação XLSX formatada
│   └── gui/
│       ├── main_window.py       # janela principal
│       ├── help_dialog.py       # diálogo de ajuda integrada
│       ├── workers.py           # QThread workers (processamento assíncrono)
│       └── styles.py            # stylesheet (tema escuro Catppuccin Mocha)
├── requirements.txt
├── build.bat                    # script PyInstaller (Windows)
├── LICENSE
└── README.md
```

### Tecnologias

- **PyQt6** — Interface gráfica
- **PyMuPDF (fitz)** — Extração de texto e renderização de páginas
- **pytesseract** + **Pillow** — Wrapper Python sobre Tesseract para OCR
- **openpyxl** — Geração de XLSX
- **regex** — Suporte Unicode avançado para classes `\p{L}`
- **PyInstaller** — Empacotamento em executável (build)

---

## Build do executável

Em ambiente Windows com Python e dependências instaladas:

```cmd
build.bat
```

Saída: `dist\ContadorPalavras.exe`

Se o Tesseract estiver instalado em `C:\Program Files\Tesseract-OCR`, o script o embarca automaticamente no executável. Caso contrário, o usuário final precisará instalá-lo separadamente.

---

## Reprodutibilidade

Toda a contagem segue regras determinísticas, sem componentes aleatórios. Processar os mesmos PDFs nas mesmas condições produz resultados idênticos. Diferenças entre execuções só podem ocorrer quando o OCR é aplicado a páginas marginais cuja qualidade de imagem varia o reconhecimento.

A documentação completa dos critérios de contagem, exclusão e classificação de confiança está embutida no software (atalho F1) e neste README, garantindo auditabilidade do processo.

---

## Testes

A suíte usa **pytest** e cobre o motor de contagem, a busca de termos, o filtro de
corpus, a detecção de metadados, os analisadores (incluindo sentimento) e a
exportação, além de um teste de integração do pipeline completo sobre um PDF
sintético.

```bash
pip install -r requirements-dev.txt
pytest                       # executa a suíte
pytest --cov=src/core        # com relatório de cobertura
```

A cobertura do código próprio exclui a biblioteca vendorizada LeIA; consulte o relatório gerado pela suíte para o valor da versão em teste. Os testes de interface podem ser executados com `QT_QPA_PLATFORM=offscreen`.

---

## Limitações conhecidas

- A detecção de páginas pré-textuais é heurística e pode produzir falsos positivos em layouts atípicos. Verifique sempre a aba *Páginas Excluídas* do XLSX exportado.
- A detecção automática de ano e presidente baseia-se em padrões textuais; em PDFs com baixa qualidade de extração, pode falhar (campos retornam vazios).
- O OCR adiciona tempo significativo de processamento (segundos por página). Use apenas quando necessário.
- A classificação legislativa depende das colunas textuais e da regra usada. Revise amostras positivas e negativas; arquivos incompletos e mudanças de indexação afetam o índice anual.
- As estatísticas PET são descritivas. Não demonstram causalidade nem confirmam a teoria automaticamente; séries curtas e lacunas exigem cautela.

---

## Autoria

Trabalho desenvolvido no âmbito do Programa de Pós-graduação em Desenvolvimento Territorial e Meio Ambiente da Universidade de Araraquara (UNIARA):

- Natalia Vieira de Carvalho
- Alessandra Nascimento dos Santos
- Helena Carvalho de Lorenzo
- Adriano Marques Gonçalves

---

## Licença

MIT — consulte o arquivo [LICENSE](LICENSE) para detalhes.

---

## Citação

Caso utilize este software em sua pesquisa, sugere-se a seguinte citação:

> MARTINS, N. V. C.; SANTOS, A. N. dos; LORENZO, H. C. de; GONÇALVES, A. M. *Contador de Palavras: ferramenta para análise quantitativa padronizada de corpus documentais em PDF*. Araraquara: UNIARA, 2026. DOI: [10.5281/zenodo.20343113](https://doi.org/10.5281/zenodo.20343113).
