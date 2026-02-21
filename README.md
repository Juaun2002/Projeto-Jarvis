```
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓
▓░  ▄▄▄▄░▄▀▀░░▄███▄░░░▄▀▀░░░▄▀▀▄░░▀░░░░░▄▀▀▀▄░   ▀░░▄▄░░░░░░░▄███▄░▀░▀░░▄▀▀░░▄██▀▀▀░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓
▓░  █░░░█░░░░█░░░░▀░▀░░░░░░█░░░█░░░░░░▀▀▀▀▀░░██░░░░░░░░░░░█░░░░░░░░░░█░░░░░░░░█░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓
▓░  ▀▀▀▀░▄▀▀░░▀███░░░▀▄▄▄░░░▀▄▄░░░░▄▀░░░░░░░░░░░░░░░░░░░░░░▀███░░░░░░░░▀▀█▄░░▀███▀░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓
▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░▓
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
```

# 🎤 JARVIS - Assistente Virtual Inteligente

Um assistente virtual completo em português com reconhecimento de voz, síntese inteligente de fala e capacidades de automação offline + cloud.

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Arquitetura](#arquitetura)
- [Componentes Principais](#componentes-principais)
- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Como Usar](#como-usar)
- [Funcionalidades](#funcionalidades)
- [Configuração](#configuração)
- [Estrutura do Projeto](#estrutura-do-projeto)

---

## 🎯 Visão Geral

**JARVIS** é um assistente de voz modular que funciona totalmente offline para reconhecimento e síntese, com opção de IA na nuvem via **Groq** para respostas inteligentes. Combina o melhor das soluções open-source:

- 🎙️ **Reconhecimento de Voz**: Vosk (offline, português)
- 🔊 **Síntese de Fala**: Piper (neural, natural) + Windows Speech (fallback)
- 🧠 **IA**: Groq Llama (nuvem, rápido e gratuito)
- 🎯 **Detecção de Hotword**: OpenWakeWord (detector dedicado, alta precisão)
- 🖱️ **Controle por Gestos**: OpenCV (reconhecimento de mão)
- 💾 **Memória**: Persistência de contexto e preferências do usuário

---

## 🏗️ Arquitetura

```
┌─────────────────┐
│  Microfone      │
└────────┬────────┘
         │
    ┌────▼────────────────────────────────┐
    │   HOTWORD DETECTOR (OpenWakeWord)   │  <- Escuta "Olá", "Jarvis"
    └────┬───────────────────────────────┘
         │ [hotword detectada]
         │
    ┌────▼──────────────────────┐
    │   STT (Vosk)              │  <- Converte fala → texto
    └────┬──────────────────────┘
         │
    ┌────▼──────────────────────┐
    │   PROCESSAMENTO DE TEXTO  │
    │  - Normalização           │
    │  - Detecção de Comando    │
    │  - Análise de Tom         │
    └────┬──────────────────────┘
         │
    ┌────▼────────────────────────────────┐
    │  AÇÃO ou IA?                        │
    └────┬──────────┬─────────────────────┘
         │          │
    ┌────▼──────┐ ┌▼──────────────────┐
    │ ACTIONS   │ │ BRAIN (Groq)      │
    │ - Abrir   │ │ - Respostas       │
    │ - Pesq.   │ │ - Contexto        │
    │ - Nota    │ │ - Memória         │
    └────┬──────┘ └┬──────────────────┘
         │        │
         └────┬───┘
              │
         ┌────▼──────────────────────┐
         │   TTS (Piper / Windows)   │  <- Converte texto → fala
         └────┬──────────────────────┘
              │
         ┌────▼────────────────┐
         │  Alto-falante       │
         └─────────────────────┘
```

---

## 🔧 Componentes Principais

### 1. **main_vosk.py** - Orquestrador Central
- Loop principal da aplicação
- Gerencia fluxo de conversação e continuidade
- Detecta frases de encerramento ("obrigado", "valeu", etc.)
- Gerencia tom formal/informal
- Controle de gestos

### 2. **wakeword_openwakeword.py** - Detector de Hotword
- Baseado em OpenWakeWord (modelos neurais pré-treinados)
- Detecta "Olá", "Jarvis" e variações
- Limiar configurável (OWW_THRESHOLD)
- VAD (Voice Activity Detection) incorporado

### 3. **stt_vosk.py** - Reconhecimento de Voz
- Motor offline em português
- Processa áudio em tempo real
- Retorna texto reconhecido

### 4. **tts.py** - Síntese de Fala
- **Backend principal**: Piper (voz neural natural)
- **Backend fallback**: Windows Speech ou pyttsx3
- Configurações:
  - `PIPER_LENGTH_SCALE`: Controla velocidade (padrão: 1.05)
  - `PIPER_NOISE_SCALE`: Variabilidade (padrão: 0.55)
  - `PIPER_NOISE_W`: Ruído (padrão: 0.72)

### 5. **brain.py** - IA Inteligente
- Integração com Groq API (LLaMA)
- Mantém contexto da conversa
- Carrega memória do usuário

### 6. **actions.py** - Executor de Comandos
- Abre aplicativos (Chrome, WhatsApp)
- Executa pesquisas web
- Cria/lê notas
- Controla volume e tela
- Agenda desligamento do PC

### 7. **jarvis_ui.py** - Interface Gráfica (PyQt6)
- Visualização em tempo real do espectro de áudio
- Log da conversa
- Status do sistema
- Indicador de voz/áudio

### 8. **personality.py** - Persona do Assistente
- Respostas personalizadas e naturais
- Diferentes tons (formal/informal)
- Frases de saudação, confusão, etc.

### 9. **interrupt_listener.py** - Controle de Parada
- Detecta comando "Pare" em tempo real
- Interrompe síntese de fala imediatamente
- Toggle de mute

### 10. **gesture_control.py** - Reconhecimento de Gestos
- Webcam + OpenCV
- Reconhece gestos de mão:
  - Punho: Ativar Jarvis
  - 1 dedo: "Sim chefe"
  - 2 dedos: "Volume +"
  - 3 dedos: "Volume -"
  - Mão aberta: "OK"

---

## 📋 Requisitos

### Sistema
- Python 3.11+
- Windows 10+ (testado em Windows 11)
- Microfone conectado
- Câmera (opcional, para gestos)

### Dependências Principais
```
PyQt6==6.10.0              # Interface gráfica
vosk==0.3.45               # STT offline
sounddevice==0.5.3         # Captura de áudio
openwakeword==0.6.0        # Detector de hotword
piper-tts==1.3.0           # Síntese neural
pyttsx3==2.99              # TTS fallback
pyautogui==0.9.54          # Automação de teclado/mouse
psutil==6.1.1              # Info do sistema
opencv-python==4.13.0      # Visão computacional
numpy==2.4.2               # Computação numérica
pyqtgraph==0.14.0          # Gráficos
python-dotenv==1.2.1       # Variáveis de ambiente
```

---

## 💾 Instalação

### 1. Clone o repositório
```bash
git clone https://github.com/Juaun2002/Projeto-Jarvis.git
cd Projeto-Jarvis
```

### 2. Crie um ambiente virtual
```bash
python -m venv .venv-2
.\.venv-2\Scripts\Activate.ps1  # Windows PowerShell
# ou
.venv-2\Scripts\activate.bat    # Windows CMD
```

### 3. Instale as dependências
```bash
pip install PyQt6 sounddevice vosk pyttsx3 python-dotenv pyautogui psutil opencv-python numpy pyqtgraph openwakeword
```

### 4. Configure a chave Groq
```bash
# Crie um arquivo .env na raiz do projeto
GROQ_API_KEY=sua_chave_groq_aqui
GROQ_MODEL=llama-3.1-8b-instant
```

Obtenha uma chave gratuita em: https://console.groq.com

### 5. Baixe os modelos Vosk
```bash
# O modelo será baixado automaticamente na primeira execução
# Se precisar, baixe manualmente de: https://alphacephei.com/vosk/models
# Extraia em: ./vosk-model-small-pt-0.3/
```

---

## 🚀 Como Usar

### Executar a aplicação
```bash
python main_vosk.py
```

### Fluxo básico
1. **Aguarde a janela da UI abrir** (PyQt6)
2. **Diga "Olá"** para ativar o assistente
3. **Fale seu comando ou pergunta**
4. Jarvis responde e aguarda continuidade (14 segundos)
5. **Diga "Obrigado" ou "Valeu"** para encerrar e voltar à espera

### Exemplos de Comandos

**Ações rápidas:**
- "Abrir Chrome"
- "Pesquisar Python para iniciantes"
- "Criar uma nota"
- "Que horas são?"
- "Como está o clima?"

**Controle:**
- "Modo informal" / "Modo formal"
- "Ligar gestos" / "Desligar gestos"
- "Pare" (interrompe fala imediatamente)

**Gestos (se ativado):**
- ✊ Punho = Ativar Jarvis
- ☝ 1 dedo = "Sim chefe"
- ✌️ 2 dedos = "Volume +"
- 🤟 3 dedos = "Volume -"
- ✋ Mão aberta = "OK"

---

## ✨ Funcionalidades

### ✅ Implementadas
- ✅ Detecção de hotword com OpenWakeWord
- ✅ STT offline com Vosk (português)
- ✅ TTS neural com Piper (voz natural)
- ✅ IA conversacional via Groq
- ✅ Memória de longo prazo (JSON)
- ✅ Abertura de aplicativos
- ✅ Pesquisa web integrada
- ✅ Criação e leitura de notas
- ✅ Controle de tom (formal/informal)
- ✅ Reconhecimento de gestos de mão
- ✅ Continuidade de conversa (sem repetir hotword)
- ✅ Interrupção por comando "Pare"
- ✅ Interface visual (espectro de áudio)

### 🔮 Futuras
- 🔲 Suporte para Whisper (transcrição mais precisa)
- 🔲 Histórico de conversa persistente
- 🔲 Controle de smart home (lights, etc.)
- 🔲 Integração com calendário
- 🔲 Múltiplos idiomas
- 🔲 Modelo local de IA (LLaMA local via Ollama)

---

## ⚙️ Configuração

### Variáveis de Ambiente (.env)

```dotenv
# Groq API
GROQ_API_KEY=sua_chave_aqui
GROQ_MODEL=llama-3.1-8b-instant
GROQ_FREE_MODELS=llama-3.1-8b-instant,llama-3.3-70b-versatile

# TTS (Piper)
TTS_BACKEND=auto              # auto | piper | windows_speech | pyttsx3
PIPER_LENGTH_SCALE=1.05       # Velocidade (< 1.0 = mais rápido)
PIPER_NOISE_SCALE=0.55        # Variabilidade da voz
PIPER_NOISE_W=0.72            # Qualidade do ruído
PIPER_SPEAKER_ID=0            # ID do falante

# Hotword (OpenWakeWord)
OWW_THRESHOLD=0.52            # Sensibilidade (0.0-1.0, maior = menos falsos positivos)
OWW_VAD_THRESHOLD=0.45        # Voice Activity Detection
```

### Hotword customizado
Editar em `config.py`:
```python
HOTWORD = "olá"
HOTWORD_ALIASES = ["jarvis", "jarves", "javis", "assistente", "oi", "ei", "hey"]
```

---

## 📁 Estrutura do Projeto

```
Projeto-Jarvis/
├── main_vosk.py              # Orquestrador principal
├── wakeword_openwakeword.py  # Detector de hotword (novo)
├── stt_vosk.py               # Speech-to-Text
├── tts.py                    # Text-to-Speech (Piper + fallback)
├── brain.py                  # IA (Groq)
├── actions.py                # Comandos e automação
├── personality.py            # Persona do assistente
├── interrupt_listener.py      # Detector de "Pare"
├── gesture_control.py         # Reconhecimento de gestos
├── jarvis_ui.py              # Interface PyQt6
├── config.py                 # Configurações centralizadas
├── .env                      # Segredos (não versionado)
├── .env.example              # Template de configuração
├── .gitignore                # Arquivos ignorados
├── requirements.txt          # (Opcional) Para documentar deps
├── jarvis_memoria.json       # Memória da conversa (gerado)
├── jarvis_notas.txt          # Notas do usuário (gerado)
├── piper/                    # Modelos de TTS
│   ├── piper.exe
│   ├── models/
│   │   └── pt_BR-faber-medium.onnx
│   └── espeak-ng-data/
├── vosk-model-small-pt-0.3/  # Modelo de STT
├── assets/                   # Recursos (imagens, ícones)
└── README.md                 # Este arquivo
```

---

## 🐛 Troubleshooting

### "DLL load failed - onnxruntime"
**Solução**: Os imports estão na ordem errada. Certifique-se de que `import onnxruntime` vem **antes** de qualquer import PyQt6.

### "Modelo Vosk não encontrado"
**Solução**: Baixe em https://alphacephei.com/vosk/models e extraia `vosk-model-small-pt-0.3` na raiz do projeto.

### "OpenWakeWord não detecta hotword"
**Solução**: Ajuste `OWW_THRESHOLD` no `.env` (reduzir = mais sensível, aumentar = menos falsos positivos).

### "Microfone não funciona"
**Solução**: Verifique se o dispositivo está ativo:
```bash
python -c "import sounddevice; print(sounddevice.query_devices())"
```

---

## 📜 Licença

Este projeto é de código aberto. Modifique e distribua livremente, mantendo referência ao autor original.

---

## 🤝 Contribuições

Sugestões e melhorias são bem-vindas! Abra uma issue ou PR no GitHub.

---

```
╔════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                                                    ║
║           ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗    ███████╗███╗   ██╗ ██████╗██╗      █████╗ ██╗   ██╗███████╗  ║
║           ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝    ██╔════╝████╗  ██║██╔════╝██║     ██╔══██╗██║   ██║██╔════╝  ║
║           ██║███████║██████╔╝██║   ██║██║███████╗    █████╗  ██╔██╗ ██║██║     ██║     ███████║██║   ██║███████╗  ║
║      ██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║    ██╔══╝  ██║╚██╗██║██║     ██║     ██╔══██║██║   ██║╚════██║  ║
║      ╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║    ███████╗██║ ╚████║╚██████╗███████╗██║  ██║╚██████╔╝███████║  ║
║       ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝    ╚══════╝╚═╝  ╚═══╝ ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝   ║
║                                                                                                                    ║
╚════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
```

**Desenvolvido por**: João Vitor | **Última atualização**: Fevereiro 2026
