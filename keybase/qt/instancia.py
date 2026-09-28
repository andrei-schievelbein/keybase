"""Uma instancia so: a segunda abertura avisa a primeira e sai.

Duas janelas sobre a mesma base gravariam uma por cima da outra. Por isso o
app ouve num socket local; quem abre depois (o atalho do Karabiner, o terminal)
manda 'alternar' e encerra, e a janela aberta vem para a frente ou se esconde.

O socket e um arquivo com caminho fixo, e nao so um nome: assim o
abrir-keybase.sh fala com ele direto (nc -U), sem esperar o Python e o Qt
carregarem, e o atalho responde na hora.
"""

from pathlib import Path

from PySide6.QtNetwork import QLocalServer, QLocalSocket

CAMINHO_SOCKET = Path.home() / '.keybase' / 'instancia.sock'
MENSAGEM_ALTERNAR = b'alternar'
ESPERA_MS = 500


def avisar_instancia_aberta(caminho=CAMINHO_SOCKET):
    """Manda 'alternar' para o KeyBase ja aberto. False se nao ha nenhum."""
    socket = QLocalSocket()
    socket.connectToServer(str(caminho))
    if not socket.waitForConnected(ESPERA_MS):
        return False
    socket.write(MENSAGEM_ALTERNAR + b'\n')
    socket.waitForBytesWritten(ESPERA_MS)
    socket.disconnectFromServer()
    return True


def ouvir(caminho, ao_alternar, parent=None):
    """Passa a atender as proximas aberturas. Devolve o servidor (guarde-o:
    coletado pelo Python, ele para de ouvir)."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    # arquivo de um KeyBase que fechou com erro: ninguem ouve, e o listen
    # falharia com 'endereco em uso'
    QLocalServer.removeServer(str(caminho))

    servidor = QLocalServer(parent)

    def atender():
        while servidor.hasPendingConnections():
            conexao = servidor.nextPendingConnection()

            def ler(conexao=conexao):
                mensagem = bytes(conexao.readAll()).strip()
                if mensagem == MENSAGEM_ALTERNAR:
                    ao_alternar()
                conexao.disconnectFromServer()

            if conexao.bytesAvailable():
                ler()
            else:
                conexao.readyRead.connect(ler)
            conexao.disconnected.connect(conexao.deleteLater)

    servidor.newConnection.connect(atender)
    if not servidor.listen(str(caminho)):
        return None
    return servidor
