import customtkinter as ctk
import json
import os
import sys
import re
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer, TextLexer
from pygments.formatters import TerminalFormatter
from pygments.util import ClassNotFound
import markdown
from html.parser import HTMLParser

def get_base_dir():
    if getattr(sys, 'frozen', False):
        # Se estiver rodando como executável
        return os.path.dirname(sys.executable)
    else:
        # Se estiver rodando como script
        return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()
DATA_FILE = os.path.join(BASE_DIR, 'data.json')
WINDOW_CONFIG_FILE = os.path.join(BASE_DIR, 'window_config.json')

def salvar_config_janela(janela):
    config = {
        'geometry': janela.geometry()
    }
    with open(WINDOW_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f)

def carregar_config_janela(janela):
    if os.path.exists(WINDOW_CONFIG_FILE):
        try:
            with open(WINDOW_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                janela.geometry(config['geometry'])
        except:
            pass

estado = 'inicio'
dados = {}
resultados = []
programa_selecionado = None
sub_estado = None
entrada_buffer = ''
nota_em_edicao = None  # Rastreia nota sendo editada (índice e texto original)
atalho_em_edicao = None  # Rastreia atalho sendo editado
snippet_em_edicao = None  # Rastreia snippet sendo editado

root = ctk.CTk()
root.title("KeyBase")
root.iconbitmap("keybase.ico")

# Carregar a posição e tamanho salvos da janela
carregar_config_janela(root)

# Definir fonte monoespaçada para a saída
try:
    fonte_saida = ctk.CTkFont(family="Roboto Mono", size=14)
except:
    fonte_saida = ctk.CTkFont(family="Consolas", size=14)

entrada = ctk.CTkEntry(root, width=800, font=("Consolas", 12))
entrada.pack(pady=10)

# Área de ajuda/status (3 linhas) - OCULTA POR PADRÃO
ajuda = ctk.CTkTextbox(root, width=800, height=60, font=("Consolas", 12), fg_color="#1a1a1a")
# Não fazer pack() aqui - será mostrada apenas ao editar

# Área principal de conteúdo
saida = ctk.CTkTextbox(root, width=800, height=500, font=("Consolas", 14))
saida.pack(pady=5, fill="both", expand=True)

def escrever_saida(texto):
    saida.insert("end", texto + "\n")
    saida.see("end")

def limpar_saida():
    saida.delete("1.0", "end")

def escrever_ajuda(texto):
    """Escreve mensagem na área de ajuda e a torna visível"""
    ajuda.delete("1.0", "end")
    ajuda.insert("1.0", texto)
    # Mostrar área de ajuda (inserir entre entrada e saída)
    ajuda.pack(after=entrada, pady=5, fill="x")

def limpar_ajuda():
    """Limpa e oculta a área de ajuda"""
    ajuda.delete("1.0", "end")
    ajuda.pack_forget()  # Ocultar área de ajuda

def aplicar_syntax_highlighting(codigo, linguagem="python"):
    """
    Aplica syntax highlighting ao código usando Pygments
    """
    try:
        # Tentar obter o lexer pela linguagem especificada
        if linguagem and linguagem.lower() != "text":
            try:
                lexer = get_lexer_by_name(linguagem.lower(), stripall=True)
            except ClassNotFound:
                # Se não encontrar, tenta adivinhar
                lexer = guess_lexer(codigo)
        else:
            lexer = TextLexer()
        
        # Mapeamento de cores para tema escuro (compatível com CustomTkinter)
        cores = {
            'Keyword': '#569CD6',           # Azul (def, class, if, for, etc)
            'Name.Function': '#DCDCAA',     # Amarelo claro (nomes de funções)
            'Name.Class': '#4EC9B0',        # Verde água (nomes de classes)
            'String': '#CE9178',            # Laranja claro (strings)
            'Number': '#B5CEA8',            # Verde claro (números)
            'Comment': '#6A9955',           # Verde escuro (comentários)
            'Operator': '#D4D4D4',          # Branco (operadores)
            'Name.Builtin': '#4EC9B0',      # Verde água (print, len, etc)
            'Name': '#9CDCFE',              # Azul claro (variáveis)
        }
        
        # Limpar e preparar textbox
        saida.delete("1.0", "end")
        
        # Configurar tags de cores
        for token_type, cor in cores.items():
            saida.tag_config(token_type, foreground=cor)
        
        # Processar tokens e inserir com cores
        from pygments import lex
        for token_type, value in lex(codigo, lexer):
            token_name = str(token_type).split('.')[-1]
            full_token = str(token_type)
            
            # Tentar usar o token completo primeiro, depois o simplificado
            if full_token in cores:
                saida.insert("end", value, full_token)
            elif token_name in cores:
                saida.insert("end", value, token_name)
            else:
                saida.insert("end", value)
        
        saida.see("1.0")
        
    except Exception as e:
        # Em caso de erro, mostrar código sem formatação
        saida.delete("1.0", "end")
        saida.insert("end", codigo)
        saida.see("1.0")

class HTMLToTkinterParser(HTMLParser):
    """
    Converte HTML simples (gerado pelo markdown) em texto formatado para CTkTextbox
    usando tags do Tkinter
    """
    def __init__(self, textbox):
        super().__init__()
        self.textbox = textbox
        self.tag_stack = []
        self.list_level = 0
        self.in_code_block = False
        self.code_block_content = []  # Armazena conteúdo do bloco de código
        self.code_block_language = None  # Linguagem do bloco de código
        
    def handle_starttag(self, tag, attrs):
        """Processa tags de abertura HTML"""
        if tag in ['h1', 'h2', 'h3']:
            self.tag_stack.append(tag)
        elif tag == 'strong' or tag == 'b':
            self.tag_stack.append('bold')
        elif tag == 'em' or tag == 'i':
            self.tag_stack.append('italic')
        elif tag == 'code':
            # Verificar se é código inline ou bloco
            # Blocos de código vêm dentro de <pre><code>
            if not self.in_code_block:
                self.tag_stack.append('code')
            else:
                # Extrair linguagem se especificada (class="language-python")
                for attr_name, attr_value in attrs:
                    if attr_name == 'class' and attr_value.startswith('language-'):
                        self.code_block_language = attr_value.replace('language-', '')
        elif tag == 'pre':
            self.in_code_block = True
            self.code_block_content = []
            self.code_block_language = None
        elif tag in ['ul', 'ol']:
            self.list_level += 1
        elif tag == 'li':
            indent = "  " * (self.list_level - 1)
            self.textbox.insert("end", f"{indent}• ", 'list')
            
    def handle_endtag(self, tag):
        """Processa tags de fechamento HTML"""
        if tag in ['h1', 'h2', 'h3']:
            if self.tag_stack and self.tag_stack[-1] in ['h1', 'h2', 'h3']:
                self.tag_stack.pop()
            self.textbox.insert("end", "\n")
        elif tag in ['strong', 'b']:
            if self.tag_stack and self.tag_stack[-1] == 'bold':
                self.tag_stack.pop()
        elif tag in ['em', 'i']:
            if self.tag_stack and self.tag_stack[-1] == 'italic':
                self.tag_stack.pop()
        elif tag == 'code':
            if self.tag_stack and self.tag_stack[-1] == 'code':
                self.tag_stack.pop()
        elif tag == 'pre':
            # Fim do bloco de código - aplicar syntax highlighting
            self.in_code_block = False
            codigo = ''.join(self.code_block_content)
            
            if codigo.strip():
                self._aplicar_syntax_highlighting_bloco(codigo, self.code_block_language)
            
            self.textbox.insert("end", "\n")
            self.code_block_content = []
            self.code_block_language = None
        elif tag in ['ul', 'ol']:
            self.list_level -= 1
        elif tag == 'li':
            self.textbox.insert("end", "\n")
        elif tag == 'p':
            self.textbox.insert("end", "\n")
    
    def _aplicar_syntax_highlighting_bloco(self, codigo, linguagem):
        """Aplica syntax highlighting a um bloco de código"""
        try:
            from pygments import lex
            from pygments.lexers import get_lexer_by_name, TextLexer
            from pygments.util import ClassNotFound
            
            # Tentar obter lexer pela linguagem
            if linguagem:
                try:
                    lexer = get_lexer_by_name(linguagem.lower(), stripall=True)
                except ClassNotFound:
                    lexer = TextLexer()
            else:
                lexer = TextLexer()
            
            # Cores para syntax highlighting (mesmas dos snippets)
            cores = {
                'Keyword': '#569CD6',
                'Name.Function': '#DCDCAA',
                'Name.Class': '#4EC9B0',
                'String': '#CE9178',
                'Number': '#B5CEA8',
                'Comment': '#6A9955',
                'Operator': '#D4D4D4',
                'Name.Builtin': '#4EC9B0',
                'Name': '#9CDCFE',
            }
            
            # Configurar tags de cores
            for token_type, cor in cores.items():
                self.textbox.tag_config(token_type, foreground=cor, background="#2D2D2D")
            
            # Processar tokens e inserir com cores
            for token_type, value in lex(codigo, lexer):
                token_name = str(token_type).split('.')[-1]
                full_token = str(token_type)
                
                # Tentar usar o token completo primeiro, depois o simplificado
                if full_token in cores:
                    self.textbox.insert("end", value, full_token)
                elif token_name in cores:
                    self.textbox.insert("end", value, token_name)
                else:
                    # Texto sem cor específica, mas com fundo escuro
                    self.textbox.insert("end", value, 'code_block')
        except Exception as e:
            # Em caso de erro, inserir código sem formatação
            self.textbox.insert("end", codigo, 'code_block')
            
    def handle_data(self, data):
        """Processa o conteúdo de texto"""
        if self.in_code_block:
            # Armazenar conteúdo do bloco de código
            self.code_block_content.append(data)
        elif data.strip():  # Ignorar espaços em branco vazios
            # Aplicar todas as tags ativas
            if self.tag_stack:
                self.textbox.insert("end", data, tuple(self.tag_stack))
            else:
                self.textbox.insert("end", data)

def configurar_tags_markdown():
    """
    Configura tags de formatação Markdown no CTkTextbox
    Nota: Não podemos usar 'font' nas tags devido ao scaling do CustomTkinter
    """
    # Cabeçalhos - apenas cores (tamanho não pode ser alterado)
    saida.tag_config("h1", foreground="#569CD6", spacing1=10, spacing3=5)
    saida.tag_config("h2", foreground="#4EC9B0", spacing1=8, spacing3=4)
    saida.tag_config("h3", foreground="#DCDCAA", spacing1=6, spacing3=3)
    
    # Formatação de texto - CustomTkinter não suporta bold/italic em tags
    # Vamos usar apenas cores diferentes para destacar
    saida.tag_config("bold", foreground="#FFFFFF")  # Branco mais forte
    saida.tag_config("italic", foreground="#B4B4B4")  # Cinza claro
    saida.tag_config("code", background="#2D2D2D", foreground="#CE9178")
    saida.tag_config("code_block", background="#2D2D2D", foreground="#CE9178")
    
    # Listas
    saida.tag_config("list", lmargin1=20, lmargin2=40)

def aplicar_markdown_formatacao(texto):
    """
    Aplica formatação Markdown ao texto usando tags do CTkTextbox
    Similar ao aplicar_syntax_highlighting mas para Markdown
    """
    try:
        # Limpar saída
        saida.delete("1.0", "end")
        
        # Configurar tags de formatação
        configurar_tags_markdown()
        
        # Converter Markdown para HTML (com suporte a fenced code blocks)
        html = markdown.markdown(texto, extensions=['fenced_code'])
        
        # Parsear HTML e aplicar formatação
        parser = HTMLToTkinterParser(saida)
        parser.feed(html)
        
        saida.see("1.0")
        
    except Exception as e:
        # Em caso de erro, mostrar texto sem formatação + erro
        saida.delete("1.0", "end")
        saida.insert("end", f"[ERRO AO RENDERIZAR MARKDOWN: {str(e)}]\n\n")
        saida.insert("end", texto)
        saida.see("1.0")
        print(f"Erro ao renderizar Markdown: {e}")  # Debug no console


def carregar_dados():
    dados = {"programas": []}
    if not os.path.exists(DATA_FILE):
        return dados
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        try:
            dados = json.load(f)
            if 'programas' not in dados:
                dados['programas'] = []
            for programa in dados['programas']:
                programa.setdefault('atalhos', [])
                programa.setdefault('notas', [])
                programa.setdefault('snippets', [])
                # Converter notas antigas para o novo formato
                notas_convertidas = []
                for nota in programa['notas']:
                    if isinstance(nota, str):
                        notas_convertidas.append({
                            "descricao": nota[:50] + "..." if len(nota) > 50 else nota,
                            "texto": nota
                        })
                    else:
                        notas_convertidas.append(nota)
                programa['notas'] = notas_convertidas
                
                # Adicionar campo 'linguagem' aos snippets que não possuem
                for snippet in programa['snippets']:
                    if 'linguagem' not in snippet:
                        snippet['linguagem'] = 'python'  # Padrão para snippets antigos
            return dados
        except json.JSONDecodeError:
            return {"programas": []}

def salvar_dados():
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

    escrever_saida("Dados salvos com sucesso!")

def buscar_programas(termo):
    termo = termo.lower()
    return [p for p in dados['programas'] if termo in p['nome'].lower()]

def exibir_programas(lista):
    for idx, prog in enumerate(lista):
        # Contar total de itens (atalhos + notas + snippets)
        total_itens = len(prog.get('atalhos', [])) + len(prog.get('notas', [])) + len(prog.get('snippets', []))
        
        # Formatar a saída com o total
        contador = f"[{total_itens} itens]" if total_itens > 0 else ""
        escrever_saida(f"{idx + 1} - {prog['nome']}: {prog['descricao']} {contador}".strip())

def exibir_menu_programa():
    limpar_saida()
    
    # Contar itens do programa selecionado
    num_atalhos = len(programa_selecionado.get('atalhos', []))
    num_notas = len(programa_selecionado.get('notas', []))
    num_snippets = len(programa_selecionado.get('snippets', []))
    
    escrever_saida("========================")
    escrever_saida(f"1 - Ver atalhos [{num_atalhos}]")
    escrever_saida(f"2 - Ver notas [{num_notas}]")
    escrever_saida(f"3 - Ver snippets [{num_snippets}]")
    escrever_saida("========================")
    escrever_saida("4 - Adicionar")
    escrever_saida("5 - Editar")
    escrever_saida("6 - Deletar")
    escrever_saida("========================")
    escrever_saida("7 - Editar nome do programa")
    escrever_saida("8 - Editar descrição")
    escrever_saida("9 - Deletar programa")
    escrever_saida("========================")
    escrever_saida("Pressione ENTER para voltar")
    escrever_saida("========================")

def ver_atalhos():
    global estado, sub_estado
    limpar_saida()
    if not programa_selecionado['atalhos']:
        escrever_saida("Nenhum atalho cadastrado. Aperte C para cadastrar ou Enter para voltar.")
        sub_estado = 'atalho_vazio'
    else:
        escrever_saida("Digite o número do atalho para ver detalhes ou ENTER para voltar.")
        for idx, atalho in enumerate(programa_selecionado['atalhos']):
            # Pegar apenas a primeira linha da descrição
            primeira_linha = atalho['descricao'].split('\n')[0]
            preview = primeira_linha[:50] + "..." if len(primeira_linha) > 50 else primeira_linha
            escrever_saida(f"{idx + 1} - {atalho['combinacao']}: {preview}")
        sub_estado = 'atalho_existente'

def ver_notas():
    global estado, sub_estado
    limpar_saida()
    if not programa_selecionado['notas']:
        escrever_saida("Nenhuma nota cadastrada. Aperte C para cadastrar ou Enter para voltar.")
        sub_estado = 'nota_vazio'
    else:
        escrever_saida("Digite o número da nota para ver o texto completo ou ENTER para voltar.")
        for idx, nota in enumerate(programa_selecionado['notas']):
            escrever_saida(f"{idx + 1} - {nota['descricao']}")
        sub_estado = 'nota_existente'

def ver_snippets():
    global estado, sub_estado
    limpar_saida()
    if not programa_selecionado['snippets']:
        escrever_saida("Nenhum snippet cadastrado. Aperte C para cadastrar ou Enter para voltar.")
        sub_estado = 'snippet_vazio'
    else:
        escrever_saida("Digite o número do snippet para ver o código completo ou ENTER para voltar.")
        for idx, snippet in enumerate(programa_selecionado['snippets']):
            escrever_saida(f"{idx + 1} - {snippet['descricao']}")
        sub_estado = 'snippet_existente'

def executar_comando(event=None):
    global estado, dados, resultados, programa_selecionado, sub_estado, entrada_buffer

    comando = entrada.get().strip()
    entrada.delete(0, 'end')
    
    # Não escrever comando se estiver em modo de edição (para não poluir o conteúdo)
    if sub_estado not in ['nota_edicao', 'atalho_edicao', 'snippet_edicao']:
        escrever_saida(f"> {comando}")

    if sub_estado in ['atalho_existente', 'nota_existente', 'snippet_existente']:
        if comando == '':
            exibir_menu_programa()
            sub_estado = None
        elif sub_estado == 'nota_existente' and comando.isdigit():
            idx = int(comando) - 1
            if 0 <= idx < len(programa_selecionado['notas']):
                nota = programa_selecionado['notas'][idx]
                entrada_buffer = idx  # Guardar índice da nota
                
                # Aplicar formatação Markdown
                aplicar_markdown_formatacao(nota['texto'])
                
                # Adicionar cabeçalho com instruções de edição
                saida.insert("1.0", f"Pressione ENTER para voltar ou E para editar.\n\nNota: {nota['descricao']}\n\n")
                saida.see("1.0")
                
                # Mudar para sub-estado de visualização
                sub_estado = 'nota_visualizacao'
            else:
                escrever_saida("Número inválido. Pressione ENTER para voltar.")
        elif sub_estado == 'atalho_existente' and comando.isdigit():
            idx = int(comando) - 1
            if 0 <= idx < len(programa_selecionado['atalhos']):
                atalho = programa_selecionado['atalhos'][idx]
                entrada_buffer = idx  # Guardar índice do atalho
                
                # Criar texto Markdown com o atalho
                descricao = atalho['descricao']
                if '**' not in descricao and '#' not in descricao:
                    texto_markdown = f"# {atalho['combinacao']}\n\n{descricao}\n"
                else:
                    texto_markdown = descricao
                
                # Aplicar formatação Markdown
                aplicar_markdown_formatacao(texto_markdown)
                
                # Adicionar cabeçalho com instruções de edição
                saida.insert("1.0", f"Pressione ENTER para voltar ou E para editar.\n\nAtalho: {atalho['combinacao']}\n\n")
                saida.see("1.0")
                
                # Mudar para sub-estado de visualização
                sub_estado = 'atalho_visualizacao'
            else:
                escrever_saida("Número inválido. Pressione ENTER para voltar.")
        elif sub_estado == 'snippet_existente' and comando.isdigit():
            idx = int(comando) - 1
            if 0 <= idx < len(programa_selecionado['snippets']):
                snippet = programa_selecionado['snippets'][idx]
                entrada_buffer = idx  # Guardar índice do snippet
                
                # Obter linguagem do snippet (se existir)
                linguagem = snippet.get('linguagem', 'python')
                
                # Se a linguagem for markdown, renderizar o código como markdown puro
                if linguagem == 'markdown':
                    # Renderizar código diretamente como markdown
                    aplicar_markdown_formatacao(snippet['codigo'])
                else:
                    # Criar texto Markdown com snippet
                    # Se a descrição já tiver Markdown, usar como está
                    # Senão, criar estrutura básica
                    descricao = snippet['descricao']
                    
                    if '```' in snippet['codigo']:
                        # Código já tem blocos Markdown - usar como está
                        texto_markdown = f"# {descricao}\n\n{snippet['codigo']}\n"
                    else:
                        # Código simples - envolver em bloco de código
                        texto_markdown = f"# {descricao}\n\n```{linguagem}\n{snippet['codigo']}\n```\n"
                    
                    # Aplicar formatação Markdown (que já inclui syntax highlighting)
                    aplicar_markdown_formatacao(texto_markdown)
                
                # Adicionar cabeçalho com instruções de edição
                saida.insert("1.0", f"Pressione ENTER para voltar ou E para editar.\n\n")
                saida.see("1.0")
                
                # Mudar para sub-estado de visualização
                sub_estado = 'snippet_visualizacao'
            else:
                escrever_saida("Número inválido. Pressione ENTER para voltar.")
        else:
            escrever_saida("Pressione apenas ENTER para voltar ou digite um número válido.")
        return

    # Tratamento para visualização de nota com opção de editar
    if sub_estado == 'nota_visualizacao':
        if comando == '':
            # Voltar para lista de notas
            ver_notas()
        elif comando.upper() == 'E':
            # Entrar em modo de edição
            global nota_em_edicao
            idx = entrada_buffer
            nota = programa_selecionado['notas'][idx]
            
            limpar_saida()
            limpar_ajuda()
            
            # Mensagens de ajuda na área separada
            escrever_ajuda(f"Editando Nota: {nota['descricao']} \nPressione Ctrl+S para salvar ou Esc para cancelar.")
            
            # Conteúdo editável na área principal
            saida.insert("end", nota['texto'])
            
            # Mudar para modo de edição
            sub_estado = 'nota_edicao'
            nota_em_edicao = {'idx': idx, 'texto_original': nota['texto']}
            
            # Mover foco para o textbox de edição
            saida.focus_set()
        else:
            escrever_saida("Comando inválido. Pressione ENTER para voltar ou E para editar.")
        return

    # Tratamento para edição de nota
    if sub_estado == 'nota_edicao':
        if comando.lower() == 'salvar' or comando == 'CTRL_S':
            # Pegar texto editado do textbox
            texto_editado = saida.get("1.0", "end-1c")
            
            # Remover "CTRL_S" se estiver no final
            if texto_editado.strip().endswith('CTRL_S'):
                texto_editado = texto_editado.rsplit('CTRL_S', 1)[0].rstrip()
            
            # Salvar no banco de dados
            idx = nota_em_edicao['idx']
            programa_selecionado['notas'][idx]['texto'] = texto_editado
            salvar_dados()
            
            # Voltar para visualização
            nota = programa_selecionado['notas'][idx]
            aplicar_markdown_formatacao(nota['texto'])
            saida.insert("1.0", f"Pressione ENTER para voltar ou E para editar.\n\nNota: {nota['descricao']}\n\n[Nota salva com sucesso!]\n\n")
            saida.see("1.0")
            
            sub_estado = 'nota_visualizacao'
            nota_em_edicao = None
            entrada.focus_set()  # Voltar foco para campo de entrada
            limpar_ajuda()  # Ocultar área de ajuda
        elif comando.lower() == 'cancelar' or comando == 'ESC':
            # Cancelar edição
            idx = nota_em_edicao['idx']
            nota = programa_selecionado['notas'][idx]
            
            # Voltar para visualização
            aplicar_markdown_formatacao(nota['texto'])
            saida.insert("1.0", f"Pressione ENTER para voltar ou E para editar.\n\nNota: {nota['descricao']}\n\n[Edição cancelada]\n\n")
            saida.see("1.0")
            
            sub_estado = 'nota_visualizacao'
            nota_em_edicao = None
            limpar_ajuda()  # Ocultar área de ajuda
            entrada.focus_set()  # Voltar foco para campo de entrada
        else:
            escrever_saida("\nPressione Ctrl+S para salvar ou Esc para cancelar.")
        return

    # Tratamento para visualização de atalho com opção de editar
    if sub_estado == 'atalho_visualizacao':
        if comando == '':
            # Voltar para lista de atalhos
            ver_atalhos()
        elif comando.upper() == 'E':
            # Entrar em modo de edição
            global atalho_em_edicao
            idx = entrada_buffer
            atalho = programa_selecionado['atalhos'][idx]
            
            limpar_saida()
            limpar_ajuda()
            
            # Mensagens de ajuda na área separada
            escrever_ajuda(f"Editando Atalho: {atalho['combinacao']} \nPressione Ctrl+S para salvar ou Esc para cancelar.")
            
            # Conteúdo editável na área principal
            saida.insert("end", atalho['descricao'])
            
            # Mudar para modo de edição
            sub_estado = 'atalho_edicao'
            atalho_em_edicao = {'idx': idx, 'descricao_original': atalho['descricao']}
            
            # Mover foco para o textbox de edição
            saida.focus_set()
        else:
            escrever_saida("Comando inválido. Pressione ENTER para voltar ou E para editar.")
        return

    # Tratamento para edição de atalho
    if sub_estado == 'atalho_edicao':
        if comando.lower() == 'salvar' or comando == 'CTRL_S':
            # Pegar texto editado do textbox
            texto_editado = saida.get("1.0", "end-1c")
            
            # Remover "CTRL_S" se estiver no final
            if texto_editado.strip().endswith('CTRL_S'):
                texto_editado = texto_editado.rsplit('CTRL_S', 1)[0].rstrip()
            
            # Salvar no banco de dados
            idx = atalho_em_edicao['idx']
            programa_selecionado['atalhos'][idx]['descricao'] = texto_editado
            salvar_dados()
            
            # Voltar para visualização
            atalho = programa_selecionado['atalhos'][idx]
            descricao = atalho['descricao']
            if '**' not in descricao and '#' not in descricao:
                texto_markdown = f"# {atalho['combinacao']}\n\n{descricao}\n"
            else:
                texto_markdown = descricao
            aplicar_markdown_formatacao(texto_markdown)
            saida.insert("1.0", f"Pressione ENTER para voltar ou E para editar.\n\nAtalho: {atalho['combinacao']}\n\n[Atalho salvo com sucesso!]\n\n")
            saida.see("1.0")
            
            sub_estado = 'atalho_visualizacao'
            atalho_em_edicao = None
            entrada.focus_set()  # Voltar foco para campo de entrada
            limpar_ajuda()  # Ocultar área de ajuda
        elif comando.lower() == 'cancelar' or comando == 'ESC':
            # Cancelar edição
            idx = atalho_em_edicao['idx']
            atalho = programa_selecionado['atalhos'][idx]
            
            # Voltar para visualização
            descricao = atalho['descricao']
            if '**' not in descricao and '#' not in descricao:
                texto_markdown = f"# {atalho['combinacao']}\n\n{descricao}\n"
            else:
                texto_markdown = descricao
            aplicar_markdown_formatacao(texto_markdown)
            saida.insert("1.0", f"Pressione ENTER para voltar ou E para editar.\n\nAtalho: {atalho['combinacao']}\n\n[Edição cancelada]\n\n")
            saida.see("1.0")
            
            sub_estado = 'atalho_visualizacao'
            atalho_em_edicao = None
            limpar_ajuda()  # Ocultar área de ajuda
            entrada.focus_set()  # Voltar foco para campo de entrada
        else:
            escrever_saida("\nPressione Ctrl+S para salvar ou Esc para cancelar.")
        return

    # Tratamento para visualização de snippet com opção de editar
    if sub_estado == 'snippet_visualizacao':
        if comando == '':
            # Voltar para lista de snippets
            ver_snippets()
        elif comando.upper() == 'E':
            # Entrar em modo de edição
            global snippet_em_edicao
            idx = entrada_buffer
            snippet = programa_selecionado['snippets'][idx]
            
            limpar_saida()
            limpar_ajuda()
            
            # Mensagens de ajuda na área separada
            escrever_ajuda(f"Editando Snippet: {snippet['descricao']} \nPressione Ctrl+S para salvar ou Esc para cancelar.")
            
            # Conteúdo editável na área principal
            saida.insert("end", snippet['codigo'])
            
            # Mudar para modo de edição
            sub_estado = 'snippet_edicao'
            snippet_em_edicao = {'idx': idx, 'codigo_original': snippet['codigo']}
            
            # Mover foco para o textbox de edição
            saida.focus_set()
        else:
            escrever_saida("Comando inválido. Pressione ENTER para voltar ou E para editar.")
        return

    # Tratamento para edição de snippet
    if sub_estado == 'snippet_edicao':
        if comando.lower() == 'salvar' or comando == 'CTRL_S':
            # Pegar texto editado do textbox
            texto_editado = saida.get("1.0", "end-1c")
            
            # Remover "CTRL_S" se estiver no final
            if texto_editado.strip().endswith('CTRL_S'):
                texto_editado = texto_editado.rsplit('CTRL_S', 1)[0].rstrip()
            
            # Salvar no banco de dados
            idx = snippet_em_edicao['idx']
            programa_selecionado['snippets'][idx]['codigo'] = texto_editado
            salvar_dados()
            
            # Voltar para visualização
            snippet = programa_selecionado['snippets'][idx]
            linguagem = snippet.get('linguagem', 'python')
            descricao = snippet['descricao']
            
            if '```' in snippet['codigo']:
                texto_markdown = f"# {descricao}\n\n{snippet['codigo']}\n"
            else:
                texto_markdown = f"# {descricao}\n\n```{linguagem}\n{snippet['codigo']}\n```\n"
            
            aplicar_markdown_formatacao(texto_markdown)
            saida.insert("1.0", f"Pressione ENTER para voltar ou E para editar.\n\n[Snippet salvo com sucesso!]\n\n")
            saida.see("1.0")
            
            sub_estado = 'snippet_visualizacao'
            snippet_em_edicao = None
            entrada.focus_set()  # Voltar foco para campo de entrada
            limpar_ajuda()  # Ocultar área de ajuda
        elif comando.lower() == 'cancelar' or comando == 'ESC':
            # Cancelar edição
            idx = snippet_em_edicao['idx']
            snippet = programa_selecionado['snippets'][idx]
            
            # Voltar para visualização
            linguagem = snippet.get('linguagem', 'python')
            descricao = snippet['descricao']
            
            if '```' in snippet['codigo']:
                texto_markdown = f"# {descricao}\n\n{snippet['codigo']}\n"
            else:
                texto_markdown = f"# {descricao}\n\n```{linguagem}\n{snippet['codigo']}\n```\n"
            
            aplicar_markdown_formatacao(texto_markdown)
            saida.insert("1.0", f"Pressione ENTER para voltar ou E para editar.\n\n[Edição cancelada]\n\n")
            saida.see("1.0")
            
            sub_estado = 'snippet_visualizacao'
            snippet_em_edicao = None
            limpar_ajuda()  # Ocultar área de ajuda
            entrada.focus_set()  # Voltar foco para campo de entrada
        else:
            escrever_saida("\nPressione Ctrl+S para salvar ou Esc para cancelar.")
        return

    if comando.lower() == 'sair':
        salvar_config_janela(root)
        root.destroy()
        return

    if sub_estado in ['atalho_vazio', 'nota_vazio', 'snippet_vazio']:
        if comando.upper() == 'C':
            if sub_estado == 'atalho_vazio':
                limpar_saida()
                escrever_saida("Digite a combinação do atalho:")
                estado = 'cadastrar_atalho_comb'
            elif sub_estado == 'nota_vazio':
                limpar_saida()
                escrever_saida("Digite a descrição da nota:")
                estado = 'cadastrar_nota_desc'
            else:  # snippet_vazio
                limpar_saida()
                escrever_saida("Digite a descrição do snippet:")
                estado = 'cadastrar_snippet_desc'
            sub_estado = None
            return
        elif comando == '':
            exibir_menu_programa()
            sub_estado = None
            return
        else:
            escrever_saida("Opção inválida. Aperte C para cadastrar ou Enter para voltar.")
            return

    # ======== Estados =========

    if estado == 'inicio':
        if comando == '':
            limpar_saida()
            resultados = dados['programas']
            if resultados:
                exibir_programas(resultados)
                escrever_saida("\nDigite o número do programa para selecionar ou C para cadastrar")
            else:
                escrever_saida("Nenhum programa cadastrado.")
                escrever_saida("Digite C para cadastrar um novo programa")
        elif comando.upper() == 'C':
            limpar_saida()
            escrever_saida("Digite o nome do novo programa:")
            estado = 'adicionar_nome'
        elif comando.isdigit():
            idx = int(comando) - 1
            if 0 <= idx < len(dados['programas']):
                programa_selecionado = dados['programas'][idx]
                exibir_menu_programa()
                estado = 'menu_programa'
            else:
                escrever_saida("Número inválido.")
        else:
            resultados = buscar_programas(comando)
            limpar_saida()
            if resultados:
                exibir_programas(resultados)
                escrever_saida("\nDigite o número do programa para selecionar ou C para cadastrar")
            else:
                escrever_saida("Nenhum programa encontrado.")
                escrever_saida("Digite C para cadastrar um novo programa")

    elif estado == 'confirmar_cadastro':
        if comando.upper() == 'S':
            escrever_saida("Digite o nome do novo programa:")
            estado = 'adicionar_nome'
        else:
            estado = 'inicio'

    elif estado == 'adicionar_nome':
        entrada_buffer = comando
        escrever_saida("Digite uma descrição para o programa:")
        estado = 'adicionar_descricao'

    elif estado == 'adicionar_descricao':
        novo_programa = {
            "nome": entrada_buffer,
            "descricao": comando,
            "atalhos": [],
            "notas": [],
            "snippets": []
        }
        dados['programas'].append(novo_programa)
        salvar_dados()
        escrever_saida(f"Programa '{entrada_buffer}' adicionado com sucesso!")
        estado = 'inicio'

    elif estado == 'selecionar_programa':
        if comando.isdigit():
            idx = int(comando) - 1
            if 0 <= idx < len(resultados):
                programa_selecionado = resultados[idx]
                exibir_menu_programa()
                estado = 'menu_programa'
            else:
                escrever_saida("Número inválido.")
                estado = 'inicio'
        else:
            escrever_saida("Entrada inválida.")
            estado = 'inicio'

    elif estado == 'menu_programa':
        if comando == '':
            limpar_saida()
            escrever_saida("Comece a digitar o nome do programa ou 'sair' para encerrar.")
            estado = 'inicio'
        elif comando == '1':
            ver_atalhos()
        elif comando == '2':
            ver_notas()
        elif comando == '3':
            ver_snippets()
        elif comando == '4':
            limpar_saida()
            escrever_saida("O que deseja adicionar?")
            escrever_saida("1 - Atalho")
            escrever_saida("2 - Nota")
            escrever_saida("3 - Snippet")
            escrever_saida("\nPressione ENTER para voltar")
            estado = 'cadastrar_item'
        elif comando == '5':
            limpar_saida()
            escrever_saida("O que deseja editar?")
            escrever_saida("1 - Atalho")
            escrever_saida("2 - Nota")
            escrever_saida("3 - Snippet")
            escrever_saida("\nPressione ENTER para voltar")
            estado = 'editar_item'
        elif comando == '6':
            limpar_saida()
            escrever_saida("O que deseja deletar?")
            escrever_saida("1 - Atalho")
            escrever_saida("2 - Nota")
            escrever_saida("3 - Snippet")
            escrever_saida("\nPressione ENTER para voltar")
            estado = 'deletar_item'
        elif comando == '7':
            limpar_saida()
            escrever_saida(f"Nome atual do programa: {programa_selecionado['nome']}")
            escrever_saida("\nDigite o novo nome do programa ou tecle ENTER para voltar:")
            estado = 'editar_nome_programa'
        elif comando == '8':
            limpar_saida()
            escrever_saida(f"Descrição atual do programa: {programa_selecionado['descricao']}")
            escrever_saida("\nDigite a nova descrição do programa ou tecle ENTER para voltar:")
            estado = 'editar_descricao_programa'
        elif comando == '9':
            limpar_saida()
            escrever_saida(f"Deseja apagar o programa '{programa_selecionado['nome']}'?")
            escrever_saida("Todos os atalhos, notas e snippets serão apagados!")
            escrever_saida("\nDigite 'S' para confirmar ou tecle ENTER para voltar:")
            estado = 'deletar_programa'
        else:
            escrever_saida("Opção inválida.")

    elif estado == 'editar_item':
        if comando == '':
            exibir_menu_programa()
            estado = 'menu_programa'
        elif comando == '1':
            limpar_saida()
            for idx, atalho in enumerate(programa_selecionado['atalhos']):
                escrever_saida(f"{idx + 1} - {atalho['combinacao']}: {atalho['descricao']}")
            escrever_saida("\nDigite o número do atalho que deseja editar ou tecle ENTER para voltar:")
            estado = 'editar_atalho_num'
        elif comando == '2':
            limpar_saida()
            for idx, nota in enumerate(programa_selecionado['notas']):
                escrever_saida(f"{idx + 1} - {nota['descricao']}")
            escrever_saida("\nDigite o número da nota que deseja editar ou tecle ENTER para voltar:")
            estado = 'editar_nota_num'
        elif comando == '3':
            limpar_saida()
            for idx, snippet in enumerate(programa_selecionado['snippets']):
                escrever_saida(f"{idx + 1} - {snippet['descricao']}")
            escrever_saida("\nDigite o número do snippet que deseja editar ou tecle ENTER para voltar:")
            estado = 'editar_snippet_num'
        else:
            escrever_saida("Opção inválida.")

    elif estado == 'editar_atalho_num':
        if comando == '':
            exibir_menu_programa()
            estado = 'menu_programa'
            return
        if comando.isdigit():
            entrada_buffer = int(comando) - 1
            if 0 <= entrada_buffer < len(programa_selecionado['atalhos']):
                limpar_saida()
                atalho = programa_selecionado['atalhos'][entrada_buffer]
                escrever_saida(f"Digite a nova combinação do atalho ou ENTER para manter '{atalho['combinacao']}':")
                estado = 'editar_atalho_comb'
            else:
                escrever_saida("Número inválido.")
                estado = 'menu_programa'
        else:
            escrever_saida("Entrada inválida.")
            estado = 'menu_programa'

    elif estado == 'editar_atalho_comb':
        if comando != '':
            programa_selecionado['atalhos'][entrada_buffer]['combinacao'] = comando
        limpar_saida()
        atalho = programa_selecionado['atalhos'][entrada_buffer]
        escrever_saida(f"Digite a nova descrição do atalho ou ENTER para manter '{atalho['descricao']}':")
        estado = 'editar_atalho_desc'

    elif estado == 'editar_atalho_desc':
        if comando != '':
            programa_selecionado['atalhos'][entrada_buffer]['descricao'] = comando
        salvar_dados()
        escrever_saida("Atalho editado com sucesso!")
        exibir_menu_programa()
        estado = 'menu_programa'

    elif estado == 'editar_nota_num':
        if comando == '':
            exibir_menu_programa()
            estado = 'menu_programa'
            return
        if comando.isdigit():
            entrada_buffer = int(comando) - 1
            if 0 <= entrada_buffer < len(programa_selecionado['notas']):
                limpar_saida()
                nota = programa_selecionado['notas'][entrada_buffer]
                escrever_saida(f"Digite a nova descrição da nota ou ENTER para manter '{nota['descricao']}':")
                estado = 'editar_nota_desc'
            else:
                escrever_saida("Número inválido.")
                estado = 'menu_programa'
        else:
            escrever_saida("Entrada inválida.")
            estado = 'menu_programa'

    elif estado == 'editar_nota_desc':
        if comando != '':
            programa_selecionado['notas'][entrada_buffer]['descricao'] = comando
        limpar_saida()
        nota = programa_selecionado['notas'][entrada_buffer]
        escrever_saida(f"Digite o novo texto da nota ou ENTER para manter:")
        escrever_saida(f"\nTexto atual:\n{nota['texto']}")
        estado = 'editar_nota_texto'

    elif estado == 'editar_nota_texto':
        if comando != '':
            programa_selecionado['notas'][entrada_buffer]['texto'] = comando
        salvar_dados()
        escrever_saida("Nota editada com sucesso!")
        exibir_menu_programa()
        estado = 'menu_programa'

    elif estado == 'editar_snippet_num':
        if comando == '':
            exibir_menu_programa()
            estado = 'menu_programa'
            return
        if comando.isdigit():
            entrada_buffer = int(comando) - 1
            if 0 <= entrada_buffer < len(programa_selecionado['snippets']):
                limpar_saida()
                snippet = programa_selecionado['snippets'][entrada_buffer]
                escrever_saida(f"Digite a nova descrição do snippet ou ENTER para manter '{snippet['descricao']}':")
                estado = 'editar_snippet_desc'
            else:
                escrever_saida("Número inválido.")
                estado = 'menu_programa'
        else:
            escrever_saida("Entrada inválida.")
            estado = 'menu_programa'

    elif estado == 'editar_snippet_desc':
        if comando != '':
            programa_selecionado['snippets'][entrada_buffer]['descricao'] = comando
        limpar_saida()
        snippet = programa_selecionado['snippets'][entrada_buffer]
        escrever_saida(f"Digite o novo código do snippet ou ENTER para manter:")
        escrever_saida(f"\nCódigo atual:\n{snippet['codigo']}")
        estado = 'editar_snippet_codigo'

    elif estado == 'editar_snippet_codigo':
        if comando != '':
            programa_selecionado['snippets'][entrada_buffer]['codigo'] = comando
        salvar_dados()
        escrever_saida("Snippet editado com sucesso!")
        exibir_menu_programa()
        estado = 'menu_programa'

    elif estado == 'cadastrar_item':
        if comando == '':
            exibir_menu_programa()
            estado = 'menu_programa'
        elif comando == '1':
            limpar_saida()
            escrever_saida("Digite a combinação do atalho:")
            estado = 'cadastrar_atalho_comb'
        elif comando == '2':
            limpar_saida()
            escrever_saida("Digite a descrição da nota:")
            estado = 'cadastrar_nota_desc'
        elif comando == '3':
            limpar_saida()
            escrever_saida("Digite a descrição do snippet:")
            estado = 'cadastrar_snippet_desc'
        else:
            escrever_saida("Opção inválida.")

    elif estado == 'cadastrar_atalho_comb':
        entrada_buffer = comando
        escrever_saida("Digite a descrição do atalho:")
        estado = 'cadastrar_atalho_desc'

    elif estado == 'cadastrar_atalho_desc':
        novo_atalho = {
            "combinacao": entrada_buffer,
            "descricao": comando
        }
        programa_selecionado['atalhos'].append(novo_atalho)
        salvar_dados()
        escrever_saida("Atalho cadastrado com sucesso!")
        exibir_menu_programa()
        estado = 'menu_programa'

    elif estado == 'cadastrar_nota_desc':
        entrada_buffer = comando
        limpar_saida()
        escrever_saida("Digite o texto da nota:")
        estado = 'cadastrar_nota_texto'

    elif estado == 'cadastrar_nota_texto':
        nova_nota = {
            "descricao": entrada_buffer,
            "texto": comando
        }
        programa_selecionado['notas'].append(nova_nota)
        salvar_dados()
        escrever_saida("Nota cadastrada com sucesso!")
        exibir_menu_programa()
        estado = 'menu_programa'

    elif estado == 'cadastrar_snippet_desc':
        entrada_buffer = comando
        limpar_saida()
        
        # Lista de linguagens em ordem alfabética
        linguagens = ['bash', 'c', 'cpp', 'css', 'html', 'java', 'javascript', 'python', 'sql', 'text', 'markdown']
        
        escrever_saida("Escolha a linguagem do snippet:")
        escrever_saida("========================")
        for idx, lang in enumerate(linguagens, 1):
            escrever_saida(f"{idx} - {lang}")
        escrever_saida("========================")
        escrever_saida("Ou pressione ENTER para Python (padrão)")
        
        estado = 'cadastrar_snippet_linguagem'

    elif estado == 'cadastrar_snippet_linguagem':
        # Lista de linguagens (mesma ordem)
        linguagens = ['bash', 'c', 'cpp', 'css', 'html', 'java', 'javascript', 'python', 'sql', 'text', 'markdown']
        
        # Verificar se é um número ou nome de linguagem
        if comando.strip() == '':
            linguagem = 'python'  # Padrão
        elif comando.isdigit():
            idx = int(comando) - 1
            if 0 <= idx < len(linguagens):
                linguagem = linguagens[idx]
            else:
                escrever_saida("Número inválido. Usando Python como padrão.")
                linguagem = 'python'
        else:
            # Aceitar nome da linguagem diretamente
            linguagem = comando.strip().lower()
            if linguagem not in linguagens:
                escrever_saida(f"Linguagem '{linguagem}' não reconhecida. Usando Python como padrão.")
                linguagem = 'python'
        
        # Criar um buffer temporário para armazenar descrição e linguagem
        # Formato: "descricao|linguagem"
        entrada_buffer = f"{entrada_buffer}|{linguagem}"
        
        limpar_saida()
        escrever_saida(f"Digite o código do snippet ({linguagem}):")
        estado = 'cadastrar_snippet_codigo'

    elif estado == 'cadastrar_snippet_codigo':
        # Recuperar descrição e linguagem do buffer
        partes = entrada_buffer.split('|')
        descricao = partes[0]
        linguagem = partes[1] if len(partes) > 1 else 'python'
        
        novo_snippet = {
            "descricao": descricao,
            "codigo": comando,
            "linguagem": linguagem
        }
        programa_selecionado['snippets'].append(novo_snippet)
        salvar_dados()
        escrever_saida("Snippet cadastrado com sucesso!")
        exibir_menu_programa()
        estado = 'menu_programa'

    elif estado == 'deletar_item':
        if comando == '':
            exibir_menu_programa()
            estado = 'menu_programa'
        elif comando == '1':
            limpar_saida()
            if not programa_selecionado['atalhos']:
                escrever_saida("Não há atalhos para deletar.")
                exibir_menu_programa()
                estado = 'menu_programa'
            else:
                for idx, atalho in enumerate(programa_selecionado['atalhos']):
                    escrever_saida(f"{idx + 1} - {atalho['combinacao']}: {atalho['descricao']}")
                escrever_saida("\nDigite o número do atalho que deseja deletar ou tecle ENTER para voltar:")
                estado = 'deletar_atalho_num'
        elif comando == '2':
            limpar_saida()
            if not programa_selecionado['notas']:
                escrever_saida("Não há notas para deletar.")
                exibir_menu_programa()
                estado = 'menu_programa'
            else:
                for idx, nota in enumerate(programa_selecionado['notas']):
                    escrever_saida(f"{idx + 1} - {nota['descricao']}")
                escrever_saida("\nDigite o número da nota que deseja deletar ou tecle ENTER para voltar:")
                estado = 'deletar_nota_num'
        elif comando == '3':
            limpar_saida()
            if not programa_selecionado['snippets']:
                escrever_saida("Não há snippets para deletar.")
                exibir_menu_programa()
                estado = 'menu_programa'
            else:
                for idx, snippet in enumerate(programa_selecionado['snippets']):
                    escrever_saida(f"{idx + 1} - {snippet['descricao']}")
                escrever_saida("\nDigite o número do snippet que deseja deletar ou tecle ENTER para voltar:")
                estado = 'deletar_snippet_num'
        else:
            escrever_saida("Opção inválida.")

    elif estado == 'deletar_atalho_num':
        if comando == '':
            exibir_menu_programa()
            estado = 'menu_programa'
            return
        if comando.isdigit():
            entrada_buffer = int(comando) - 1
            if 0 <= entrada_buffer < len(programa_selecionado['atalhos']):
                atalho = programa_selecionado['atalhos'][entrada_buffer]
                escrever_saida(f"Tem certeza que deseja deletar o atalho '{atalho['combinacao']}'? (S/N)")
                estado = 'confirmar_deletar_atalho'
            else:
                escrever_saida("Número inválido.")
                estado = 'menu_programa'
        else:
            escrever_saida("Entrada inválida.")
            estado = 'menu_programa'

    elif estado == 'confirmar_deletar_atalho':
        if comando.upper() == 'S':
            del programa_selecionado['atalhos'][entrada_buffer]
            salvar_dados()
            escrever_saida("Atalho deletado com sucesso!")
            exibir_menu_programa()
            estado = 'menu_programa'
        else:
            exibir_menu_programa()
            estado = 'menu_programa'

    elif estado == 'deletar_nota_num':
        if comando == '':
            exibir_menu_programa()
            estado = 'menu_programa'
            return
        if comando.isdigit():
            entrada_buffer = int(comando) - 1
            if 0 <= entrada_buffer < len(programa_selecionado['notas']):
                nota = programa_selecionado['notas'][entrada_buffer]
                escrever_saida(f"Tem certeza que deseja deletar a nota '{nota['descricao']}'? (S/N)")
                estado = 'confirmar_deletar_nota'
            else:
                escrever_saida("Número inválido.")
                estado = 'menu_programa'
        else:
            escrever_saida("Entrada inválida.")
            estado = 'menu_programa'

    elif estado == 'confirmar_deletar_nota':
        if comando.upper() == 'S':
            del programa_selecionado['notas'][entrada_buffer]
            salvar_dados()
            escrever_saida("Nota deletada com sucesso!")
            exibir_menu_programa()
            estado = 'menu_programa'
        else:
            exibir_menu_programa()
            estado = 'menu_programa'

    elif estado == 'editar_nome_programa':
        if comando == '':
            exibir_menu_programa()
            estado = 'menu_programa'
            return
        
        programa_selecionado['nome'] = comando
        salvar_dados()
        escrever_saida("Nome do programa alterado com sucesso!")
        exibir_menu_programa()
        estado = 'menu_programa'

    elif estado == 'editar_descricao_programa':
        if comando == '':
            exibir_menu_programa()
            estado = 'menu_programa'
            return
        
        programa_selecionado['descricao'] = comando
        salvar_dados()
        escrever_saida("Descrição do programa alterada com sucesso!")
        exibir_menu_programa()
        estado = 'menu_programa'

    elif estado == 'deletar_programa':
        if comando.upper() == 'S':
            dados['programas'].remove(programa_selecionado)
            salvar_dados()
            limpar_saida()
            escrever_saida("Programa deletado com sucesso!")
            escrever_saida("\nComece a digitar o nome do programa ou 'sair' para encerrar.")
            estado = 'inicio'
        else:
            exibir_menu_programa()
            estado = 'menu_programa'

    elif estado == 'deletar_snippet_num':
        if comando == '':
            exibir_menu_programa()
            estado = 'menu_programa'
            return
        if comando.isdigit():
            entrada_buffer = int(comando) - 1
            if 0 <= entrada_buffer < len(programa_selecionado['snippets']):
                snippet = programa_selecionado['snippets'][entrada_buffer]
                escrever_saida(f"Tem certeza que deseja deletar o snippet '{snippet['descricao']}'? (S/N)")
                estado = 'confirmar_deletar_snippet'
            else:
                escrever_saida("Número inválido.")
                estado = 'menu_programa'
        else:
            escrever_saida("Entrada inválida.")
            estado = 'menu_programa'

    elif estado == 'confirmar_deletar_snippet':
        if comando.upper() == 'S':
            del programa_selecionado['snippets'][entrada_buffer]
            salvar_dados()
            escrever_saida("Snippet deletado com sucesso!")
            exibir_menu_programa()
            estado = 'menu_programa'
        else:
            exibir_menu_programa()
            estado = 'menu_programa'

def salvar_nota_edicao(event=None):
    """Salvar nota/atalho/snippet em edição com Ctrl+S"""
    global sub_estado, nota_em_edicao, atalho_em_edicao, snippet_em_edicao
    
    if sub_estado in ['nota_edicao', 'atalho_edicao', 'snippet_edicao']:
        # Simular comando de salvar
        entrada.delete(0, 'end')
        entrada.insert(0, 'CTRL_S')
        executar_comando()
    return "break"  # Prevenir comportamento padrão

def cancelar_edicao_nota(event=None):
    """Cancelar edição com Esc"""
    global sub_estado, nota_em_edicao, atalho_em_edicao, snippet_em_edicao
    
    if sub_estado in ['nota_edicao', 'atalho_edicao', 'snippet_edicao']:
        # Simular comando de cancelar
        entrada.delete(0, 'end')
        entrada.insert(0, 'ESC')
        executar_comando()
    return "break"  # Prevenir comportamento padrão

# Bindings de teclado
entrada.bind("<Return>", executar_comando)
root.bind("<Control-s>", salvar_nota_edicao)
root.bind("<Escape>", cancelar_edicao_nota)

# Salvar a posição e tamanho da janela ao fechar
root.protocol("WM_DELETE_WINDOW", lambda: (salvar_config_janela(root), root.destroy()))

limpar_saida()
escrever_saida("========================================")
escrever_saida("                BEM-VINDO AO KEYBASE!   ")
escrever_saida("========================================")
escrever_saida("- Pressione ENTER para listar todos os programas")
escrever_saida("- Comece a digitar para buscar")
escrever_saida("- Pressione 'sair' para encerrar.")

dados = carregar_dados()

root.after(100, lambda: entrada.focus_set())
root.mainloop()
