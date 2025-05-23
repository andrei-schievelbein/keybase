import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'data.json')

print(f"Usando arquivo: {os.path.abspath(DATA_FILE)}")


def carregar_dados():
    if not os.path.exists(DATA_FILE):
        return {"programas": []}

    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        try:
            dados = json.load(f)
            if 'programas' not in dados:
                dados['programas'] = []
            # Garante que todos os programas tenham 'atalhos' e 'notas'
            for programa in dados['programas']:
                if 'atalhos' not in programa:
                    programa['atalhos'] = []
                if 'notas' not in programa:
                    programa['notas'] = []
            return dados
        except json.JSONDecodeError:
            return {"programas": []}


def salvar_dados(dados):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)
    print(f"Dados salvos com sucesso no arquivo: {DATA_FILE}")


def buscar_programas(dados, termo):
    termo = termo.lower()
    resultados = []
    for programa in dados['programas']:
        if termo in programa['nome'].lower():
            resultados.append(programa)
    return resultados


def adicionar_programa(dados):
    nome = input("Digite o nome do novo programa: ").strip()
    descricao = input("Digite uma descrição para o programa: ").strip()
    novo_programa = {
        "nome": nome,
        "descricao": descricao,
        "atalhos": [],
        "notas": []
    }
    dados['programas'].append(novo_programa)
    salvar_dados(dados)
    print(f"\nPrograma '{nome}' adicionado com sucesso!\n")


def iniciar_busca_ou_cadastro(dados):
    while True:
        termo = input("Comece a digitar o nome do programa (ou 'sair' para encerrar): ").strip()
        if termo.lower() == 'sair':
            print("Encerrando KeyBase. Até mais!")
            break

        resultados = buscar_programas(dados, termo)
        if resultados:
            print("\nProgramas encontrados:")
            for idx, prog in enumerate(resultados):
                print(f"{idx + 1} - {prog['nome']}: {prog['descricao']}")

            programa_selecionado = selecionar_programa(resultados)
            if programa_selecionado:
                print(f"\nVocê selecionou: {programa_selecionado['nome']}\n")
                menu_programa(programa_selecionado, dados)
            else:
                print("Voltando para a busca...\n")
        else:
            print("Nenhum programa encontrado.")
            opcao = input("Deseja cadastrar um novo programa? (S/N): ").strip().upper()
            if opcao == 'S':
                adicionar_programa(dados)


def selecionar_programa(resultados):
    while True:
        escolha = input("Digite o número do programa para selecionar ou pressione ENTER para voltar: ").strip()
        if escolha == '':
            return None
        if escolha.isdigit():
            idx = int(escolha) - 1
            if 0 <= idx < len(resultados):
                return resultados[idx]
        print("Opção inválida. Tente novamente.")


def menu_programa(programa, dados):
    while True:
        print(f"\n===========================")
        print(f" PROGRAMA: {programa['nome']}")
        print(f"===========================\n")
        print("===================")
        print("1 - Ver atalhos")
        print("2 - Ver notas")
        print("===================")
        print("3 - Adicionar")
        print("4 - Editar")
        print("5 - Deletar")
        print("===================")
        print("6 - Editar nome do programa")
        print("7 - Editar descrição")
        print("8 - Deletar programa")
        print("===================")
        print("0 - Voltar")
        print("===================\n")

        escolha = input("Escolha uma opção: ").strip()

        if escolha == '1':
            ver_atalhos(programa)
            input("Pressione ENTER para voltar ao menu...")
        elif escolha == '2':
            ver_notas(programa)
            input("Pressione ENTER para voltar ao menu...")
        elif escolha == '3':
            adicionar_item(programa, dados)
        elif escolha == '4':
            editar_item(programa, dados)
        elif escolha == '5':
            deletar_item(programa, dados)
        elif escolha == '6':
            editar_nome_programa(programa, dados)
        elif escolha == '7':
            editar_descricao_programa(programa, dados)
        elif escolha == '8':
            confirmar = input("Tem certeza que deseja deletar este programa? (S/N): ").strip().upper()
            if confirmar == 'S':
                deletar_programa(programa, dados)
                break
        elif escolha == '0':
            break
        else:
            print("Opção inválida. Tente novamente.")



def adicionar_item(programa, dados):
    tipo = input("Deseja adicionar um atalho ou uma nota? (A/N): ").strip().upper()
    if tipo == 'A':
        adicionar_atalho(programa, dados)
    elif tipo == 'N':
        adicionar_nota(programa, dados)
    else:
        print("Opção inválida.")


def editar_item(programa, dados):
    tipo = input("Deseja editar um atalho ou uma nota? (A/N): ").strip().upper()
    if tipo == 'A':
        editar_atalho(programa, dados)
    elif tipo == 'N':
        editar_nota(programa, dados)
    else:
        print("Opção inválida.")


def deletar_item(programa, dados):
    tipo = input("Deseja deletar um atalho ou uma nota? (A/N): ").strip().upper()
    if tipo == 'A':
        deletar_atalho(programa, dados)
    elif tipo == 'N':
        deletar_nota(programa, dados)
    else:
        print("Opção inválida.")


