# 🔑 KeyBase

<div align="center">

![KeyBase Logo](keybase.png)

Um gerenciador elegante de atalhos, notas e snippets de código para seus programas favoritos.

![Python](https://img.shields.io/badge/Python-3.x-blue.svg)
![CustomTkinter](https://img.shields.io/badge/CustomTkinter-5.x-orange.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

</div>

## 📖 Sobre

KeyBase é uma aplicação desktop moderna desenvolvida em Python que permite você gerenciar e organizar:

- ⌨️ Atalhos de teclado
- 📝 Notas importantes
- 💻 Snippets de código

Para cada programa que você usa, você pode manter uma biblioteca organizada de referências rápidas, tornando seu trabalho mais eficiente.

## ✨ Características

- 🎯 Interface moderna e intuitiva usando CustomTkinter
- 🔍 Busca rápida de programas
- 📱 Design responsivo
- 💾 Salvamento automático de dados
- 🎨 Tema escuro elegante
- 🪟 Memoriza posição e tamanho da janela
- 📝 **Renderização Markdown** para notas e atalhos
- ✏️ **Edição rápida** com Ctrl+S para salvar e Esc para cancelar
- 🎨 **Syntax highlighting** para snippets de código (suporta 11 linguagens)
- 📊 **Contadores inteligentes** mostrando quantidade de itens
- 🔖 **Snippets Markdown** com suporte a blocos de código

## 🚀 Como Usar

1. Execute o KeyBase
2. Pressione Enter para ver todos os programas ou comece a digitar para buscar
3. Selecione um programa pelo número
4. Gerencie atalhos, notas e snippets através do menu intuitivo

### Menu Principal

```
========================
1 - Ver atalhos
2 - Ver notas
3 - Ver snippets
========================
4 - Adicionar
5 - Editar
6 - Deletar
========================
7 - Editar nome do programa
8 - Editar descrição
9 - Deletar programa
========================
```

## 🛠️ Instalação

### Usuários Windows


#### GitHub Releases
1. Baixe a última versão do executável na seção [Releases](https://github.com/andrei-schievelbein/keybase/releases)
2. Execute o arquivo `KeyBase.exe`
3. Pronto! Não precisa de instalação

### Desenvolvedores

```bash
# Clone o repositório
git clone https://github.com/andrei-schievelbein/keybase.git

# Entre no diretório
cd keybase

# Instale as dependências
pip install -r requirements.txt

# Execute o programa
python keybase.pyw
```

## 📦 Arquivos e Portabilidade

### Executável Standalone

O KeyBase é distribuído como um **executável standalone** (`.exe`), o que significa:

- ✅ **Não precisa de instalação** - Basta executar o arquivo
- ✅ **Não precisa de Python instalado** - Tudo está embutido no executável
- ✅ **Totalmente portátil** - Pode ser executado de um pen drive


### Arquivos Gerados

Quando você executa o KeyBase, ele cria automaticamente alguns arquivos no **mesmo diretório** onde o executável está localizado:

| Arquivo | Necessário? | Descrição |
|---------|-------------|-----------|
| **KeyBase_latest.exe** | ✅ **Obrigatório** | O executável principal do programa |
| **data.json** | ⚠️ **Recomendado** | Armazena todas as suas notas, atalhos e snippets. Sem ele, você perde seus dados |
| **window_config.json** | ❌ **Opcional** | Salva o tamanho e posição da janela. Será recriado automaticamente se não existir |

### Uso Portátil (Pen Drive)

Para usar o KeyBase em um pen drive:

**Mínimo absoluto:**
```
📁 MeuPenDrive
  └── KeyBase_latest.exe
```

**Recomendado (mantém seus dados):**
```
📁 MeuPenDrive
  ├── KeyBase_latest.exe
  └── data.json
```

**Completo (mantém dados + preferências):**
```
📁 MeuPenDrive
  ├── KeyBase_latest.exe
  ├── data.json
  └── window_config.json
```

> **💡 Dica:** Se você executar o KeyBase pela primeira vez sem o `data.json`, ele criará um arquivo vazio. Seus dados serão salvos automaticamente conforme você adiciona programas, notas, atalhos e snippets.

## 🔧 Tecnologias

- [Python](https://www.python.org/) - Linguagem de programação
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) - Framework moderno para interfaces gráficas
- [Pygments](https://pygments.org/) - Syntax highlighting para snippets de código
- [Markdown](https://python-markdown.github.io/) - Renderização de Markdown
- [PyInstaller](https://www.pyinstaller.org/) - Para criar o executável

## 📝 Estrutura de Dados

O KeyBase usa um arquivo JSON para armazenar os dados com a seguinte estrutura:

```json
{
    "programas": [
        {
            "nome": "Nome do Programa",
            "descricao": "Descrição do Programa",
            "atalhos": [
                {
                    "combinacao": "Ctrl + C",
                    "descricao": "Copiar"
                }
            ],
            "notas": [
                {
                    "descricao": "Título da Nota",
                    "texto": "Conteúdo detalhado da nota"
                }
            ],
            "snippets": [
                {
                    "descricao": "Descrição do Snippet",
                    "codigo": "print('Hello World')",
                    "linguagem": "python"
                }
            ]
        }
    ]
}
```

## 🤝 Contribuindo

Contribuições são sempre bem-vindas! Sinta-se à vontade para:

1. 🍴 Fazer um Fork
2. 👯 Clonar o repositório
3. 🔧 Criar uma branch para sua feature
4. ✏️ Fazer commit das mudanças
5. 👍 Fazer push para a branch
6. 🎉 Criar um novo Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 👤 Autor

Feito com ❤️ por [Andrei Schievelbein](https://www.linkedin.com/in/andrei-schievelbein/)

---

<div align="center">

Se este projeto te ajudou, deixe uma ⭐️!

</div>
