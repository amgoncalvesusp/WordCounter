"""In-app help dialog."""

from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QPushButton, QTextBrowser, QVBoxLayout, QWidget,
)


HELP_HTML = """
<style>
    body { font-family: "Segoe UI", sans-serif; color: #cdd6f4; font-size: 11pt; line-height: 1.55; }
    h1 { color: #f5e0dc; font-size: 18pt; margin-top: 12px; }
    h2 { color: #cba6f7; font-size: 14pt; margin-top: 18px; padding-bottom: 4px; }
    h3 { color: #f9e2af; font-size: 12pt; margin-top: 14px; }
    code { background: #313244; color: #f5e0dc; padding: 2px 6px; border-radius: 4px; }
    pre { background: #181825; color: #cdd6f4; padding: 12px; border-radius: 8px;
          border-left: 3px solid #cba6f7; }
    .tip { background: #181825; padding: 12px; border-left: 3px solid #a6e3a1;
           border-radius: 6px; margin: 10px 0; }
    .warn { background: #181825; padding: 12px; border-left: 3px solid #f9e2af;
            border-radius: 6px; margin: 10px 0; }
    ul { margin-left: 8px; padding-left: 16px; }
    li { margin: 4px 0; }
    .key { background: #45475a; color: #f5e0dc; padding: 2px 8px; border-radius: 4px;
           font-family: monospace; font-size: 10pt; }
</style>

<h1>Como usar o Contador de Palavras</h1>

<p>Use as abas <b>PDFs</b>, <b>Legislativo</b> e <b>Séries PET</b> para preparar dados e estudar atenção ao longo do tempo. Esta documentação acompanha o idioma disponível no programa: português brasileiro.</p>

<p><a href="#pdfs">PDFs</a> · <a href="#legislativo">Legislativo</a> ·
<a href="#pet">Séries PET e estatísticas</a> · <a href="#metricas">Métricas textuais</a></p>

<h2 id="pdfs">PDFs: início rápido</h2>
<ol>
    <li><b>Adicionar PDFs</b> — Arraste arquivos para a área pontilhada ou clique em <code>Adicionar Arquivos</code>.</li>
    <li><b>(Opcional) Definir termos de busca</b> — Digite termos no campo de busca, um por linha.</li>
    <li><b>(Opcional) Marcar OCR</b> — Ative se algum PDF for escaneado (apenas imagem).</li>
    <li><b>Processar</b> — Clique em <code>▶ Processar PDFs</code>. O progresso aparece na barra inferior.</li>
    <li><b>Exportar</b> — Após conclusão, clique em <code>⬇ Exportar XLSX</code>.</li>
    <li><b>Enviar à PET</b> — Após processar, escolha <code>Palavras do corpus</code>, <code>Palavras do PDF</code> ou <code>Ocorrências no corpus: &lt;termo&gt;</code> e clique em <code>Enviar contagens para PET</code>. A série chega à aba <b>Séries PET</b> na unidade <b>Contagem</b>.</li>
</ol>
<p>Para documentos que não sejam Mensagens Presidenciais, desative <b>Detectar presidente</b>. O ano detectado e as páginas excluídas exigem conferência no XLSX. O botão <b>Cancelar</b> interrompe o lote; exportações parciais, quando disponíveis, não representam o corpus completo.</p>
<p>O envio exige <b>um PDF por ano válido e único</b>. Se os anos estiverem ausentes ou duplicados, prepare ou ajuste manualmente os pares ano/valor na aba <b>Séries PET</b>; o programa não agrega PDFs automaticamente. As contagens enviadas <b>não são proporção de texto climático</b>. A cobertura da taxonomia não é transformada automaticamente em atenção climática.</p>

<h2 id="legislativo">Legislativo: importar, classificar e revisar</h2>
<ol>
    <li>Baixe a produção completa do período na fonte oficial; evite arquivos previamente filtrados por palavras climáticas.</li>
    <li>Adicione o <b>CSV</b> e confira a amostra. Escolha a Casa (Câmara ou Senado), o identificador único, a data de apresentação ou ano, o tipo e as colunas textuais: <b>ementa, ementa detalhada, indexação, resumo ou keywords</b>, conforme o arquivo.</li>
    <li>Prefira a <b>data de apresentação</b> quando disponível. O ano da numeração do projeto pode ser diferente do ano de apresentação na Casa.</li>
    <li>Defina os mesmos tipos e anos para todo o recorte. Para uma série histórica, confira também <b>PLS</b> e <b>PLC</b>, além de <b>PL, PEC, PLP e MPV</b>. Tipos não selecionados ficam fora tanto do numerador quanto do denominador.</li>
    <li>Digite uma expressão booleana e processe. Leia os campos, termos e trechos que sustentam a identificação. Uma proposição conta uma vez, mesmo com várias ocorrências.</li>
    <li>Revise uma amostra de identificados e de não identificados. Use a revisão para marcar <b>sim</b> ou <b>não</b>, com nota quando necessário; escolha <b>restaurar automático</b> para retirar uma revisão. A decisão automática e suas evidências são preservadas.</li>
    <li>Confira o resumo anual e exporte XLSX. Envie uma Casa por vez à aba <b>Séries PET</b>, mantendo o rótulo e a unidade da série.</li>
</ol>
<p><b>Exemplo de regra:</b></p>
<pre>("mudanças climáticas" OR "mudanças do clima") OR (carbono AND emiss*)</pre>
<ul>
    <li><code>OR</code> ou <code>|</code>: pelo menos uma alternativa.</li>
    <li><code>AND</code>: ambas as condições; podem estar em colunas diferentes da mesma proposição.</li>
    <li><code>NOT</code>: ausência da condição seguinte. Use exclusões apenas com justificativa metodológica.</li>
    <li>Precedência: <code>NOT</code>, depois <code>AND</code>, depois <code>OR</code>. Parênteses deixam a regra explícita.</li>
    <li><code>climátic*</code> aceita flexões. Aspas tornam a expressão literal; dentro delas, <code>*</code> e <code>|</code> são caracteres comuns. A busca ignora acentos e caixa. Uma frase não atravessa duas colunas.</li>
</ul>
<p><b>Estados:</b> identificado = regra satisfeita; não identificado = texto disponível sem correspondência; <b>Pendentes</b> = ausência de texto para classificar. Ausência de termo não comprova ausência de conteúdo climático. Projetos favoráveis e contrários à política climática podem representar atenção ao tema; o resultado não mede apoio nem implementação.</p>
<p><b>Índice de atenção climática (%) = 100 × proposições climáticas únicas ÷ total de proposições únicas do recorte.</b> Exemplo: 80 em 4.000 = 2%. A deduplicação usa Casa e identificador; a mesma matéria em Casas diferentes não é somada automaticamente.</p>
<p>Enquanto houver pendentes, o percentual definitivo fica indisponível. O <b>mínimo identificado (%)</b> mostra os positivos já identificados divididos pelo total, incluindo pendentes. Complete os textos ou revise os registros antes de formar uma série definitiva.</p>
<div class="warn">O catálogo do Senado informa que alguns CSVs incluem somente <b>matérias atualmente em tramitação</b>; não use esses arquivos isoladamente como produção histórica total. Registre fonte, data da coleta, período, tipos, colunas e regra. Alterações na indexação também podem afetar comparações entre anos.</div>

<h2 id="pet">Séries PET: início rápido</h2>
<ol>
    <li>Receba o resumo legislativo de uma Casa ou importe um CSV de série anual. Também é possível digitar pares <code>ano;valor</code>, um por linha, por exemplo <code>2020;2,0</code>.</li>
    <li>Identifique a série e sua unidade: percentual, contagem ou outra unidade. Mantenha o mesmo conceito em todos os anos.</li>
    <li>Escolha <b>diferença</b> ou <b>variação relativa</b> e calcule. Confira níveis, transições anuais, número de mudanças válidas e avisos antes das estatísticas.</li>
    <li>Exporte níveis, mudanças, estatísticas e parâmetros. As medidas resumem a distribuição das <b>mudanças</b>, não a distribuição dos níveis de atenção.</li>
</ol>
<p>Para Mensagens ao Congresso, uma série pode conter uma contagem explicitamente definida ou um percentual temático previamente validado. Somar termos encontrados não produz automaticamente percentual de texto climático: expressões podem se sobrepor, repetir-se ou ter sentidos diferentes. A cobertura da taxonomia do perfil climático também não serve como percentual de atenção textual.</p>

<h3>Escolher a mudança e interpretar</h3>
<ul>
    <li><b>Diferença:</b> valor atual − valor anterior. De 2% para 3% = <b>+1 ponto percentual</b>; em contagens, a diferença permanece na unidade original.</li>
    <li><b>Variação relativa (%):</b> 100 × (valor atual − valor anterior) ÷ valor anterior. De 2% para 3% = <b>+50%</b>. Essa medida é diferente de pontos percentuais.</li>
    <li>Usam-se somente <b>anos consecutivos</b>. Falta de ano não é preenchida com zero nem tratada como mudança de um ano.</li>
    <li><b>base zero:</b> variação relativa é indefinida; a transição fica sem valor e gera aviso. Não se adiciona pseudocontagem. Na diferença, passar de zero para um é uma mudança válida de +1.</li>
</ul>

<h3>Curtose, excesso e L-curtose</h3>
<ul>
    <li><b>Excesso de curtose amostral corrigido:</b> mesma convenção da função <code>CURT</code> do Excel. A distribuição normal tem referência <b>0</b>. Valores maiores sugerem maior peso de mudanças extremas nas caudas; poucos extremos podem dominar o resultado.</li>
    <li><b>Curtose correspondente (Pearson):</b> excesso corrigido + 3. A referência normal é <b>3</b>. Não compare diretamente esse número com um excesso publicado sem conferir a convenção.</li>
    <li><b>L-curtose amostral:</b> razão <code>l4/l2</code> entre momentos-L amostrais. A referência normal é aproximadamente <b>0,1226</b>. É menos sensível a extremos que a curtose usual, mas não elimina incerteza nem viés da seleção dos dados. Não é curtose de valores logaritmizados.</li>
    <li>Com <b>menos de quatro</b> mudanças válidas, ou com mudanças constantes, as estatísticas ficam indisponíveis. Série de níveis constante também produz mudanças constantes.</li>
    <li>Menos de <b>20 mudanças</b> gera aviso de série curta: é um alerta heurístico de cautela, não tamanho mínimo universal nem teste de significância.</li>
</ul>
<div class="warn">Curtose elevada pode ser compatível com mudanças pontuadas, mas <b>não confirma</b> a Teoria do Equilíbrio Pontuado (PET) por si só. Observe a sequência temporal, eventos, qualidade do universo, zeros, lacunas e sensibilidade às regras. Os valores de referência da normal não são limiares de significância. O software não estima causalidade, não detecta automaticamente o ano de uma pontuação e não mede desproporção frente às necessidades sociais sem uma medida dessas necessidades.</div>

<h2>Busca de termos e expressões</h2>

<p>Permite contar quantas vezes cada palavra ou expressão aparece em cada documento, tanto no PDF completo quanto no corpus analítico.</p>

<h3>Regras de sintaxe</h3>
<ul>
    <li><b>Palavra simples:</b> <code>clima</code> — conta todas as ocorrências da palavra inteira, ignorando acentos e maiúsculas/minúsculas. Não encontra <i>climático</i>.</li>
    <li><b>Curinga <code>*</code> (variações):</b> <code>climátic*</code> — completa o fim da palavra e encontra <i>climática</i>, <i>climático</i>, <i>climáticas</i>, <i>climáticos</i>. Resolve plural e gênero sem digitar cada forma.</li>
    <li><b>Expressão sem aspas:</b> <code>mudanç* climátic*</code> — busca a sequência de palavras, permitindo espaços variáveis e curinga em qualquer palavra.</li>
    <li><b>Alternativas com <code>|</code>:</b> <code>mudanç* d* clima | mudanç* climátic*</code> — soma todas as variantes em <b>uma única coluna</b> do relatório.</li>
    <li><b>Expressão com aspas (busca literal):</b> <code>"efeito estufa"</code> — exige correspondência exata da expressão entre limites de palavra. Dentro das aspas, <code>*</code> e <code>|</code> valem como caracteres comuns.</li>
    <li><b>Linha em branco</b> ou iniciada com <code>#</code> — ignorada (comentário).</li>
</ul>

<h3>Exemplo de entrada</h3>
<pre># Cada linha vira uma coluna no relatório

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
"perdas e danos"</pre>

<div class="tip">
    <b>Preciso usar aspas?</b> Não. As aspas servem só quando você quer a expressão <i>literal</i>, sem variações. Para cobrir <i>mudança do clima</i>, <i>mudanças do clima</i>, <i>mudanças climáticas</i> e <i>mudança climática</i> de uma vez, escreva uma linha só:
    <br><code>mudanç* d* clima | mudanç* climátic*</code>
</div>

<div class="tip">
    <b>Acentos e maiúsculas:</b> A busca é case-insensitive e accent-insensitive por padrão. <code>clima</code> encontra <i>Clima</i>, <i>CLIMA</i>, <i>clíma</i> (caso ocorra erro de OCR).
</div>

<h2>Regras de contagem de palavras</h2>

<h3>Contam como palavra</h3>
<ul>
    <li>Sequências de letras, incluindo acentuadas (ex: <i>política</i>, <i>açúcar</i>)</li>
    <li>Palavras hifenizadas como unidade lexical</li>
    <li>Siglas formadas por letras (ex: <i>ONU</i>, <i>FMI</i>, <i>SUS</i>, <i>PIB</i>)</li>
    <li>Abreviações com letras</li>
</ul>

<h3>Não contam</h3>
<ul>
    <li>Números isolados (<i>2024</i>, <i>15</i>)</li>
    <li>Algarismos romanos como marcadores de capítulo (<i>III</i>, <i>IV</i>, <i>XIV</i>)</li>
    <li>Pontuação e símbolos</li>
    <li>Marcadores de página</li>
    <li>Caracteres soltos de erro de OCR</li>
</ul>

<h2>Corpus analítico</h2>

<p>O software realiza duas contagens distintas:</p>
<ul>
    <li><b>PDF Completo</b> — Todo o texto extraído, incluindo capa, ficha catalográfica, sumário, etc.</li>
    <li><b>Corpus Analítico</b> — Apenas o conteúdo substantivo da Mensagem.</li>
</ul>

<h3>Páginas excluídas automaticamente</h3>
<ul>
    <li>Capa e folha de rosto</li>
    <li>Ficha catalográfica (ISBN, CDD, CDU, Biblioteca da Presidência)</li>
    <li>Sumário / Índice (detectado por padrão de linhas pontilhadas)</li>
    <li>Expediente</li>
    <li>Lista de ministros e autoridades</li>
    <li>Páginas em branco</li>
</ul>

<div class="warn">
    A detecção é baseada em palavras-chave e heurísticas. Pode haver falsos positivos em layouts atípicos. Confira o resumo de páginas excluídas na aba <i>Páginas Excluídas</i> do arquivo XLSX exportado.
</div>

<h2 id="metricas">Outras análises de PDFs: uso e interpretação</h2>
<ul>
    <li><b>Concordância (KWIC):</b> informe termos e ative a opção para exportar o contexto ao redor das ocorrências. Leia esses trechos para avaliar o sentido; frequência isolada não é análise de conteúdo concluída.</li>
    <li><b>Sentimento (LeIA/VADER-PT):</b> gera escore por sentença e média no documento. Positivo ≥ 0,05; negativo ≤ −0,05; neutro entre esses limites. O XLSX permite conferir sentenças. Valência lexical não demonstra apoio político, eficácia da política ou posição do autor; negações e linguagem técnica podem ser mal interpretadas.</li>
    <li><b>Legibilidade (Flesch-PT):</b> índice = 248,835 − 1,015 × palavras/frases − 84,6 × sílabas/palavras. Maior índice sugere leitura mais fácil; ≥75 muito fácil, 50–75 fácil, 25–50 difícil, &lt;25 muito difícil. Contagem silábica é aproximada; não mede qualidade científica.</li>
    <li><b>Diversidade lexical:</b> TTR = palavras distintas/tokens; Guiraud = palavras distintas/√tokens. Maior valor indica maior variedade lexical. TTR depende do tamanho do texto; compare corpora de extensão semelhante.</li>
    <li><b>Palavras-chave:</b> lista as palavras de conteúdo mais frequentes após excluir stopwords. Use a aba de frequências para explorar temas; palavra frequente não é necessariamente a mais relevante.</li>
    <li><b>Perfil climático:</b> setores/instrumentos reportados diretamente, menções indiretas e lacunas segundo o texto. A <b>cobertura da taxonomia</b> é a fração de itens esperados reportados, não a parcela climática do texto nem o índice legislativo anual.</li>
    <li><b>Metadados:</b> ano e presidente são detectados por padrões. Confira-os; desative presidente quando não fizer parte do corpus. Grau de confiança indica disponibilidade de texto, não precisão semântica de toda a análise.</li>
</ul>

<h2>OCR (PDFs escaneados)</h2>

<p>PDFs sem texto pesquisável (apenas imagem) requerem OCR para extrair conteúdo. O software usa <b>Tesseract</b> com idioma português.</p>

<ul>
    <li>O OCR é aplicado automaticamente em páginas com pouco ou nenhum texto extraível.</li>
    <li>Marque a checkbox <i>Aplicar OCR</i> antes de processar.</li>
    <li>Se o Tesseract não for detectado, a checkbox fica desabilitada. Instale-o e reinicie o programa.</li>
</ul>

<h3>Instalação do Tesseract</h3>
<ol>
    <li>Baixe em: <code>github.com/UB-Mannheim/tesseract/wiki</code></li>
    <li>Durante a instalação, marque o pacote de idioma <b>português</b>.</li>
    <li>Mantenha o caminho padrão (<code>C:\\Program Files\\Tesseract-OCR</code>) para detecção automática.</li>
</ol>

<h2>Grau de confiança</h2>

<p>Cada documento recebe uma classificação:</p>
<ul>
    <li><b style="color:#a6e3a1;">Alto</b> — Extração limpa, ≥95% das páginas com texto, pouco ou nenhum OCR.</li>
    <li><b style="color:#f9e2af;">Médio</b> — 80–95% das páginas com texto, ou uso intensivo de OCR.</li>
    <li><b style="color:#f38ba8;">Baixo</b> — Menos de 80% das páginas com texto extraído.</li>
</ul>

<h2>Perfil de política climática</h2>

<p>A opção <b>Perfil de política climática</b> monta uma imagem do que o documento reporta como política climática. A classificação usa uma taxonomia editável de setores e instrumentos, armazenada em <code>src/core/data/climate_policy_taxonomy.json</code>.</p>

<ul>
    <li><b>Reportado direto</b> — setor ou instrumento aparece em trecho com âncora climática, como clima, emissões, carbono, mitigação ou adaptação.</li>
    <li><b>Menção indireta</b> — setor ou instrumento aparece no corpus analítico, mas sem enquadramento climático claro no mesmo trecho.</li>
    <li><b>Não reportado</b> — item esperado na taxonomia não aparece como política climática no documento.</li>
</ul>

<div class="warn">
    A saída descreve o que está reportado no documento. Ela não afirma que uma política existe ou inexiste fora do relatório; apenas registra evidências textuais, menções indiretas e lacunas do reporte segundo a taxonomia usada.
</div>

<h2>Estrutura do XLSX exportado</h2>

<h3>Aba 1: Contagem de Palavras</h3>
<p>Linha por documento. Colunas: identificação, metadados detectados, contagens, grau de confiança, observações. Se termos de busca foram definidos, duas colunas por termo (PDF Completo / Corpus Analítico).</p>

<h3>Aba 2: Páginas Excluídas</h3>
<p>Lista detalhada de cada página excluída do corpus analítico, com motivo da exclusão e número de palavras na página.</p>

<h3>Abas de política climática</h3>
<p>Quando a opção está ligada, o XLSX inclui <i>Politica Climatica</i>, <i>Evidencias Climaticas</i> e <i>Lacunas Climaticas</i>, com matriz por setor/instrumento, trechos auditáveis e itens esperados que não foram reportados diretamente.</p>

<h2>Atalhos</h2>
<ul>
    <li><span class="key">Ctrl+O</span> — Adicionar arquivos</li>
    <li><span class="key">Ctrl+E</span> — Exportar XLSX</li>
    <li><span class="key">Ctrl+Q</span> — Sair</li>
    <li><span class="key">F1</span> — Como usar</li>
</ul>

<h2>Reprodutibilidade</h2>
<p>Toda a contagem segue regras determinísticas. Processar os mesmos PDFs nas mesmas condições produz exatamente os mesmos resultados. Diferenças entre execuções só ocorrem se houver OCR sobre páginas marginais (qualidade de imagem pode variar a saída).</p>
<p>Nas análises legislativas e PET, preserve os arquivos originais, a versão do programa, as regras, os mapeamentos e as revisões. As exportações registram parâmetros para apoiar auditoria. O processamento é local; importar CSV não coleta automaticamente dados dos portais.</p>

<h2>Fontes para conferir o método</h2>
<ul>
    <li><a href="https://dadosabertos.camara.leg.br/swagger/api.html?tab=staticfile">Câmara: arquivos de proposições por ano e cobertura</a>.</li>
    <li><a href="https://www12.senado.leg.br/dados-abertos/conjuntos?grupo=projetos-e-materias&amp;portal=Legislativo">Senado: catálogo de Projetos e Matérias</a>.</li>
    <li><a href="https://support.microsoft.com/pt-pt/excel/functions/kurt-function">Microsoft: função CURT</a>.</li>
    <li><a href="https://fbaum.unc.edu/articles/Comp_friction/PE_in_Comparative_Perspective_AJPS_Identified.pdf">Baumgartner e colaboradores: Punctuated Equilibrium in Comparative Perspective</a>.</li>
    <li><a href="https://doi.org/10.1017/pan.2021.25">Kaplaner e Steinebach: limites da curtose e L-curtose na PET</a>.</li>
</ul>
"""


def create_help_widget(parent=None) -> QWidget:
    """Build the same Portuguese guide for an embedded tab or the F1 dialog."""
    browser = QTextBrowser(parent)
    browser.setObjectName("usageGuide")
    browser.setOpenExternalLinks(True)
    browser.setHtml(HELP_HTML)
    browser.setStyleSheet("""
        QTextBrowser {
            background-color: #1e1e2e;
            color: #cdd6f4;
            border: 1px solid #313244;
            border-radius: 8px;
            padding: 16px;
            font-size: 11pt;
        }
        QScrollBar:vertical {
            background: #181825;
            width: 12px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background: #45475a;
            border-radius: 6px;
            min-height: 30px;
        }
    """)
    return browser


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Como usar — Contador de Palavras")
        self.resize(900, 740)
        self.setStyleSheet("QDialog { background-color: #1e1e2e; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(create_help_widget(self))

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton("Fechar")
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #cba6f7;
                color: #1e1e2e;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-weight: 600;
                min-width: 100px;
            }
            QPushButton:hover { background-color: #b4befe; }
        """)
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)
