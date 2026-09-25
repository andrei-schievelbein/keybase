"""Modelos de nota: notas comuns numa pasta da raiz (padrao "Modelos"). Sem Qt.

Nao ha formato novo: um modelo e uma nota como outra qualquer, editada com E.
Ao criar uma nota com N, os modelos sao oferecidos, e {nome} e {data} no texto
do modelo sao preenchidos. str.replace, e nao str.format: modelo de codigo
cheio de chaves ({ "a": 1 }) nao pode quebrar.
"""

from datetime import date

from .model import File, Folder
from .tree import filhos_ordenados, normalizar


def pasta_de_modelos(raiz, nome):
    """A pasta de modelos, na raiz, pelo nome (sem caixa e acento), ou None."""
    if not nome:
        return None
    alvo = normalizar(nome)
    for filho in raiz.filhos or ():
        if isinstance(filho, Folder) and normalizar(filho.nome) == alvo:
            return None if filho.trancada else filho
    return None


def modelos(raiz, nome):
    """Notas da pasta de modelos com o texto disponivel (trancadas ficam de fora)."""
    pasta = pasta_de_modelos(raiz, nome)
    if pasta is None:
        return []
    return [n for n in filhos_ordenados(pasta)
            if isinstance(n, File) and n.conteudo is not None]


def preencher(texto, nome, hoje=None):
    hoje = hoje or date.today()
    return (texto.replace("{nome}", nome)
                 .replace("{data}", hoje.strftime("%d/%m/%Y")))


#: a nota que acompanha toda pasta de modelos nova: um tour pelo markdown
#: que o viewer desenha (ver EXTENSOES em qt/render/pipeline.py)
NOME_EXEMPLO = "KeyBase Markdown"

CONTEUDO_EXEMPLO = '''\
# {nome}

Criada em {data}.

Este é um modelo. Ao criar uma nota com N e escolher "KeyBase Markdown", o título acima vira o nome da nota nova, e a data, a de hoje. Edite com E para ver o markdown por trás de cada trecho.

[TOC]

## Texto

Texto em **negrito**, em *itálico*, em ***negrito e itálico*** e ~~riscado~~. Código no meio da frase: `git status`.

Uma quebra de linha digitada
aparece como quebra de linha.

## Títulos

### Título de nível 3
#### Título de nível 4

## Listas

- Item
- Outro item
  - Item dentro de item
  - Mais um

1. Primeiro passo
2. Segundo passo
3. Terceiro passo

## Tarefas

- [x] Tarefa feita
- [ ] Tarefa pendente

## Citação

> Uma citação, para destacar um trecho.
> Pode ter mais de uma linha.

## Tabela

| Comando | O que faz | Onde |
|:--------|:---------:|-----:|
| `N` | Cria uma nota | Lista |
| `E` | Edita a nota | Nota |
| `Y2` | Copia o 2º bloco de código | Nota |

## Blocos de código

Com a linguagem depois das crases, o código ganha cores. Na nota, Y1 copia o primeiro bloco, Y2 o segundo, e Y sozinho lista os blocos.

```python
def saudacao(quem):
    return "Olá, " + quem + "!"
```

```bash
ls -la ~/Downloads
```

```sql
SELECT nome, criado_em FROM notas WHERE favorito = 1;
```

## Links

Link para a web com texto: [um site de exemplo](https://example.com). Ou só o endereço: https://example.com

Link para outra nota: [[Modelos/KeyBase Markdown|esta própria nota]].
Um link para uma nota que não existe aparece riscado: [[Nota que não existe]].

## Nota de rodapé

Uma frase com uma nota de rodapé.[^1]

[^1]: O texto da nota de rodapé aparece no fim da nota.

---

Uma linha com três hífens, como a de cima, separa seções.
'''


def criar_exemplo(pasta):
    """Poe o modelo de exemplo numa pasta de modelos recem-criada.

    Em claro mesmo que a pasta nasca cifrada: e texto de documentacao, sem nada
    do usuario, e cifrar exigiria o cofre destravado no meio da criacao.
    """
    from .tree import adicionar, novo_file
    # o link para si mesma segue o nome da pasta, que e configuravel
    conteudo = CONTEUDO_EXEMPLO.replace("[[Modelos/", f"[[{pasta.nome}/")
    nota = novo_file(NOME_EXEMPLO, conteudo)
    adicionar(pasta, nota)
    return nota
