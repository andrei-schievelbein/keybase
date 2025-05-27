import customtkinter as ctk
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'data.json')

estado = 'inicio'
dados = {}
resultados = []
programa_selecionado = None
sub_estado = None
entrada_buffer = ''

root = ctk.CTk()
root.title("KeyBase")

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
    escrever_saida("===================")
    escrever_saida("1 - Ver atalhos")
    escrever_saida("2 - Ver notas")
    escrever_saida("===================")
    escrever_saida("3 - Adicionar")
    escrever_saida("4 - Editar")
    escrever_saida("5 - Deletar")
    escrever_saida("===================")
    escrever_saida("6 - Editar nome do programa")
    escrever_saida("7 - Editar descrição")
    escrever_saida("8 - Deletar programa")
    escrever_saida("===================")
    escrever_saida("0 - Voltar")
    escrever_saida("===================")

def ver_atalhos():
    global estado, sub_estado
    limpar_saida()
    if not programa_selecionado['atalhos']:
        escrever_saida("Nenhum atalho cadastrado. Aperte C para cadastrar ou Enter para voltar.")
        sub_estado = 'atalho_vazio'
    else:
        escrever_saida("Aperte ENTER para voltar.")
        for idx, atalho in enumerate(programa_selecionado['atalhos']):
            escrever_saida(f"{idx + 1} - {atalho['combinacao']}: {atalho['descricao']}")
        sub_estado = 'atalho_existente'

def ver_notas():
    global estado, sub_estado
    limpar_saida()
    if not programa_selecionado['notas']:
        escrever_saida("Nenhuma nota cadastrada. Aperte C para cadastrar ou Enter para voltar.")
        sub_estado = 'nota_vazio'
    else:
        escrever_saida("Aperte ENTER para voltar.")
        for idx, nota in enumerate(programa_selecionado['notas']):
            escrever_saida(f"{idx + 1} - {nota}")
        sub_estado = 'nota_existente'

