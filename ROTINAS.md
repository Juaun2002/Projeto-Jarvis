# 🤖 JARVIS - Rotinas e Comandos Disponíveis

## 🎤 Ativação
Diga uma das seguintes palavras para ativar o assistente:
- **"Olá"** (principal)
- **"Jarvis"**
- **"Assistente"**
- **"Oi"**
- **"Ei"**
- **"Hey"**

---

## ⏰ HORÁRIO E DATA

### Que horas são?
- **Comandos:** "Que horas são?", "Que horas", "Horário"
- **Resposta:** Hora atual (formato 24h)
- **Exemplo:** "São 14:35"

### Que dia é hoje?
- **Comandos:** "Que dia é hoje?", "Que dia é", "Data de hoje"
- **Resposta:** Dia da semana, dia, mês e ano completo
- **Exemplo:** "Hoje é segunda-feira, 18 de novembro de 2025"

### Qual a data de amanhã?
- **Comandos:** "Data de amanhã", "Que dia é amanhã"
- **Resposta:** Dia da semana e data de amanhã
- **Exemplo:** "Amanhã será terça-feira, 19 de novembro"

---

## 🔔 LEMBRETES

### Criar lembrete
- **Comandos:** 
  - "Me lembre em X minutos de [mensagem]"
  - "Criar lembrete em X horas de [mensagem]"
  - **"Lembrete X minutos"** (atalho rápido sem mensagem)
- **Exemplos:**
  - "Me lembre em 10 minutos de fazer café"
  - "Criar lembrete em 2 horas de reunião"
  - **"Lembrete 5 minutos"** → Cria lembrete rápido de 5 minutos
  - **"Lembrete 30 minutos"** → Cria lembrete rápido de 30 minutos
- **Nota:** O sistema verifica lembretes a cada 30 segundos e avisa quando chega a hora

### Listar lembretes
- **Comandos:** "Listar lembretes", "Quais lembretes"
- **Resposta:** Lista todos os lembretes pendentes com horários

---

## 📝 NOTAS

### Criar nota
- **Comandos:** "Criar nota: [texto]", "Anotar [texto]", "Nota rápida [texto]", **"Criar nota"** (modo interativo)
- **Exemplos:**
  - "Criar nota: comprar leite"
  - "Anotar reunião às 15h"
  - **"Criar nota"** → JARVIS pergunta: "O que deseja anotar?" → Você responde com o conteúdo
- **Arquivo:** As notas são salvas em `jarvis_notas.txt` com timestamp
- **Modo Interativo:** Se você disser apenas "criar nota" sem especificar o conteúdo, o JARVIS vai perguntar o que você quer anotar e aguardar sua resposta

### Ler notas
- **Comandos:** "Ler notas", "Minhas notas", "Listar notas"
- **Resposta:** Exibe as últimas 5 notas salvas

---

## 💼 TRABALHO

### Hora de trabalhar
- **Comandos:** "Hora de trabalhar", "Modo trabalho", "Motor trabalho", "Abrir VS Code"
- **Ação:** Abre o Visual Studio Code
- **Locais verificados:**
  - `C:\Users\jvpes\AppData\Local\Programs\Microsoft VS Code\Code.exe`
  - `C:\Program Files\Microsoft VS Code\Code.exe`
  - `C:\Program Files (x86)\Microsoft VS Code\Code.exe`
  - Comando `code` no PATH

### Pausar trabalho
- **Comandos:** "Pausar trabalho", "Fazer pausa", "Pausa de"
- **Ação:** Cria um lembrete de 5 minutos para voltar ao trabalho
- **Resposta:** "Pausa iniciada! Te aviso às [horário] para voltar ao trabalho"

---

## 💻 CONTROLE DO SISTEMA

### Desligar computador
- **Comandos:** "Desligar computador em X minutos", "Desligar PC em X minutos"
- **Exemplos:**
  - "Desligar computador em 30 minutos"
  - "Desligar PC em 60 minutos"
- **Ação:** Agenda desligamento do Windows (comando `shutdown /s /t`)

### Status do sistema
- **Comandos:** "Status do sistema", "Status sistema", "Desempenho"
- **Resposta:** Exibe uso de CPU, RAM e Disco em porcentagem
- **Exemplo:**
  ```
  Status do Sistema:
  • CPU: 45%
  • RAM: 62%
  • Disco: 73%
  ```

---

## 🎵 MÍDIA

### Tocar música
- **Comandos:** "Tocar música", "Abrir Spotify", "Abrir Spot"
- **Ação:** Abre o Spotify (aplicativo instalado ou versão web)
- **Locais verificados:**
  - `%AppData%\Spotify\Spotify.exe`
  - `C:\Program Files\Spotify\Spotify.exe`
  - Web: `https://open.spotify.com`

