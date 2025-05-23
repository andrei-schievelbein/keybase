import customtkinter as ctk
import json
import os

CONFIG_FILE = 'config.json'

def carregar_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"width": 600, "height": 400, "x": 100, "y": 100}

def salvar_config():
    geom = root.geometry().replace('x', '+').split('+')
    config = {
        "width": int(geom[0]),
        "height": int(geom[1]),
        "x": int(geom[2]),
        "y": int(geom[3])
    }
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def executar_comando(event=None):
    comando = entrada.get()
    saida.insert("end", f"> {comando}\n")
    entrada.delete(0, "end")
    if comando.lower() == 'sair':
        salvar_config()
        root.destroy()
    else:
        saida.insert("end", f"Comando '{comando}' executado.\n")

config = carregar_config()

# Configurações globais
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

root = ctk.CTk()

# Definindo tamanho e posição da janela
root.geometry(f"{config['width']}x{config['height']}+{config['x']}+{config['y']}")

root.title("KeyBase CLI")
try:
    root.iconbitmap("keybase.ico")
except:
    pass  # Ignorar se não tiver ícone

# Campo de entrada no topo
entrada = ctk.CTkEntry(root, width=600, height=30)
entrada.pack(padx=10, pady=(10, 0), fill="x")

entrada.bind("<Return>", executar_comando)

# Caixa de saída (tipo terminal) abaixo
saida = ctk.CTkTextbox(root, height=300, width=600)
saida.pack(padx=10, pady=10, fill="both", expand=True)

saida.insert("end", "Bem-vindo ao KeyBase CLI!\nDigite 'sair' para encerrar.\n\n")

# ✅ Força o foco após a janela estar totalmente carregada
root.after(100, lambda: entrada.focus_set())

root.mainloop()