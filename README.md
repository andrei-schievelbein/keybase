# 🔑 KeyBase

<div align="center">

![KeyBase Logo](keybase.png)

Suas notas em Markdown, organizadas em pastas — na profundidade que você quiser.

![Python](https://img.shields.io/badge/Python-3.x-blue.svg)
![PySide6](https://img.shields.io/badge/PySide6-6.x-orange.svg)
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
- 🎯 **Filtro instantâneo** — digite qualquer texto e Enter para filtrar o nível visível
- 🔢 **Contador duplo** `[diretas]:[total]` — quantas notas estão soltas na pasta e quantas existem em toda a hierarquia
- 💡 **Menu de comandos sob demanda** — escondido por padrão, aparece com `?` e some com `?`
- 📝 **Markdown completo** — cabeçalhos com tamanhos reais, tabelas, listas de tarefa, riscado, notas de rodapé, citações e links
- 🎨 **Syntax highlighting** em blocos de código (qualquer linguagem suportada pelo Pygments)
- ✂️ **Editar, preview ou tela dividida** ao escrever uma nota — `Ctrl+1`/`Ctrl+2`/`Ctrl+3`, ou `Ctrl+E` para alternar
- ✏️ **Editor dedicado** com realce de sintaxe — Ctrl+S salva, Esc cancela
- 💾 **Gravação atômica** com backup automático e snapshot diário
- 🌓 Temas claro e escuro
- 🪟 Memoriza posição e tamanho da janela

## 🚀 Como Usar

O KeyBase é operado inteiramente pelo teclado. Digite o comando no campo de cima e pressione Enter.

```
==============================================================
 ~ / Python / Pandas
==============================================================
 1 - Leitura de arquivos/                              [0]:[4]
 2 - Agrupamentos
 3 - Merge e join
==============================================================
```

### Os dois números da pasta

Cada pasta mostra `[a]:[b]`, contando **notas** (sub-pastas não entram na conta):

- **a** — notas soltas dentro da pasta;
- **b** — todas as notas da hierarquia, entrando em cada sub-pasta.

Assim `[0]:[4]` diz "nada solto aqui, mas tem 4 notas lá dentro", enquanto `[4]:[4]` diz "4 notas, e acabou". Pasta completamente vazia não mostra contador nenhum.

### O menu de comandos

O menu começa escondido, para não disputar espaço com o conteúdo.
Digite `?` (ou `Ctrl+0`, ou clique no botão `?` ao lado do campo) e ele aparece
logo abaixo do campo de comando; `?` de novo e ele some:

```
==============================================================
   C - Nova pasta        D - Deletar
   N - Nova nota         B - Buscar
   E - Editar nota       V - Voltar
   R - Renomear          M - Ir para a raiz
  ?? - Ajuda completa  sair - Encerrar
==============================================================
 ~ / Python / Pandas
==============================================================
 1 - Leitura de arquivos/                              [0]:[4]
 2 - Agrupamentos
 3 - Merge e join
==============================================================
```

### Filtrando

Digite qualquer texto que não seja um comando e dê Enter — o nível visível é filtrado pelo nome, ignorando acento e maiúsculas. `V` limpa o filtro.

```
digitou "agr"            →   1 - Agrupamentos
                             1 de 3 itens - V limpa o filtro
```

O filtro nunca sai do lugar: o breadcrumb continua o mesmo e os números passam a indexar a lista filtrada, então `1` abre o primeiro item **do que está na tela**.

Como as letras de comando continuam valendo, use a barra para filtrar por um termo que colida com elas: `/c` filtra por "c" em vez de criar uma pasta.

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
| `texto` | Filtra a pasta atual pelo nome — é só digitar e dar Enter |
| `/texto` | O mesmo, para termos que colidem com um comando (`/b`, `/c`, `/sair`) |
| `?` | Mostra ou esconde o menu de comandos (o mesmo que `Ctrl+0`) |
| `??` | Ajuda completa |
| `sair` | Encerra |

Comandos que agem sobre um item aceitam o número junto (`D3` apaga o item 3) ou sozinho (`D` pergunta qual).

### No editor

| Tecla | Ação |
|-------|------|
| `Ctrl+S` | Salva e volta |
| `Esc` | Cancela (pergunta antes de descartar) |
| `Ctrl+1` | Só o editor |
| `Ctrl+2` | Só o preview (do texto **ainda não salvo**) |
| `Ctrl+3` | Tela dividida: editor à esquerda, preview à direita |
| `Ctrl+E` | Alterna entre os três |

A tela só se divide durante a edição de uma nota. Em todo o resto do app, o terminal ocupa a tela inteira.

No modo dividido, o preview acompanha o que você digita (com uma pausa curta) e a rolagem segue o editor.

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
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -t .
```

Os testes rodam sem display, inclusive em CI.

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
- [PySide6](https://doc.qt.io/qtforpython/) — interface (Qt)
- [Markdown](https://python-markdown.github.io/) + [PyMdown Extensions](https://facelessuser.github.io/pymdown-extensions/) — renderização
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
