"""Esconder e ativar o app no macOS, pelo runtime do Objective-C via ctypes.

O Qt so esconde a janela. O que o atalho precisa e o Cmd+H de verdade:
[NSApp hide:], que devolve o foco ao app de antes, e o [NSApp activate...],
que traz o KeyBase para a frente vindo de outro app. Nada a instalar: o
libobjc e o AppKit ja estao carregados pelo Qt.

Fora do macOS, ou se algo falhar, as funcoes devolvem False e quem chama usa o
caminho do Qt.
"""

import ctypes
import ctypes.util
import sys

_runtime = None


def _objc():
    """(msg_send_objeto, msg_send_bool, NSApp) ou None."""
    global _runtime
    if _runtime is not None:
        return _runtime or None
    _runtime = False
    if sys.platform != 'darwin':
        return None
    try:
        lib = ctypes.cdll.LoadLibrary(ctypes.util.find_library('objc'))
        lib.objc_getClass.restype = ctypes.c_void_p
        lib.objc_getClass.argtypes = [ctypes.c_char_p]
        lib.sel_registerName.restype = ctypes.c_void_p
        lib.sel_registerName.argtypes = [ctypes.c_char_p]
        # objc_msgSend e variadico: no arm64 precisa de um prototipo por
        # assinatura, senao os argumentos chegam errados
        envio = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(
            ('objc_msgSend', lib))
        com_objeto = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                                      ctypes.c_void_p)(('objc_msgSend', lib))
        com_bool = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                                    ctypes.c_bool)(('objc_msgSend', lib))
        classe = lib.objc_getClass(b'NSApplication')
        if not classe:
            return None
        nsapp = envio(classe, lib.sel_registerName(b'sharedApplication'))
        if not nsapp:
            return None
        _runtime = (lib.sel_registerName, com_objeto, com_bool, nsapp)
    except (OSError, AttributeError, TypeError):
        _runtime = False
        return None
    return _runtime


def esconder_app():
    """Cmd+H: esconde o app e o foco volta ao anterior."""
    rt = _objc()
    if rt is None:
        return False
    seletor, com_objeto, _, nsapp = rt
    com_objeto(nsapp, seletor(b'hide:'), None)
    return True


def ativar_app():
    """Traz o app para a frente, vindo de outro app."""
    rt = _objc()
    if rt is None:
        return False
    seletor, com_objeto, com_bool, nsapp = rt
    com_objeto(nsapp, seletor(b'unhide:'), None)   # desfaz um hide: anterior
    com_bool(nsapp, seletor(b'activateIgnoringOtherApps:'), True)
    return True