def ver_atalhos(programa):
    print("\n*** Lista de Atalhos ***")
    if not programa['atalhos']:
        print("Nenhum atalho cadastrado.")
    else:
        for idx, atalho in enumerate(programa['atalhos']):
            print(f"{idx + 1} - {atalho['combinacao']}: {atalho['descricao']}")
    print("*************************\n")



def ver_notas(programa):
    print("\n*** Lista de Notas ***")
    if not programa['notas']:
        print("Nenhuma nota cadastrada.")
    else:
        for idx, nota in enumerate(programa['notas']):
            print(f"{idx + 1} - {nota}")
    print("*************************\n")



def adicionar_atalho(programa, dados):
    combinacao = input("Digite a combinação do atalho (ex: Ctrl + S): ").strip()
    descricao = input("Digite a descrição do atalho: ").strip()

    for atalho in programa['atalhos']:
        if atalho['combinacao'].lower() == combinacao.lower():
            print("Atalho já existe! Não será adicionado.")
            return

    novo_atalho = {
        "combinacao": combinacao,
        "descricao": descricao
    }
    programa['atalhos'].append(novo_atalho)
    salvar_dados(dados)
    print(f"Atalho '{combinacao}' adicionado com sucesso!\n")


def adicionar_nota(programa, dados):
    nota = input("Digite a nota: ").strip()
    if nota:
        programa['notas'].append(nota)
        salvar_dados(dados)
        print("Nota adicionada com sucesso!\n")
    else:
        print("Nota vazia. Nada foi adicionado.")


def editar_atalho(programa, dados):
    ver_atalhos(programa)
    escolha = input("Digite o número do atalho que deseja editar ou pressione ENTER para voltar: ").strip()
    
    if escolha == '':
        return

    if not escolha.isdigit():
        print("Entrada inválida.")
        return

    idx = int(escolha) - 1
    if 0 <= idx < len(programa['atalhos']):
        novo_comb = input("Nova combinação (deixe vazio para manter): ").strip()
        nova_desc = input("Nova descrição (deixe vazio para manter): ").strip()
        
        if novo_comb:
            programa['atalhos'][idx]['combinacao'] = novo_comb
        if nova_desc:
            programa['atalhos'][idx]['descricao'] = nova_desc
        
        salvar_dados(dados)
        print("Atalho atualizado com sucesso!\n")
    else:
        print("Número inválido.")



def editar_nota(programa, dados):
    ver_notas(programa)
    escolha = input("Digite o número da nota que deseja editar ou pressione ENTER para voltar: ").strip()
    
    if escolha == '':
        return

    if not escolha.isdigit():
        print("Entrada inválida.")
        return

    idx = int(escolha) - 1
    if 0 <= idx < len(programa['notas']):
        nova_nota = input("Digite a nova nota: ").strip()
        if nova_nota:
            programa['notas'][idx] = nova_nota
            salvar_dados(dados)
            print("Nota atualizada com sucesso!\n")
        else:
            print("Nota não alterada.")
    else:
        print("Número inválido.")



def deletar_atalho(programa, dados):
    ver_atalhos(programa)
    escolha = input("Digite o número do atalho que deseja deletar ou pressione ENTER para voltar: ").strip()
    
    if escolha == '':
        return

    if not escolha.isdigit():
        print("Entrada inválida.")
        return

    idx = int(escolha) - 1
    if 0 <= idx < len(programa['atalhos']):
        confirmar = input("Tem certeza que deseja deletar este atalho? (S/N): ").strip().upper()
        if confirmar == 'S':
            atalho = programa['atalhos'].pop(idx)
            salvar_dados(dados)
            print(f"Atalho '{atalho['combinacao']}' deletado com sucesso!\n")
    else:
        print("Número inválido.")



def deletar_nota(programa, dados):
    ver_notas(programa)
    escolha = input("Digite o número da nota que deseja deletar ou pressione ENTER para voltar: ").strip()
    
    if escolha == '':
        return

    if not escolha.isdigit():
        print("Entrada inválida.")
        return

    idx = int(escolha) - 1
    if 0 <= idx < len(programa['notas']):
        confirmar = input("Tem certeza que deseja deletar esta nota? (S/N): ").strip().upper()
        if confirmar == 'S':
            nota = programa['notas'].pop(idx)
            salvar_dados(dados)
            print(f"Nota '{nota}' deletada com sucesso!\n")
    else:
        print("Número inválido.")



def editar_nome_programa(programa, dados):
    novo_nome = input("Digite o novo nome do programa: ").strip()
    if novo_nome:
        programa['nome'] = novo_nome
        salvar_dados(dados)
        print("Nome do programa atualizado com sucesso!\n")
    else:
        print("Nome não alterado.")

def editar_descricao_programa(programa, dados):
    nova_desc = input("Digite a nova descrição do programa: ").strip()
    if nova_desc:
        programa['descricao'] = nova_desc
        salvar_dados(dados)
        print("Descrição do programa atualizada com sucesso!\n")
    else:
        print("Descrição não alterada.")



def deletar_programa(programa, dados):
    dados['programas'].remove(programa)
    salvar_dados(dados)
    print("Programa deletado com sucesso!\n")


def main():
    print("===========================")
    print("  BEM-VINDO AO KEYBASE!")
    print("===========================")
    dados = carregar_dados()
    print("Dados carregados com sucesso!\n")

    iniciar_busca_ou_cadastro(dados)


if __name__ == "__main__":
    main()
