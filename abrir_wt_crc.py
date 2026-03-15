#abrir sistema
import pyautogui as py
import time
import pyscreeze
pyscreeze.USE_IMAGE_NOT_FOUND_EXCEPTION = False
# Configuração de segurança
py.FAILSAFE = True

def esperar_e_clicar(nome_imagem, mensagem, timeout=30, clicar=True, duplo=False):
    """
    timeout: Tempo máximo (em segundos) que o bot vai esperar a imagem aparecer.
    clicar: Se True, clica na imagem ao encontrar.
    duplo: Se True, executa um clique duplo.
    """
    inicio = time.time()
    print(f"Buscando: {nome_imagem}...")
    
    while True:
        posicao = py.locateCenterOnScreen(nome_imagem, confidence=0.7)
        
        if posicao:
            if clicar:
                if duplo:
                    py.click(posicao, clicks=2)
                else:
                    py.click(posicao)
            print(f"Sucesso: {mensagem}")
            return True
        
        # Verifica se o tempo de espera acabou
        if (time.time() - inicio) > timeout:
            print(f"Aviso: Tempo esgotado para {nome_imagem}")
            return False
        
        time.sleep(0.5) # Evita sobrecarregar o processador

# --- INÍCIO DO BOT ---
def abrir_sistema():
    # # 1. Login Inicial
    py.sleep(5)
    py.press('win')
    py.sleep(1)
    py.write('React')
    py.sleep(1)
    py.press('enter')

    # esperar_e_clicar('react.png', "Cliquei no React")
    py.sleep(1)
    sucesso_gerar = esperar_e_clicar('email.png', "Cliquei no React", timeout=10)
    if not sucesso_gerar:
        esperar_e_clicar('sair.png', 'Saindo', timeout=10)
        esperar_e_clicar('email.png', "Cliquei no React", timeout=10)
    py.write('leonardocampos@brcomercio.com.br')
    py.press('tab')
    py.write('Rigarr@2026@')
    py.sleep(1)
    esperar_e_clicar('btn_entrar.png', "Login realizado", timeout=10)
    py.sleep(1)
    # 2. Navegação CRC
    esperar_e_clicar('btn_crc.png', "Botão CRC clicado")
    py.sleep(3)

    sucesso_gerar = esperar_e_clicar('btn_abrir_computador.png', "Abrindo computador remoto")
    if not sucesso_gerar: 
        esperar_e_clicar('sessao_ativa.png', "Sessão ativa detectada!", timeout=5)
        esperar_e_clicar('continuar.png', "Sessão liberada")
    py.sleep(5)
    # 4. Abertura do Sistema WT

    sucesso_gerar = esperar_e_clicar('icone_wt_crc.png', "Ícone WT encontrado", timeout=10, duplo=True)
    py.sleep(3)
    sucesso_gerar = esperar_e_clicar('btn_executar.png', "Executando WT")
    py.sleep(2)
    if not sucesso_gerar:
        py.hotkey('alt', 'tab')
        esperar_e_clicar('btn_executar.png', "Executando WT")
    py.sleep(2)                              

    # py.click(x=1058,y=658)
    # if esperar_e_clicar('icone_wt.png', "Ícone WT encontrado", timeout=60, duplo=True):
    #     esperar_e_clicar('btn_executar.png', "Executando WT")        
        # O jeito correto:
    py.press('tab', presses=4, interval=0.1)
    py.write('LEONARDOCAMPOS')
    py.press('tab') # Adicionei o TAB para pular do usuário para a senha!
    py.write('BR@SIL32A')
    py.sleep(3)
    sucesso_gerar = esperar_e_clicar('btn_entrar_wt.png', "Entrando no WT", timeout=10, duplo=False)
    py.sleep(2)
    if not sucesso_gerar:
        py.hotkey('alt', 'tab')
        esperar_e_clicar('btn_entrar_wt.png', "Entrando no WT", timeout=10, duplo=False) 
    py.sleep(5)
    sucesso_gerar = esperar_e_clicar('tela_inicial_wt.png', "Tela inicial do WT detectada", timeout=15, clicar=False)
    if not sucesso_gerar:
        print("Erro: Não consegui entrar no WT. Verifique se as credenciais estão corretas e se o WT está respondendo.")

abrir_sistema()
