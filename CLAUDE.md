# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in this repository.

## What this is

Mike is a Portuguese-language voice assistant for Windows. The repo is a single PyQt6 app: `main_vosk.py` orchestrates a hotword listener, offline Vosk STT, a deterministic command router, a Brain (Ollama with optional Groq fallback), and Piper/Win-Speech TTS — with an optional webcam gesture controller. UI/log text is Brazilian Portuguese; no emojis in user-facing strings (Brain's `_clean_response` strips them anyway).

## Running

```bash
.venv\Scripts\activate
python main_vosk.py
```

There is no `requirements.txt` or test suite. The pip line in this file's history is the source of truth (`vosk sounddevice openwakeword pyttsx3 PyQt6 psutil pyautogui opencv-python onnxruntime python-dotenv requests`).

## Architecture (3 lines)

`main_vosk.py` wires every component and runs the main loop in a background thread; the UI runs on the main thread. `init_components()` initializes TTS → STT → Brain → Actions → Hotword → InterruptListener — each step is wrapped in try/except, so a single failure leaves that attribute `None` and the loop skips it. The component map, control flow, and env-var list all reconstruct from reading the 7 source files (`main_vosk.py`, `brain.py`, `actions.py`, `tts.py`, `stt_vosk.py`, `wakeword_openwakeword.py`, `interrupt_listener.py`) plus `config.py`.

## Non-derivable gotchas (this is the part you can't recover from a quick read)

- **DLL ordering**: `onnxruntime` is imported at the very top of `main_vosk.py` so its DLL loads before Qt. Keep that order — the reverse triggers a Windows DLL conflict.
- **Base-path detection** (`sys._MEIPASS` for PyInstaller vs `os.path.dirname(__file__)` for dev) is duplicated in `config.py`, `stt_vosk.py`, `interrupt_listener.py`, `wakeword_openwakeword.py`. New files that load bundled assets must follow the same pattern.
- **TTS serialization**: all utterances go through a single worker queue. `tts.speak()` blocks on a `threading.Event` by default so the orchestrator waits for speech to finish before re-opening the mic. `tts.stop()` flushes the queue, terminates the active subprocess, and calls `winsound.PlaySound(None, SND_PURGE)` to cut Piper audio.
- **Hotword model resolution**: `openWakeWord` auto-downloads its models on first init. If no model label matches any normalized hotword token (`mike`, `maique`, `miky`, `mik`, `assistente`, …), the constructor raises and the class transparently falls back to a local Vosk recognizer against the same tokens. `OWW_THRESHOLD=0.52` (configurable).
- **Brain memory**: `Brain.ask()` persists history + session/long-term memories + a tiny user profile to `jarvis_memoria.json` after every exchange. On Ollama empty/error responses it retries with a stripped-down prompt; if `ALLOW_GROQ_FALLBACK=true` and `GROQ_API_KEY` is set, it round-robins through `GROQ_FALLBACK_MODELS`. Explicit memory commands (`lembre que…`, `guarde que…`, `anota que…`) get `importance=3` and bypass the LLM.
- **Gesture activation is opt-in**: the user says "ativar gestos" / "ligar gestos" to spawn `GestureThread`, "desativar gestos" / "desligar gestos" to stop it. Mapping: `FIST`→simulate hotword, `ONE`→"Sim chefe", `TWO`→"Volume mais", `THREE`→"Volume menos", `OPEN`→"OK".
- **System commands require explicit confirmation**: shutdown/suspend/`dormir`/`fechar mike` triggers `_confirm_sensitive_action` which does a second STT round and requires an explicit `sim`. **"desligar computador" without "totalmente / de verdade / agora / completamente" routes to `suspend_pc`** (`rundll32.exe powrprof.dll,SetSuspendState 0,1,0`), not shutdown. With the explicit phrase it parses the minutes and runs `shutdown /s /t N`.
- **App launching paths live in `config.PROGRAMS`** — add new fixed shortcuts there, not inline.
- **Required bundled assets**: `vosk-model-small-pt-0.3/` and `piper/models/pt_BR-faber-medium.onnx`. Missing files produce recoverable init errors that leave the corresponding component as `None` — the app still starts.
- **Dead env var**: `WHISPER_MODEL` is declared in `config.py` but unused (STT uses Vosk).
- **Follow-up timing**: `FOLLOW_UP_WINDOW_SECONDS=14` and `FOLLOW_UP_LISTEN_SECONDS=4` are hard-coded in `config.py` — they govern the "no need to repeat the hotword" window.

## Code map (graphify)

`graphify-out/` holds a static call graph (203 nodes, 336 edges, 9 communities). Useful as a second opinion on architecture, but it reflects the last indexed commit (`a46357b6`) and goes stale as soon as the working tree changes. Entry points: `graphify-out/graph.html` (interactive), `graph.json` (raw), `GRAPH_REPORT.md` (summary). Refresh with `graphify update .` (no API cost per the report).
