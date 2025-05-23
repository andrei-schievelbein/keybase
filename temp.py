import PySimpleGUI as sg

layout = [[sg.Text('KeyBase')], [sg.Button('Rodar')], [sg.Button('Sair')]]
window = sg.Window('KeyBase', layout)

while True:
    event, values = window.read()
    if event == sg.WINDOW_CLOSED or event == 'Sair':
        break
    if event == 'Rodar':
        # chamar sua função principal
        main()

window.close()
