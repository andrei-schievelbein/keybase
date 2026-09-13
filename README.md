# 🔑 KeyBase

<div align="center">

![KeyBase Logo](keybase.png)

Suas notas em Markdown, organizadas em pastas — na profundidade que você quiser.

![Python](https://img.shields.io/badge/Python-3.x-blue.svg)
![CustomTkinter](https://img.shields.io/badge/CustomTkinter-5.x-orange.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

</div>

## 📖 Sobre

KeyBase é uma aplicação desktop em Python para guardar referências rápidas: atalhos de teclado, comandos, trechos de código, anotações — o que você precisar consultar no dia a dia.

A organização fica por sua conta. Existem apenas dois conceitos:

- **📁 Pasta** — uma categoria. Pode conter notas e outras pastas, sem limite de profundidade.
- **📄 Nota** — um texto em Markdown.

Não há tipos fixos de conteúdo. Um "snippet" é só uma nota com um bloco de código; um "atalho" é uma nota com a combinação no título. Você decide a hierarquia:

```
~
├── Python/
│   ├── Pandas/
│   │   ├── Leitura de arquivos
│   │   └── Agrupamentos
│   └── Ambientes virtuais
├── Vscode/
│   ├── Navegação/
│   │   ├── Ctrl + P
│   │   └── Ctrl + G
│   └── Extensões
└── Rascunhos
```

## ✨ Características

- 🗂️ **Pastas aninhadas** sem limite de profundidade
- ⌨️ **Interface de teclado** — navegação por números e letras, sem mouse
- 🔍 **Busca em toda a base** por nome, descrição e conteúdo, mostrando o caminho de cada resultado
- 🎯 **Filtro local** (`/termo`) para pastas grandes
- 📝 **Markdown** com cabeçalhos, listas, ênfase e citações
- 🎨 **Syntax highlighting** em blocos de código (qualquer linguagem suportada pelo Pygments)
- ✏️ **Editor dedicado** — Ctrl+S salva, Esc cancela
- 💾 **Gravação atômica** com backup automático e snapshot diário
- 🌓 Temas claro e escuro
- 🪟 Memoriza posição e tamanho da janela

## 🚀 Como Usar

O KeyBase é operado inteiramente pelo teclado. Digite o comando no campo de cima e pressione Enter.

```
 ~ / Python / Pandas
 ──────────────────────────────────────────────────────────
   1  Leitura de arquivos/                            [4]
   2  Agrupamentos
   3  Merge e join
 ──────────────────────────────────────────────────────────
  nº abrir   C pasta   N nota   R renomear   E editar
  D deletar  V voltar  B buscar  M raiz   ? ajuda   sair
```

### Comandos

| Comando | O que faz |
|---------|-----------|
| `1` `2` `3` … | Abre o item pelo número da lista |
| `C` | Cria uma pasta na pasta atual |
| `N` | Cria uma nota na pasta atual (e já abre o editor) |
| `E` ou `E3` | Edita o conteúdo de uma nota |
| `R` ou `R3` | Renomeia um item |
| `D` ou `D3` | Apaga um item |
| `V` | Volta um nível (ou limpa o filtro) |
| `M` | Vai direto para a raiz |
| `B` | Busca em toda a base |
| `/termo` | Filtra só a pasta atual |
| `?` | Ajuda |
| `sair` | Encerra |

Comandos que agem sobre um item aceitam o número junto (`D3` apaga o item 3) ou sozinho (`D` pergunta qual).

### No editor

| Tecla | Ação |
|-------|------|
| `Ctrl+S` | Salva e volta |
| `Esc` | Cancela (pergunta antes de descartar) |

Para um bloco de código com destaque de sintaxe, use as cercas do Markdown:

````markdown
```python
df = pd.read_csv("dados.csv")
```
````

## 🛠️ Instalação

### Usuários Windows

Baixe a última versão do executável em [Releases](https://github.com/andrei-schievelbein/keybase/releases) e execute. Não precisa instalar nada.

### Desenvolvedores

```bash
git clone https://github.com/andrei-schievelbein/keybase.git
cd keybase
pip install -r requirements.txt
python keybase.pyw
```

Testes:

```bash
python -m unittest discover -s tests -t .
```

## 📦 Arquivos e Portabilidade

O KeyBase é portátil: os dados ficam **ao lado do executável**, então dá para rodar de um pen drive. Se esse diretório não for gravável (por exemplo, um `.exe` instalado em `C:\Program Files`), os dados vão para `%APPDATA%\KeyBase` em vez de se perderem.

| Arquivo | Necessário? | Descrição |
|---------|-------------|-----------|
| **KeyBase.exe** | ✅ Obrigatório | O programa |
| **keybase_data.json** | ⚠️ Recomendado | Suas pastas e notas. Sem ele, você começa do zero |
| **keybase_data.bak.json** | ❌ Automático | Cópia da versão anterior, gravada antes de cada alteração |
| **keybase_data.snapshot-*.json** | ❌ Automático | Uma cópia por dia, guardando os últimos 7 dias |
| **window_config.json** | ❌ Opcional | Tamanho, posição, tema e fontes. Recriado se faltar |

### Se o arquivo de dados for corrompido

O KeyBase **não sobrescreve** um arquivo que não conseguiu ler. Ele abre em modo somente leitura, mostra o erro e oferece restaurar o backup ou um dos snapshots — seus dados continuam no disco enquanto isso.

## 🔧 Tecnologias

- [Python](https://www.python.org/)
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) — interface
- [Markdown](https://python-markdown.github.io/) — renderização
- [Pygments](https://pygments.org/) — syntax highlighting
- [PyInstaller](https://www.pyinstaller.org/) — executável

## 📝 Estrutura de Dados

```json
{
    "schema_version": 2,
    "app_version": "2.0.0",
    "atualizado_em": "2026-09-13T16:22:04+00:00",
    "raiz": {
        "id": "raiz",
        "tipo": "folder",
        "nome": "KeyBase",
        "descricao": "",
        "criado_em": "2026-09-13T16:00:00+00:00",
        "atualizado_em": "2026-09-13T16:22:04+00:00",
        "filhos": [
            {
                "id": "7f3a1c2b9d4e4f0aa1b2c3d4e5f60718",
                "tipo": "folder",
                "nome": "Vscode",
                "descricao": "Editor principal",
                "criado_em": "2026-09-13T16:01:10+00:00",
                "atualizado_em": "2026-09-13T16:20:00+00:00",
                "filhos": [
                    {
                        "id": "c3d4e5f60718293a4b5c6d7e8f901234",
                        "tipo": "file",
                        "nome": "Ctrl + P",
                        "conteudo": "Abre o seletor rápido de arquivos.",
                        "criado_em": "2026-09-13T16:03:00+00:00",
                        "atualizado_em": "2026-09-13T16:22:04+00:00"
                    }
                ]
            }
        ]
    }
}
```

Um `folder` tem `filhos`; um `file` tem `conteudo`. A ordem de exibição é derivada (pastas antes de notas, alfabético), não armazenada — reordenar o arquivo à mão não muda nada nem quebra referências.

> **Formato anterior (v1):** versões até a 1.0.2 usavam `data.json`, com `programas` contendo listas separadas de `atalhos`, `notas` e `snippets`. Esse arquivo não é lido nem modificado pela versão atual. O script `importar_legado.py` converte esse conteúdo para o formato novo, se você quiser aproveitá-lo.

## 🤝 Contribuindo

Contribuições são bem-vindas — abra uma issue ou um pull request.

## 📄 Licença

MIT. Veja [LICENSE](LICENSE).

## 👤 Autor

Feito com ❤️ por [Andrei Schievelbein](https://www.linkedin.com/in/andrei-schievelbein/)

---
