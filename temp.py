import json
import os

data = {"teste": "valor"}

# Altere o caminho para um local temporário fora do OneDrive
# Certifique-se de que o diretório exista ou crie-o
output_path = "C:\\temp\\data.json" # Exemplo para Windows
# Se C:\temp não existir, você pode criar: os.makedirs("C:\\temp\\", exist_ok=True)

print("Diretório atual de execução:", os.getcwd())
print("Caminho absoluto de data.json (original):", os.path.abspath('data.json'))
print("Tentando salvar em:", output_path)

try:
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f)
        f.flush()
        os.fsync(f.fileno())
    print(f"Escreveu! Arquivo deveria estar em: {output_path}")
except IOError as e:
    print(f"Erro de I/O ao escrever o arquivo: {e}")
except Exception as e:
    print(f"Ocorreu um erro inesperado: {e}")