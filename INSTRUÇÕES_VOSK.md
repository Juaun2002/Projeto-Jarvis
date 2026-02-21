# INSTRUÇÕES - Como configurar o JARVIS com Vosk

## 📥 Baixar modelo de voz em português

1. Acesse: https://alphacephei.com/vosk/models
2. Baixe: **vosk-model-small-pt-0.3.zip** (~40MB)
3. Extraia a pasta na raiz do projeto: `J:\code\py\jarvis\vosk-model-small-pt-0.3`

## 🚀 Executar

```bash
python main_vosk.py
```

## ✅ Vantagens do Vosk

- ✅ **100% Gratuito**
- ✅ **Funciona offline** (não precisa de internet)
- ✅ **Leve e rápido** (~40MB vs 400MB do Whisper)
- ✅ **Não trava** ao carregar
- ✅ **Hotword integrada** (não precisa de API key)

## 🎤 Como usar

1. Aguarde o sistema carregar
2. Diga **"jarvis"** em voz alta
3. Quando ele perguntar "O que deseja?", fale seu comando
4. JARVIS responderá
5. Repita! Diga "jarvis" novamente sempre que quiser fazer algo

## 📝 Comandos disponíveis

- "Qual é a capital do Brasil?"
- "Me conte uma piada"
- "Abra o Chrome"
- "Abra o WhatsApp"
- "Pesquise por receitas de bolo"
- Qualquer pergunta geral!

## ⚠️ Se o modelo não for encontrado

Você verá:
```
⚠️ Modelo não encontrado em 'vosk-model-small-pt-0.3'
📥 Baixe de: https://alphacephei.com/vosk/models
```

Certifique-se de que a pasta está no lugar certo:
```
J:\code\py\jarvis\
├── main_vosk.py
├── vosk-model-small-pt-0.3\    ← AQUI!
│   ├── am\
│   ├── conf\
│   ├── graph\
│   └── ...
├── tts.py
└── ...
```