---

## 🌙 ROTINAS ESPECIAIS

### Boa noite
- **Comando:** "Boa noite"
- **Ação:** Fecha todos os navegadores (Chrome, Firefox, Edge)
- **Resposta:** "Boa noite! Fechei os navegadores para você descansar."

---

## 🔍 PESQUISA WEB

### Pesquisar
- **Comandos:** "Pesquise por [termo]", "Pesquisar [termo]"
- **Exemplos:**
  - "Pesquise por Python tutorial"
  - "Pesquisar GitHub"
- **Ação:** Abre o Google Chrome com a pesquisa no Google

---

## 🛑 CONTROLE DE VOZ

### Parar execução
- **Comandos:** "Pare", "Parar", "Cale-se"
- **Ação:** Interrompe imediatamente o processamento atual e volta para aguardar hotword
- **Uso:** Para cancelar uma resposta longa ou interromper uma ação
- **Prioridade:** MÁXIMA (processado em tempo real)

### Modo Mudo
- **Comando:** "Silêncio"
- **Ação:** Ativa/desativa o modo mudo (toggle)
- **Comportamento:** 
  - Quando **ativado**: JARVIS para de falar mas continua ouvindo e processando comandos
  - Respostas aparecem apenas no texto (logs)
  - Para **desativar**: diga "Silêncio" novamente
- **Uso:** Útil quando você quer usar o assistente sem som

---

## ❓ AJUDA

### Listar comandos
- **Comandos:** "Ajuda", "O que você pode fazer?", "Quais comandos?", "Listar comandos", "Comandos disponíveis"
- **Resposta:** Lista completa de todos os comandos organizados por categoria

---

## 🤖 INTELIGÊNCIA ARTIFICIAL

### Perguntas gerais
- **Funcionalidade:** Qualquer pergunta que não seja um comando específico é enviada para o modelo de IA (Ollama Llama3)
- **Exemplos:**
  - "Qual a capital da França?"
  - "Como fazer um loop em Python?"
  - "Me conte uma piada"
- **Resposta:** O modelo de IA gera uma resposta contextual

---

## 📊 ARQUIVOS GERADOS

### jarvis_notas.txt
- **Localização:** Pasta raiz do JARVIS
- **Formato:** `[DD/MM/YYYY HH:MM] Conteúdo da nota`
- **Uso:** Todas as notas criadas são salvas neste arquivo

---

## 🔧 CONFIGURAÇÕES

### Modelo de voz (TTS)
- **Engine:** Piper TTS
- **Modelo:** `pt_BR-faber-medium.onnx`
- **Taxa de amostragem:** 22050 Hz

### Reconhecimento de voz (STT)
- **Engine:** Vosk
- **Modelo:** `vosk-model-small-pt-0.3` (40 MB, offline)
- **Idioma:** Português (Brasil)

### Hotword
- **Palavra de ativação:** "Olá"
- **Engine:** Vosk (detecção contínua)

### IA
- **Modelo:** Ollama Llama3
- **Uso:** Respostas gerais não relacionadas a comandos específicos

---

## 📝 NOTAS IMPORTANTES

1. **Reconhecimento de voz:** O modelo Vosk small pode ter imprecisões. Fale claramente e pausadamente.

2. **Variações aceitas:** O sistema aceita múltiplas variações de cada comando (ex: "motor trabalho" = "modo trabalho").

3. **Lembretes:** São verificados a cada 30 segundos. Quando acionados, são removidos automaticamente.

4. **Notas:** São anexadas ao arquivo, nunca sobrescritas. Use "Ler notas" para ver as últimas 5.

5. **Desligamento:** Uma vez agendado, use `shutdown /a` no terminal para cancelar.

---

## 🚀 DICAS DE USO

- **Seja claro:** Fale próximo ao microfone e articule bem as palavras
- **Use números:** Para lembretes e desligamento, diga números claramente ("dez minutos", "cinco minutos")
- **Comando "Pare":** Útil quando o assistente está falando muito
- **Status do sistema:** Monitore o desempenho do PC antes de tarefas pesadas
- **Notas rápidas:** Ideal para ideias e lembretes que não precisam de horário específico

---

## 📦 DEPENDÊNCIAS

```
PyQt6==6.10.0
piper-tts==1.3.0
vosk==0.3.45
sounddevice==0.5.3
ollama (servidor local)
pyautogui
psutil==6.1.1
```

---

**Versão:** 1.0  
**Última atualização:** Novembro 2025  
**Desenvolvido por:** JARVIS Project
