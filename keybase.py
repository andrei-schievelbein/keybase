import customtkinter as ctk
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'data.json')

# Estado global
estado = 'inicio'
dados = {}
resultados = []
programa_selecionado = None
sub_estado = None
entrada_buffer = ''
indice_edicao = None

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
    if not os.path.exists(DATA_FILE):
        return {"programas": []}
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        try:
            dados = json.load(f)
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
    global sub_estado
    limpar_saida()
    if not programa_selecionado['atalhos']:
        escrever_saida("Nenhum atalho cadastrado. Aperte C para cadastrar ou Enter para voltar.")
        sub_estado = 'atalho_vazio'
    else:
        escrever_saida("Aperte ENTER para voltar.")
        for idx, atalho in enumerate(programa_selecionado['atalhos']):
            escrever_saida(f"{idx + 1} - {atalho['combinacao']}: {atalho['descricao']}")
        sub_estado = 'atalho_existente'

def adicionar_atalho():
    global estado
    escrever_saida("Digite a combinação do atalho:")
    estado = 'adicionar_atalho_comb'

def ver_notas():
    global sub_estado
    limpar_saida()
    if not programa_selecionado['notas']:
        escrever_saida("Nenhuma nota cadastrada. Aperte C para cadastrar ou Enter para voltar.")
        sub_estado = 'nota_vazio'
    else:
        escrever_saida("Aperte ENTER para voltar.")
        for idx, nota in enumerate(programa_selecionado['notas']):
            escrever_saida(f"{idx + 1} - {nota}")
        sub_estado = 'nota_existente'

def adicionar_nota():
    global estado
    escrever_saida("Digite a nota:")
    estado = 'adicionar_nota'

def executar_comando(event=None):
    global estado, dados, resultados, programa_selecionado, sub_estado, entrada_buffer, indice_edicao

    comando = entrada.get().strip()
    entrada.delete(0, 'end')
    escrever_saida(f"> {comando}")

    if sub_estado == 'atalho_existente':
        if comando == '':
            exibir_menu_programa()
            sub_estado = None
        else:
            escrever_saida("Pressione apenas ENTER para voltar.")
        return

    if sub_estado == 'nota_existente':
        if comando == '':
            exibir_menu_programa()
            sub_estado = None
        else:
            escrever_saida("Pressione apenas ENTER para voltar.")
        return

    if comando.lower() == 'sair':
        root.destroy()
        return

    if sub_estado:
        if sub_estado in ['atalho_vazio', 'nota_vazio']:
            if comando.upper() == 'C':
                if sub_estado == 'atalho_vazio':
                    adicionar_atalho()
                else:
                    adicionar_nota()
                sub_estado = None
                return
            elif comando == '':
                exibir_menu_programa()
                sub_estado = None
                return
            else:
                escrever_saida("Opção inválida. Aperte C para cadastrar ou Enter para voltar.")
                return

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
            escrever_saida("Deseja adicionar um atalho ou uma nota? (A/N):")
            estado = 'adicionar_item'
        elif comando == '4':
            limpar_saida()
            escrever_saida("Deseja editar um atalho ou uma nota? (A/N):")
            estado = 'editar_item'
        elif comando == '5':
            limpar_saida()
            escrever_saida("Deseja deletar um atalho ou uma nota? (A/N):")
            estado = 'deletar_item'
        elif comando == '0':
            limpar_saida()
            estado = 'inicio'
            escrever_saida("Voltando para a busca...")
        else:
            escrever_saida("Opção inválida.")

    elif estado == 'adicionar_item':
        if comando.upper() == 'A':
            adicionar_atalho()
        elif comando.upper() == 'N':
            adicionar_nota()
        else:
            escrever_saida("Opção inválida.")
            exibir_menu_programa()
            estado = 'menu_programa'

    elif estado == 'editar_item':
        if comando.upper() == 'A':
            limpar_saida()
            escrever_saida("Digite o número do atalho que deseja editar ou tecle ENTER para voltar:")
            for idx, atalho in enumerate(programa_selecionado['atalhos']):
                escrever_saida(f"{idx + 1} - {atalho['combinacao']}: {atalho['descricao']}")
            estado = 'editar_atalho'
        elif comando.upper() == 'N':
            limpar_saida()
            escrever_saida("Digite o número da nota que deseja editar ou tecle ENTER para voltar:")
            for idx, nota in enumerate(programa_selecionado['notas']):
                escrever_saida(f"{idx + 1} - {nota}")
            estado = 'editar_nota'
        else:
            escrever_saida("Opção inválida.")
            exibir_menu_programa()
            estado = 'menu_programa'

    elif estado == 'editar_atalho':
        if comando == '':
            exibir_menu_programa()
            estado = 'menu_programa'
        elif comando.isdigit():
            indice_edicao = int(comando) - 1
            if 0 <= indice_edicao < len(programa_selecionado['atalhos']):
                escrever_saida("Digite a nova descrição do atalho:")
                entrada_buffer = indice_edicao
                estado = 'confirmar_editar_atalho'
            else:
                escrever_saida("Número inválido.")
                exibir_menu_programa()
                estado = 'menu_programa'
        else:
            escrever_saida("Entrada inválida.")

    elif estado == 'confirmar_editar_atalho':
        programa_selecionado['atalhos'][entrada_buffer]['descricao'] = comando
        salvar_dados()
        escrever_saida("Atalho editado com sucesso!")
        exibir_menu_programa()
        estado = 'menu_programa'

    elif estado == 'editar_nota':
        if comando == '':
            exibir_menu_programa()
            estado = 'menu_programa'
        elif comando.isdigit():
            indice_edicao = int(comando) - 1
            if 0 <= indice_edicao < len(programa_selecionado['notas']):
                escrever_saida("Digite a nova nota:")
                entrada_buffer = indice_edicao
                estado = 'confirmar_editar_nota'
            else:
                escrever_saida("Número inválido.")
                exibir_menu_programa()
                estado = 'menu_programa'
        else:
            escrever_saida("Entrada inválida.")

    elif estado == 'confirmar_editar_nota':
        programa_selecionado['notas'][entrada_buffer] = comando
        salvar_dados()
        escrever_saida("Nota editada com sucesso!")
        exibir_menu_programa()
        estado = 'menu_programa'

    elif estado == 'adicionar_atalho_comb':
        entrada_buffer = comando
        escrever_saida("Digite a descrição do atalho:")
        estado = 'adicionar_atalho_desc'

    elif estado == 'adicionar_atalho_desc':
        for atalho in programa_selecionado['atalhos']:
            if atalho['combinacao'].lower() == entrada_buffer.lower():
                escrever_saida("Atalho já existe! Não será adicionado.")
                exibir_menu_programa()
                estado = 'menu_programa'
                return
        novo = {"combinacao": entrada_buffer, "descricao": comando}
        programa_selecionado['atalhos'].append(novo)
        salvar_dados()
        escrever_saida(f"Atalho '{entrada_buffer}' adicionado com sucesso!")
        exibir_menu_programa()
        estado = 'menu_programa'

    elif estado == 'adicionar_nota':
        programa_selecionado['notas'].append(comando)
        salvar_dados()
        escrever_saida("Nota adicionada com sucesso!")
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
