import customtkinter as ctk
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
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

root = ctk.CTk()
root.title("KeyBase")

# Carregar a posição e tamanho salvos da janela
carregar_config_janela(root)

entrada = ctk.CTkEntry(root, width=600)
entrada.pack(padx=10, pady=(10, 0), fill="x")

saida = ctk.CTkTextbox(root, height=400)
saida.pack(padx=10, pady=10, fill="both", expand=True)

def escrever_saida(texto):
    saida.insert("end", texto + "\n")
    saida.see("end")

def limpar_saida():
    saida.delete("1.0", "end")

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
        escrever_saida(f"{idx + 1} - {prog['nome']}: {prog['descricao']}")

def exibir_menu_programa():
    limpar_saida()
    escrever_saida("========================")
    escrever_saida("1 - Ver atalhos")
    escrever_saida("2 - Ver notas")
    escrever_saida("3 - Ver snippets")
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
        escrever_saida("Aperte ENTER para voltar.")
        for atalho in programa_selecionado['atalhos']:
            escrever_saida(f"{atalho['combinacao']}: {atalho['descricao']}")
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
    escrever_saida(f"> {comando}")

    if sub_estado in ['atalho_existente', 'nota_existente', 'snippet_existente']:
        if comando == '':
            exibir_menu_programa()
            sub_estado = None
        elif sub_estado == 'nota_existente' and comando.isdigit():
            idx = int(comando) - 1
            if 0 <= idx < len(programa_selecionado['notas']):
                limpar_saida()
                nota = programa_selecionado['notas'][idx]
                escrever_saida("Pressione ENTER para voltar.")
                escrever_saida("\nTexto:")
                escrever_saida(nota['texto'])
            else:
                escrever_saida("Número inválido. Pressione ENTER para voltar.")
        elif sub_estado == 'snippet_existente' and comando.isdigit():
            idx = int(comando) - 1
            if 0 <= idx < len(programa_selecionado['snippets']):
                limpar_saida()
                snippet = programa_selecionado['snippets'][idx]
                escrever_saida("Pressione ENTER para voltar.")
                escrever_saida("\nCódigo:")
                escrever_saida(snippet['codigo'])
            else:
                escrever_saida("Número inválido. Pressione ENTER para voltar.")
        else:
            escrever_saida("Pressione apenas ENTER para voltar ou digite um número válido.")
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
        escrever_saida("Digite o código do snippet:")
        estado = 'cadastrar_snippet_codigo'

    elif estado == 'cadastrar_snippet_codigo':
        novo_snippet = {
            "descricao": entrada_buffer,
            "codigo": comando
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

entrada.bind("<Return>", executar_comando)

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
