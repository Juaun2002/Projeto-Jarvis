# Graph Report - .  (2026-07-13)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 203 nodes · 336 edges · 9 communities
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 18 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a46357b6`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Actions
- Brain
- Jarvis
- JarvisUI
- JarvisPersonality
- main_vosk.py
- HotwordDetector
- InterruptListener
- TTS

## God Nodes (most connected - your core abstractions)
1. `Brain` - 31 edges
2. `Actions` - 30 edges
3. `Jarvis` - 26 edges
4. `JarvisUI` - 21 edges
5. `JarvisPersonality` - 14 edges
6. `TTS` - 14 edges
7. `GestureThread` - 12 edges
8. `InterruptListener` - 12 edges
9. `JarvisSignals` - 12 edges
10. `HotwordDetector` - 11 edges

## Surprising Connections (you probably didn't know these)
- `Jarvis` --uses--> `Actions`  [INFERRED]
  main_vosk.py → actions.py
- `JarvisSignals` --uses--> `Actions`  [INFERRED]
  main_vosk.py → actions.py
- `Jarvis` --uses--> `Brain`  [INFERRED]
  main_vosk.py → brain.py
- `JarvisSignals` --uses--> `Brain`  [INFERRED]
  main_vosk.py → brain.py
- `Jarvis` --uses--> `GestureThread`  [INFERRED]
  main_vosk.py → gesture_control.py

## Import Cycles
- None detected.

## Communities (9 total, 0 thin omitted)

### Community 0 - "Actions"
Cohesion: 0.08
Nodes (16): Actions, Mostra todos os comandos disponíveis, Inicia thread que verifica lembretes, Cria um lembrete com tempo relativo, Thread que verifica lembretes a cada minuto, Retorna a data de amanhã, Ação de energia: por padrão suspende; desliga apenas se explicitamente solicitad, Coloca o computador em suspensão. (+8 more)

### Community 1 - "Brain"
Cohesion: 0.08
Nodes (14): Brain, Extrai preferências simples e forma de tratamento a partir da fala do usuário., Captura comandos explícitos de memória do usuário., Inicializa o Brain com contexto conversacional e memória persistente., Seleciona histórico recente e relevante por palavras-chave simples., Monta prompt com perfil e contexto recente/relevante., Busca modelos acessíveis para a chave atual usando endpoint /models., Consulta Groq com fallback entre modelos permitidos. (+6 more)

### Community 2 - "Jarvis"
Cohesion: 0.13
Nodes (11): Jarvis, Detecta e troca preferência de tom por comando de voz., Comandos que exigem confirmação explícita antes de executar., Pede confirmação de voz para ações sensíveis., É chamado quando o Interrupt Listener detecta comando de parada, Loop principal - aguarda hotword e processa comandos, Ativa modo de controle por gestos, Desativa modo de controle por gestos (+3 more)

### Community 3 - "JarvisUI"
Cohesion: 0.14
Nodes (4): JarvisUI, JarvisSignals, QObject, QWidget

### Community 4 - "JarvisPersonality"
Cohesion: 0.11
Nodes (10): É chamado quando detecta 'silêncio' - muta o assistente, JarvisPersonality, Retorna resposta de interrupção, Retorna resposta ao mutar, Retorna uma despedida, Retorna mensagem de processamento, Adiciona contexto natural à resposta, Gerencia respostas naturais e personalidade do Mike (+2 more)

### Community 5 - "main_vosk.py"
Cohesion: 0.15
Nodes (3): GestureThread, Thread para detectar gestos com OpenCV, QThread

### Community 6 - "HotwordDetector"
Cohesion: 0.22
Nodes (4): Grava áudio e converte para texto com qualidade melhorada, STT, HotwordDetector, Aguarda a hotword ser detectada com openWakeWord.

### Community 7 - "InterruptListener"
Cohesion: 0.21
Nodes (4): InterruptListener, Listener que fica sempre escutando por comandos de interrupção         on_inter, Inicia thread de escuta contínua, Loop contínuo de escuta

### Community 8 - "TTS"
Cohesion: 0.26
Nodes (3): Enfileira a fala para execução serial no worker do TTS.          Por padrão ag, Para a reprodução de áudio imediatamente, TTS

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Jarvis` connect `Jarvis` to `Actions`, `Brain`, `JarvisUI`, `JarvisPersonality`, `main_vosk.py`, `HotwordDetector`, `InterruptListener`, `TTS`?**
  _High betweenness centrality (0.377) - this node is a cross-community bridge._
- **Why does `Actions` connect `Actions` to `Jarvis`, `JarvisUI`, `main_vosk.py`, `HotwordDetector`?**
  _High betweenness centrality (0.343) - this node is a cross-community bridge._
- **Why does `Brain` connect `Brain` to `Jarvis`, `JarvisUI`, `main_vosk.py`, `HotwordDetector`?**
  _High betweenness centrality (0.342) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `Brain` (e.g. with `Jarvis` and `JarvisSignals`) actually correct?**
  _`Brain` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `Actions` (e.g. with `Jarvis` and `JarvisSignals`) actually correct?**
  _`Actions` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `Jarvis` (e.g. with `Actions` and `Brain`) actually correct?**
  _`Jarvis` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `JarvisUI` (e.g. with `Jarvis` and `JarvisSignals`) actually correct?**
  _`JarvisUI` has 2 INFERRED edges - model-reasoned connections that need verification._