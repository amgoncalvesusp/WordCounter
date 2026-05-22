"""In-app help dialog."""
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QPushButton, QTextBrowser, QVBoxLayout


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

<p>Software para contagem padronizada e auditável de palavras em PDFs. Desenvolvido para pesquisa acadêmica em políticas públicas, com suporte específico a Mensagens Presidenciais ao Congresso Nacional.</p>

<h2>Fluxo básico de uso</h2>
<ol>
    <li><b>Adicionar PDFs</b> — Arraste arquivos para a área pontilhada ou clique em <code>Adicionar Arquivos</code>.</li>
    <li><b>(Opcional) Definir termos de busca</b> — Digite termos no campo de busca, um por linha.</li>
    <li><b>(Opcional) Marcar OCR</b> — Ative se algum PDF for escaneado (apenas imagem).</li>
    <li><b>Processar</b> — Clique em <code>▶ Processar PDFs</code>. O progresso aparece na barra inferior.</li>
    <li><b>Exportar</b> — Após conclusão, clique em <code>⬇ Exportar XLSX</code>.</li>
</ol>

<h2>Busca de termos e expressões</h2>

<p>Permite contar quantas vezes cada palavra ou expressão aparece em cada documento, tanto no PDF completo quanto no corpus analítico.</p>

<h3>Regras de sintaxe</h3>
<ul>
    <li><b>Palavra simples:</b> <code>clima</code> — conta todas as ocorrências da palavra, ignorando acentos e maiúsculas/minúsculas.</li>
    <li><b>Expressão sem aspas:</b> <code>mudança do clima</code> — busca a sequência permitindo espaços variáveis entre palavras.</li>
    <li><b>Expressão com aspas (busca exata):</b> <code>"efeito estufa"</code> — exige correspondência literal da expressão entre limites de palavra.</li>
    <li><b>Linha em branco</b> ou iniciada com <code>#</code> — ignorada (comentário).</li>
</ul>

<h3>Exemplo de entrada</h3>
<pre># Termos relacionados a mitigação
carbono
desmatamento
"efeito estufa"
"mudança do clima"
mitigação

# Termos relacionados a adaptação
adaptação
resiliência
"perdas e danos"</pre>

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

<h2>Estrutura do XLSX exportado</h2>

<h3>Aba 1: Contagem de Palavras</h3>
<p>Linha por documento. Colunas: identificação, metadados detectados, contagens, grau de confiança, observações. Se termos de busca foram definidos, duas colunas por termo (PDF Completo / Corpus Analítico).</p>

<h3>Aba 2: Páginas Excluídas</h3>
<p>Lista detalhada de cada página excluída do corpus analítico, com motivo da exclusão e número de palavras na página.</p>

<h2>Atalhos</h2>
<ul>
    <li><span class="key">Ctrl+O</span> — Adicionar arquivos</li>
    <li><span class="key">Ctrl+E</span> — Exportar XLSX</li>
    <li><span class="key">Ctrl+Q</span> — Sair</li>
    <li><span class="key">F1</span> — Esta tela de ajuda</li>
</ul>

<h2>Reprodutibilidade</h2>
<p>Toda a contagem segue regras determinísticas. Processar os mesmos PDFs nas mesmas condições produz exatamente os mesmos resultados. Diferenças entre execuções só ocorrem se houver OCR sobre páginas marginais (qualidade de imagem pode variar a saída).</p>
"""


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Como usar — Contador de Palavras")
        self.resize(900, 740)
        self.setStyleSheet("QDialog { background-color: #1e1e2e; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        browser = QTextBrowser()
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
        layout.addWidget(browser)

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
