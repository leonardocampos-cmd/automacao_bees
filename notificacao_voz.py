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

