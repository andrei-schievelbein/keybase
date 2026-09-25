"""A nota "Keybase Doc": o manual do KeyBase, dentro do proprio KeyBase. Sem Qt.

Criada na raiz uma unica vez (ver App.garantir_doc). Depois e uma nota como
outra qualquer: o usuario edita ou apaga, e o app nao a recria nem atualiza.

Paragrafos numa linha so: o nl2br do render mostra cada quebra digitada.
"""

NOME_DOC = "Keybase Doc"

CONTEUDO_DOC = '''\
# Keybase Doc

O manual do KeyBase, dentro do próprio KeyBase. Esta nota é sua: edite com E, mova com X ou apague com D. Ela não volta sozinha depois de apagada.

[TOC]

## O que é o KeyBase

Um lugar para guardar referências rápidas: atalhos de teclado, comandos, trechos de código, anotações. Tudo o que você consulta no dia a dia.

Existem só dois tipos de item:

- **Pasta**: agrupa notas e outras pastas, sem limite de profundidade.
- **Nota**: um texto em Markdown.

Não há tipos fixos de conteúdo. Um "snippet" é uma nota com um bloco de código; um "atalho" é uma nota com a combinação de teclas no título. A organização é sua.

## A tela

O KeyBase é operado pelo teclado. Digite o comando na barra de cima e aperte ENTER.

```
==============================================================
 ~ / Python / Pandas
==============================================================
 1 - Leitura de arquivos/                              [0]:[4]
 2 - Agrupamentos
 3 - Merge e join
==============================================================
```

- A primeira linha é o caminho. `~` é a raiz.
- Pastas terminam em `/`. As pastas vêm antes das notas, e cada grupo fica em ordem alfabética. A ordem não se muda à mão.
- Os avisos ("Pasta criada.", "Renomeado para...") aparecem no lugar do caminho por alguns segundos.

### Os dois números da pasta

Cada pasta mostra `[a]:[b]`, contando só notas:

- **a**: notas soltas dentro da pasta;
- **b**: todas as notas da hierarquia, entrando em cada sub-pasta.

`[0]:[4]` quer dizer "nada solto aqui, mas 4 notas lá dentro". Pasta vazia não mostra contador.

### Marcas no fim da linha

| Marca | Significado |
|:------|:------------|
| `[favorito]` | Marcado com F |
| `[cifrada]` | Nota ou pasta inteira protegida pela senha mestra |
| `[novas cifradas]` | Pasta cujas notas novas já nascem cifradas |

### O menu de comandos

O menu começa escondido. `?` (ou Ctrl+0, ou o botão `?` ao lado da barra) mostra e esconde. `??` abre a ajuda completa.

## Navegação

| Comando | O que faz |
|:--------|:----------|
| `1` `2` `3` … | Abre o item pelo número |
| `V` | Volta um nível (ou limpa o filtro) |
| ENTER vazio | O mesmo que V |
| `M` | Vai direto para a raiz |
| `L` | Favoritos e notas abertas recentemente, numa lista só |
| `sair` | Encerra (fechar a janela também salva) |

## Criar e organizar

| Comando | O que faz |
|:--------|:----------|
| `P` | Cria uma pasta na pasta atual |
| `N` | Cria uma nota na pasta atual e já abre o editor |
| `E` ou `E3` | Edita uma nota |
| `R` ou `R3` | Renomeia um item |
| `D` ou `D3` | Apaga um item (pede confirmação) |
| `X` ou `X3` | Move um item para outra pasta |
| `Y` ou `Y3` | Copia um item para outra pasta; o original fica |
| `Z` ou `Z3` | Duplica um item como "Nome (cópia)" |
| `F` ou `F3` | Marca ou desmarca um favorito |
| `W` ou `W3` | Exporta a pasta como arquivos .md |
| `U` | Desfaz a última ação |

Comandos que agem sobre um item aceitam o número junto (`D3` apaga o item 3) ou sozinho (`D` pergunta qual).

### Apagar

Apagar uma nota ou uma pasta vazia pede uma confirmação simples. Uma pasta com conteúdo mostra quanto vai junto, exige digitar DELETAR e grava um backup antes. Nos dois casos, U desfaz.

### Mover e copiar para outra pasta

X e Y abrem uma tela para escolher o destino. O menu fica fixo no topo:

| Tecla | Ação |
|:------|:-----|
| número | Entra na pasta |
| `C` | Move (ou copia) para a pasta mostrada |
| ENTER | Sobe um nível |
| `M` | Vai para a raiz |
| ESC | Cancela |

Mover para dentro de uma pasta cifrada deixa o item protegido por ela. Mover para fora pede confirmação, porque o item passa a ficar em claro.

### Desfazer

U desfaz a última ação: apagar, mover, renomear, duplicar, decifrar ou restaurar uma versão. Dá para desfazer várias em sequência, enquanto nada mais tiver sido alterado depois.

### Exportar

W exporta a pasta atual (ou W3, a pasta 3) como arquivos .md, numa pasta `KeyBase-export-AAAA-MM-DD` em Downloads. Na raiz, exporta tudo. Se houver itens cifrados, o KeyBase pergunta se pula ou inclui em claro.

## Filtrar e buscar

### Filtro na pasta atual

A partir da segunda letra digitada na barra, a pasta já é filtrada pelo nome, sem ENTER e sem diferenciar acento e maiúsculas. Uma letra só não filtra, para não se confundir com um comando, e texto com número (`D3`, `12`) também não.

- ENTER fixa o filtro e limpa a barra. Os números passam a indexar a lista filtrada: `1` abre o primeiro item filtrado.
- ESC apaga o que está na barra, e a lista volta.
- Digitar com um filtro já fixado filtra a pasta inteira de novo. Apagar tudo volta ao filtro fixado.
- V limpa o filtro fixado.

Para filtrar por algo que é um comando, comece com barra: `/c` filtra por "c" em vez de abrir a configuração, e `/sair` não encerra.

### Busca em toda a base

B busca pelo nome, pela descrição e pelo conteúdo das notas, em todas as pastas. Cada resultado mostra o caminho.

- O termo precisa de pelo menos 2 letras.
- Tolera erro de digitação no nome: "pnadas" acha "Pandas".
- As setas escolhem um resultado e ENTER abre. Um número também abre.
- Com os itens cifrados trancados, notas cifradas são achadas só pelo nome, e nada dentro de pastas cifradas aparece.

## Notas

### Ler

Abrir uma nota mostra o Markdown já desenhado. Nela valem:

| Comando | O que faz |
|:--------|:----------|
| `E` | Edita |
| `R` | Renomeia |
| `D` | Apaga |
| `Y` | Área de transferência (veja abaixo) |
| `H` | Histórico de versões |
| `F` | Favorito |
| `K` | Cifra ou decifra |
| `A` | Digita a senha de uma nota trancada |
| `V` ou ENTER | Volta |

### Copiar para a área de transferência

- `Y2` copia o 2º bloco de código da nota.
- `Y` sozinho lista os blocos de código; `0` copia a nota inteira. Uma nota sem blocos é copiada inteira.
- Algo cifrado copiado é apagado da área de transferência depois de 20 segundos (configurável), se ela ainda tiver o que foi copiado.

### Histórico

H lista as versões da nota guardadas nos backups e snapshots, sem repetir iguais. Abra uma para ler e aperte R para restaurá-la. U desfaz a restauração.

### Editor

| Tecla | Ação |
|:------|:-----|
| Ctrl+S | Salva e volta |
| ESC | Vai para a barra de cima; ESC de novo cancela (pergunta antes de descartar) |
| ENTER na barra | Volta ao texto |
| Ctrl+1 | Só o editor |
| Ctrl+2 | Só o preview do texto ainda não salvo |
| Ctrl+3 | Tela dividida: editor e preview lado a lado |
| Ctrl+E | Alterna entre os três modos |
| `?` na barra | Mostra ou esconde os atalhos de edição |
| `??` na barra | Ajuda completa, sem perder o texto |

No modo dividido, o preview acompanha a digitação e a rolagem segue o editor. O KeyBase lembra o último modo usado.

No macOS, tanto o Ctrl quanto o Cmd funcionam nesses atalhos.

### Modelos

Modelos são notas comuns numa pasta `Modelos` na raiz. Ao criar uma nota com N, o KeyBase oferece `1 - Em branco` e os modelos. No texto do modelo, `{nome}` vira o nome da nota nova e `{data}`, a data de hoje.

- Se a pasta ainda não existe, o N oferece `2 - Criar a pasta de modelos`.
- Toda pasta de modelos nova já vem com o modelo "KeyBase Markdown", um tour por tudo o que o Markdown do KeyBase desenha.
- Criar uma nota dentro da própria pasta de modelos cria um modelo novo, sem perguntar.
- O nome da pasta é configurável em `pasta_modelos`.

## Markdown

As notas são escritas em Markdown. O modelo "KeyBase Markdown", na pasta de modelos, mostra cada recurso funcionando.

| Recurso | Como escrever |
|:--------|:--------------|
| Título | `# Título`, `## Seção`, `### Sub-seção` |
| Negrito, itálico | `**negrito**`, `*itálico*` |
| Riscado | `~~riscado~~` |
| Código no texto | `` `comando` `` |
| Lista | `- item`, ou `1. passo` |
| Tarefa | `- [ ] pendente`, `- [x] feita` |
| Citação | `> texto` |
| Tabela | linhas com `|`, e `|:--|` para alinhar |
| Linha horizontal | `---` |
| Nota de rodapé | `texto[^1]` e, no fim, `[^1]: explicação` |
| Sumário | `[TOC]` numa linha sozinha |

Uma quebra de linha digitada aparece como quebra de linha. O `#` precisa de espaço depois para virar título: `#!/bin/bash` e `#config` ficam como texto.

### Blocos de código

Três crases com o nome da linguagem abrem um bloco com cores:

````markdown
```python
df = pd.read_csv("dados.csv")
```
````

Qualquer linguagem do Pygments funciona: python, bash, sql, json, yaml, javascript e muitas outras.

### Links

- `https://...` abre no navegador. `[texto](https://...)` mostra o texto no lugar do endereço.
- `[[Nome da nota]]` vira link para outra nota. Também valem `[[Pasta/Nome]]` e `[[Pasta/Nome|texto mostrado]]`.
- Um link para uma nota que não existe aparece riscado.

Link para este manual: [[Keybase Doc]].

## Notas e pastas cifradas

Você escolhe o que cifrar. Tudo fica protegido por uma senha mestra única (AES-256-GCM, com a chave derivada da senha por scrypt).

> **Não existe recuperação de senha.** Sem a senha mestra, o que foi cifrado fica ilegível para sempre.

### Três níveis de proteção

| Nível | Como ligar | O que fica visível no arquivo |
|:------|:-----------|:------------------------------|
| Nota cifrada | K sobre a nota | O nome da nota |
| Pasta com notas novas cifradas | K sobre a pasta, opção 2, ou `s` ao criar com P | Os nomes e as notas antigas |
| Pasta inteira cifrada | K sobre a pasta, opção 3 | Só o nome da pasta |

### Comandos

| Comando | O que faz |
|:--------|:----------|
| `K` ou `K3` | Cifra ou decifra uma nota; decifrar pede confirmação |
| `K` numa pasta | 1 cifra todas as notas dela, 2 liga ou desliga "novas cifradas", 3 cifra a pasta inteira |
| `T` | Tranca os itens cifrados; se já estiverem trancados, pede a senha |
| `A` | Na nota trancada, pede a senha |
| `S` | Troca a senha mestra |

### Como funciona no dia a dia

- Na primeira vez que você cifra algo, o KeyBase pede para criar a senha mestra.
- A senha é pedida uma vez por sessão. Depois de 10 minutos sem uso (configurável), tudo tranca de novo.
- Dentro de uma pasta cifrada, tudo já é protegido: nada lá dentro pede senha de novo, e o K não cifra nada a mais.
- Trocar a senha com S não recifra as notas. Backups antigos continuam abrindo com a senha antiga.
- Ao cifrar, os backups ainda guardam a versão em claro. O KeyBase oferece cifrar essas cópias também, sem perder o histórico.

## Configuração

C abre o arquivo `keybase_config.toml` no editor, como uma nota. Ctrl+S valida antes de gravar: com erro, nada é gravado e o erro aparece em vermelho no topo. O KeyBase nunca reescreve esse arquivo sozinho, então seus comentários ficam.

| Opção | O que faz | Quando vale |
|:------|:----------|:------------|
| `tema` | `"dark"` ou `"light"` | Na hora |
| `[fontes]` | Família e tamanhos das fontes | Ao reabrir |
| `altura_ajuda` | Altura mínima da barra de ajuda | Na hora |
| `tempo_aviso_ms` | Quanto tempo um aviso fica no lugar do caminho | Na hora |
| `tempo_aviso_longo_ms` | O mesmo, para avisos com algo para ler, como o endereço de uma exportação. `0` deixa o aviso até você apertar ENTER | Na hora |
| `trancar_apos_min` | Minutos sem uso até os cifrados trancarem (`0` desliga) | Na hora |
| `limpar_copia_seg` | Segundos até limpar algo cifrado copiado (`0` não limpa) | Na hora |
| `[dados] pasta` | Onde ficam os dados | Ao reabrir |
| `pasta_modelos` | Nome da pasta de modelos na raiz (`""` desliga) | Na hora |

Opções novas de versões futuras aparecem sozinhas no editor, com o comentário, e só vão para o arquivo quando você salvar.

## Dados e segurança

### Onde ficam os arquivos

Os dados ficam ao lado do programa, então o KeyBase roda de um pen drive. Se essa pasta não aceitar gravação, eles vão para a pasta de dados do usuário.

| Arquivo | O que é |
|:--------|:--------|
| `keybase_data.json` | Suas pastas e notas |
| `keybase_data.bak.json` | A versão anterior, gravada antes de cada alteração |
| `keybase_data.snapshot-*.json` | Uma cópia por dia, dos últimos 7 dias |
| `keybase_config.toml` | Suas preferências |
| `keybase_estado.json` | Tamanho da janela, último modo do editor e notas recentes |
| `keybase_data.conflito-*.json` | Suas mudanças, quando outro computador gravou ao mesmo tempo |

### Vários computadores

Aponte `[dados] pasta` para uma pasta do iCloud, Dropbox ou Google Drive. Na primeira vez, os dados atuais são copiados para lá. No Windows, use `/` no caminho: `"C:/Users/voce/Dropbox"`.

Se outro computador gravou enquanto este estava aberto, o KeyBase não sobrescreve: guarda as suas mudanças numa cópia de conflito e pergunta se recarrega o do disco ou grava o daqui por cima.

### Se algo der errado

- Toda gravação é atômica: uma queda no meio não deixa o arquivo pela metade.
- Um arquivo de dados que não pôde ser lido nunca é sobrescrito. O KeyBase abre sem gravar nada, mostra o erro e oferece restaurar o backup ou um snapshot.
- Uma configuração inválida ao abrir faz o KeyBase usar os padrões e avisar, sem mexer no arquivo. Corrija com C.

## Dicas

- Nomeie notas de atalho pela combinação: uma nota "Ctrl + P" dentro de `Vscode/` se acha pelo filtro digitando só "ctrl".
- Guarde comandos em blocos de código: na nota, Y1 copia o primeiro sem precisar selecionar nada.
- Use F nas notas que você abre toda hora e L para chegar nelas de qualquer lugar.
- Crie modelos para o que você repete: um modelo de atalho com `# {nome}` e "Quando usar:" padroniza as notas.
- Ligue notas relacionadas com `[[Nome da nota]]` relacionadas em vez de repetir o mesmo texto em dois lugares.
- Errou? U desfaz. Perdeu um texto que existia antes? H na nota mostra as versões antigas.
- Cifre só o que é sensível. O que está em claro continua aparecendo na busca pelo conteúdo.
'''
