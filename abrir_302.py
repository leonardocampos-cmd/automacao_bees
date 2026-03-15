#CADASTRAR RJ
import pyautogui as py
import time
from winotify import Notification, audio
import pyscreeze
pyscreeze.USE_IMAGE_NOT_FOUND_EXCEPTION = False
# Configuração de segurança
py.FAILSAFE = True
# Tempo de espera entre ações
TEMPO_PADRAO_ESPERA = 0.1

# Mapeamento das ações na tela
MAPA_ACOES = [
    ('NOME', 'escrever'),
    ('NOME FANTASIA', 'escrever'),
    (None, 'tab'),
    ('CNPJ', 'escrever'),
    ('INSCRIÇÃO ESTADUAL NÚMERO', 'escrever'),
    ('CODATIV', 'escrever'),
    ('CODPRACA', 'escrever'),
    (None, 'tab'), (None, 'tab'), (None, 'tab'), (None, 'tab'),
    ('CEP_x', 'escrever'),
    (None, 'clicar_botao_cep'),
    (None, 'clique_duplo_endereco'),
    (None, 'cima'), (None, 'cima'), (None, 'cima'), (None, 'cima'),
    ('RUA', 'escrever'),
    ('NÚMERO', 'escrever'),
    ('BAIRRO', 'escrever'),
    (None, 'tab'), (None, 'tab'),
    ('PAÍS', 'escrever'),
    ('TELEFONE', 'escrever'),
    ('COMPLEMENTO', 'escrever'),
    ('EMAIL', 'escrever'),
    ('EMAIL', 'escrever'),
    (None, 'clicar_validacao_endereco'),
    (None, 'esquerda'),
    (None, 'enter'), (None, 'enter'),
    (None, 'enter'), (None, 'enter'), (None, 'enter'), (None, 'enter'),(None, 'enter'),
    ('EMAIL', 'escrever'),  
    (None, 'enter'), (None, 'enter'),
    (None, 'enter'), (None, 'enter'),
    ('CEP_y', 'escrever'),
    (None, 'clicar_botao_cep2'),
    (None, 'clique_duplo_endereco'),
    (None, 'clicar_validacao_endereco2'),
    (None, 'esquerda'),
    (None, 'enter'),
    (None, 'cima'), (None, 'cima'), (None, 'cima'), (None, 'cima'),
    ("Número", 'escrever'),
    ('Bairro', 'escrever'),
    (None, 'enter'), (None, 'enter'),   
    ('Rua', 'escrever'),
    # ('COMPLEMENTO', 'escrever'),
    # ('CNPJ', 'escrever'),
    (None, 'enter'), (None, 'enter'),(None, 'enter'),
    ('RCA', 'escrever'),
    (None, 'enter'), (None, 'enter'),
    ('TIPO EMPRESA', 'escrever'),
    (None, 'enter'),
    (None, 'sim'),
    (None, 'enter'), (None, 'enter'),(None, 'enter'), (None, 'enter'),(None, 'enter'),
    (None, 'sim'),
    (None, 'enter'),
    (None, 'salvar'),
    (None, 'esquerda'),
    (None, 'enter'),
    (None, 'novo'),
]
def esperar_e_clicar(nome_imagem, mensagem, timeout=30, clicar=True, duplo=False):
    """
    timeout: Tempo máximo (em segundos) que o bot vai esperar a imagem aparecer.
    clicar: Se True, clica na imagem ao encontrar.
    duplo: Se True, executa um clique duplo.
    """
    inicio = time.time()
    print(f"Buscando: {nome_imagem}...")
    
    while True:
        posicao = py.locateCenterOnScreen(nome_imagem, confidence=0.9)
        
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
def executar_acao(tipo_acao, valor=None, field_name=None):
    if tipo_acao == 'escrever':
        if isinstance(valor, str):
            if field_name == 'CEP':
                valor = valor.zfill(8)
            elif field_name == 'CNPJ':
                valor = valor.zfill(14)
        py.write(str(valor).strip())
        py.press('tab')
    else:
        mapping = {
            'tab': lambda: py.press('tab'),
            'cima': lambda: py.press('up'),
            'enter': lambda: py.press('enter'),
            'esquerda': lambda: py.press('left'),
            'novo': lambda: py.hotkey('ctrl', 'n'),
            'salvar': lambda: py.hotkey('ctrl', 's'),
            'sim': lambda: py.write('s'),
            'clicar_botao_cep': lambda: py.click(x=1310, y=640),
            'clicar_botao_cep2': lambda: py.click(x=1308, y=647),
            'clique_duplo_endereco': lambda: py.click(x=1085, y=436, clicks=2),
            'clicar_validacao_endereco': lambda: py.click(x=1306, y=679),
            'clicar_validacao_endereco2': lambda: py.click(x=1304, y=668),
        }  
        action = mapping.get(tipo_acao)
        if action:
            action()
    time.sleep(TEMPO_PADRAO_ESPERA)

    
def abrir_rotina():
    esperar_e_clicar('rotina_302.png','Rotina 302, Iniciada',timeout=10)
    py.sleep(2)
    esperar_e_clicar('novo_cadastro.png','Novo Cadastro, Iniciada',timeout=20)
    py.sleep(2)
    sucesso_gerar = esperar_e_clicar('check_marcado.png', 'Check Já Marcado',timeout=5)
    print("Marcado")
    if not sucesso_gerar:
        esperar_e_clicar('check.png', 'Check Marcado',timeout=5)
        print("Não apareceu, seguindo outra lógica...")
    #-------- INÍCIO DA EXECUÇÃO ----------

if __name__ == "__main__":
    try:
        print("Você tem 5 segundos para abrir o sistema de cadastro...")
        time.sleep(5)
        abrir_rotina()
        # Carrega o arquivo CSV de CNPJs
        arquivo_csv = "relatorios/Pedidos_A_Preparar_Rigarr.csv"
        arquivo_cnpjs = pd.read_csv(arquivo_csv, dtype=str)
        for idx, linha in arquivo_cnpjs.iterrows():
            print(f"Processando cadastro {idx + 1}/{len(arquivo_cnpjs)}...")
            dados = linha.to_dict()

            for nome_campo, acao in MAPA_ACOES:
                if acao == 'escrever':
                    valor = dados.get(nome_campo, '')
                    executar_acao(acao, valor, nome_campo)
                else:
                    executar_acao(acao)

            time.sleep(1.5)

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        py.hotkey('alt', 'tab')
        notificacao = Notification(
            app_id="Cadastro Automático",
            title="Processo Finalizado",
            msg="Todos os cadastros foram realizados com sucesso!",
            duration='long',
            icon=r"C:\Users\LeonardoCampos\Documents\Imagem1.jpg"
        )
        notificacao.set_audio(audio.LoopingAlarm, loop=False)
        notificacao.show()
        import pyttsx3

        # Inicializa o mecanismo de voz
        engine = pyttsx3.init()

        # Ajustes opcionais
        engine.setProperty('rate', 180)     # velocidade da fala
        engine.setProperty('volume', 1.0)   # volume (0.0 a 1.0)

        # Frase a ser falada
        frase = "Oi! Eu sou sua assistente em Python."

        # Reproduz o áudio
        engine.say(frase)
        engine.runAndWait()