def executar_comando(event=None):
    global estado, dados, resultados, programa_selecionado, sub_estado, entrada_buffer

    comando = entrada.get().strip()
    entrada.delete(0, 'end')
    escrever_saida(f"> {comando}")

    if sub_estado in ['atalho_existente', 'nota_existente']:
        if comando == '':
            exibir_menu_programa()
            sub_estado = None
        else:
            escrever_saida("Pressione apenas ENTER para voltar.")
        return

    if comando.lower() == 'sair':
        root.destroy()
        return

    if sub_estado in ['atalho_vazio', 'nota_vazio']:
        if comando.upper() == 'C':
            if sub_estado == 'atalho_vazio':
                limpar_saida()
                escrever_saida("Digite a combinação do atalho:")
                estado = 'cadastrar_atalho_comb'
            else:  # nota_vazio
                limpar_saida()
                escrever_saida("Digite a nova nota:")
                estado = 'cadastrar_nota'
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
        resultados = buscar_programas(comando)
        if resultados:
            limpar_saida()
            exibir_programas(resultados)
            escrever_saida("Digite o número do programa para selecionar.")
            estado = 'selecionar_programa'
        else:
            escrever_saida("Nenhum programa encontrado.")
            escrever_saida("Deseja cadastrar um novo programa? (S/N)")
            estado = 'confirmar_cadastro'
            entrada_buffer = comando

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
            "notas": []
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
        if comando == '1':
            ver_atalhos()
        elif comando == '2':
            ver_notas()
        elif comando == '3':
            limpar_saida()
            escrever_saida("Deseja cadastrar um atalho ou uma nota? (A/N):")
            estado = 'cadastrar_item'
        elif comando == '4':
            limpar_saida()
            escrever_saida("Deseja editar um atalho ou uma nota? (A/N):")
            estado = 'editar_item'
        elif comando == '5':
            limpar_saida()
            escrever_saida("Deseja deletar um atalho ou uma nota? (A/N):")
            estado = 'deletar_item'
        elif comando == '6':
            limpar_saida()
            escrever_saida(f"Nome atual do programa: {programa_selecionado['nome']}")
            escrever_saida("\nDigite o novo nome do programa ou tecle ENTER para voltar:")
            estado = 'editar_nome_programa'
        elif comando == '7':
            limpar_saida()
            escrever_saida(f"Descrição atual do programa: {programa_selecionado['descricao']}")
            escrever_saida("\nDigite a nova descrição do programa ou tecle ENTER para voltar:")
            estado = 'editar_descricao_programa'
        elif comando == '8':
            limpar_saida()
            escrever_saida(f"Deseja apagar o programa '{programa_selecionado['nome']}'?")
            escrever_saida("Todos os atalhos e notas serão apagados!")
            escrever_saida("\nDigite 'S' para confirmar ou tecle ENTER para voltar:")
            estado = 'deletar_programa'
        elif comando == '0':
            limpar_saida()
            escrever_saida("Comece a digitar o nome do programa ou 'sair' para encerrar.")
            estado = 'inicio'
        else:
            escrever_saida("Opção inválida.")

    elif estado == 'editar_item':
        if comando.upper() == 'A':
            limpar_saida()
            for idx, atalho in enumerate(programa_selecionado['atalhos']):
                escrever_saida(f"{idx + 1} - {atalho['combinacao']}: {atalho['descricao']}")
            escrever_saida("Digite o número do atalho que deseja editar ou tecle ENTER para voltar:")
            estado = 'editar_atalho_num'
        elif comando.upper() == 'N':
            limpar_saida()
            for idx, nota in enumerate(programa_selecionado['notas']):
                escrever_saida(f"{idx + 1} - {nota}")
            escrever_saida("Digite o número da nota que deseja editar ou tecle ENTER para voltar:")
            estado = 'editar_nota_num'
        else:
            escrever_saida("Opção inválida.")
            exibir_menu_programa()
            estado = 'menu_programa'

    elif estado == 'editar_atalho_num':
        if comando == '':
            exibir_menu_programa()
            estado = 'menu_programa'
            return
        if comando.isdigit():
            entrada_buffer = int(comando) - 1
            if 0 <= entrada_buffer < len(programa_selecionado['atalhos']):
                escrever_saida("Digite a nova combinação do atalho:")
                estado = 'editar_atalho_comb'
            else:
                escrever_saida("Número inválido.")
                estado = 'menu_programa'
        else:
            escrever_saida("Entrada inválida.")
            estado = 'menu_programa'

    elif estado == 'editar_atalho_comb':
        programa_selecionado['atalhos'][entrada_buffer]['combinacao'] = comando
        escrever_saida("Digite a nova descrição do atalho:")
        estado = 'editar_atalho_desc'

    elif estado == 'editar_atalho_desc':
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
                escrever_saida("Digite a nova nota:")
                estado = 'editar_nota'
            else:
                escrever_saida("Número inválido.")
                estado = 'menu_programa'
        else:
            escrever_saida("Entrada inválida.")
            estado = 'menu_programa'

    elif estado == 'editar_nota':
        programa_selecionado['notas'][entrada_buffer] = comando
        salvar_dados()
        escrever_saida("Nota editada com sucesso!")
        exibir_menu_programa()
        estado = 'menu_programa'

    elif estado == 'cadastrar_item':
        if comando.upper() == 'A':
            limpar_saida()
            escrever_saida("Digite a combinação do atalho:")
            estado = 'cadastrar_atalho_comb'
        elif comando.upper() == 'N':
            limpar_saida()
            escrever_saida("Digite a nova nota:")
            estado = 'cadastrar_nota'
        else:
            escrever_saida("Opção inválida.")
            exibir_menu_programa()
            estado = 'menu_programa'

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

    elif estado == 'cadastrar_nota':
        programa_selecionado['notas'].append(comando)
        salvar_dados()
        escrever_saida("Nota cadastrada com sucesso!")
        exibir_menu_programa()
        estado = 'menu_programa'

    elif estado == 'deletar_item':
        if comando.upper() == 'A':
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
        elif comando.upper() == 'N':
            limpar_saida()
            if not programa_selecionado['notas']:
                escrever_saida("Não há notas para deletar.")
                exibir_menu_programa()
                estado = 'menu_programa'
            else:
                for idx, nota in enumerate(programa_selecionado['notas']):
                    escrever_saida(f"{idx + 1} - {nota}")
                escrever_saida("\nDigite o número da nota que deseja deletar ou tecle ENTER para voltar:")
                estado = 'deletar_nota_num'
        else:
            escrever_saida("Opção inválida.")
            exibir_menu_programa()
            estado = 'menu_programa'

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
                escrever_saida(f"Tem certeza que deseja deletar a nota '{nota}'? (S/N)")
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

entrada.bind("<Return>", executar_comando)

limpar_saida()
escrever_saida("===========================")
escrever_saida("  BEM-VINDO AO KEYBASE!")
escrever_saida("===========================")
escrever_saida("Comece a digitar o nome do programa ou 'sair' para encerrar.")

dados = carregar_dados()

root.after(100, lambda: entrada.focus_set())
root.mainloop()
