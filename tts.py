# tts.py
import pyttsx3
import threading
import queue
import subprocess
import platform
import os
import tempfile
import uuid

from config import (
    PIPER_EXE_PATH,
    PIPER_MODEL_PATH,
    TTS_BACKEND,
    PIPER_SPEAKER_ID,
    PIPER_LENGTH_SCALE,
    PIPER_NOISE_SCALE,
    PIPER_NOISE_W,
)

if platform.system().lower().startswith("win"):
    import winsound

class TTS:
    def __init__(self, ui=None):
        print("Inicializando TTS...")
        self.is_speaking = False
        self.ui = ui  # Referência para controlar UI
        self._lock = threading.Lock()
        self._queue = queue.Queue()
        self._shutdown = threading.Event()
        self.engine = None
        self._current_process = None
        self._current_audio_file = None
        self.piper_exe_path = PIPER_EXE_PATH
        self.piper_model_path = PIPER_MODEL_PATH
        self.piper_speaker_id = PIPER_SPEAKER_ID
        self.piper_length_scale = PIPER_LENGTH_SCALE
        self.piper_noise_scale = PIPER_NOISE_SCALE
        self.piper_noise_w = PIPER_NOISE_W
        self.backend = self._select_backend()
        self._worker = threading.Thread(target=self._speak_worker, daemon=True)
        self._worker.start()
        print(f"TTS inicializado com sucesso! Backend: {self.backend}")

    def _piper_available(self):
        return bool(self.piper_exe_path and self.piper_model_path and os.path.exists(self.piper_exe_path) and os.path.exists(self.piper_model_path))

    def _select_backend(self):
        system_name = platform.system().lower()
        requested = (TTS_BACKEND or "auto").lower()

        if requested == "piper":
            if self._piper_available():
                return "piper"
            print("⚠️ TTS: TTS_BACKEND='piper', mas piper/modelo não encontrados. Usando fallback automático.")

        if requested == "windows_speech" and system_name.startswith("win"):
            return "windows_speech"

        if requested == "pyttsx3":
            return "pyttsx3"

        if system_name.startswith("win") and self._piper_available():
            return "piper"
        if system_name.startswith("win"):
            return "windows_speech"
        return "pyttsx3"

    def _build_engine(self):
        engine = pyttsx3.init()
        
        # Configurar voz em português se disponível
        voices = engine.getProperty('voices')
        for voice in voices:
            if 'portuguese' in voice.name.lower() or 'brazil' in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break
        
        # Ajustar velocidade e volume
        engine.setProperty('rate', 150)  # Velocidade da fala
        engine.setProperty('volume', 0.9)  # Volume
        return engine

    def _speak_with_windows_speech(self, text: str):
        escaped_text = (text or "").replace("'", "''")
        cmd = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$s.Rate = 0; $s.Volume = 100; "
            f"$s.Speak('{escaped_text}')"
        )
        self._current_process = subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._current_process.wait()
        self._current_process = None

    def _speak_with_piper(self, text: str):
        wav_path = os.path.join(tempfile.gettempdir(), f"jarvis_tts_{uuid.uuid4().hex}.wav")
        args = [
            self.piper_exe_path,
            "--model",
            self.piper_model_path,
            "--output_file",
            wav_path,
            "--length_scale",
            str(self.piper_length_scale),
            "--noise_scale",
            str(self.piper_noise_scale),
            "--noise_w",
            str(self.piper_noise_w),
        ]

        if self.piper_speaker_id is not None:
            args.extend(["--speaker", str(self.piper_speaker_id)])

        process = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        self._current_process = process
        _, stderr_output = process.communicate((text or "") + "\n")
        self._current_process = None

        if process.returncode != 0:
            raise RuntimeError((stderr_output or "Erro desconhecido no Piper").strip())

        self._current_audio_file = wav_path
        if platform.system().lower().startswith("win"):
            winsound.PlaySound(wav_path, winsound.SND_FILENAME)

        self._current_audio_file = None
        if os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except OSError:
                pass

    def _speak_worker(self):
        if self.backend == "pyttsx3":
            self.engine = self._build_engine()

        while not self._shutdown.is_set():
            item = self._queue.get()
            if item is None:
                self._queue.task_done()
                break

            text, done_event = item

            try:
                self.is_speaking = True
                if self.ui:
                    self.ui.start_speaking()

                print(f"🔊 TTS: Falando: {text}")
                with self._lock:
                    if self.backend == "piper":
                        try:
                            self._speak_with_piper(text)
                        except Exception as piper_error:
                            print(f"⚠️ TTS: Piper falhou ({piper_error}). Usando Windows Speech para esta fala.")
                            self._speak_with_windows_speech(text)
                    elif self.backend == "windows_speech":
                        self._speak_with_windows_speech(text)
                    else:
                        self.engine.say(text)
                        self.engine.runAndWait()

            except Exception as e:
                print(f"⚠️ TTS: Erro no engine: {e}")
                if self.backend == "pyttsx3" and "run loop already started" in str(e).lower():
                    try:
                        with self._lock:
                            self.engine.stop()
                            self.engine = self._build_engine()
                    except Exception:
                        pass
            finally:
                self.is_speaking = False
                if self.ui:
                    self.ui.stop_speaking()
                if done_event:
                    done_event.set()
                print("🔊 TTS: Fala concluída")
                self._queue.task_done()


    def speak(self, text: str, wait: bool = True, timeout: float = 10.0):
        """Enfileira a fala para execução serial no worker do TTS.

        Por padrão aguarda a conclusão para evitar sobreposição com STT.
        """
        if not text:
            return

        print(f"🔊 TTS: Iniciando fala: '{text}'")
        done_event = threading.Event()
        self._queue.put((text, done_event))

        if wait:
            completed = done_event.wait(timeout=timeout)
            if not completed:
                print("⚠️ TTS: Tempo de espera excedido; fala seguirá em background.")
    
    def stop(self):
        """Para a reprodução de áudio imediatamente"""
        print("🛑 TTS: Stop chamado")
        self.is_speaking = False
        if self.ui:
            self.ui.stop_speaking()

        # Limpa falas pendentes
        while True:
            try:
                item = self._queue.get_nowait()
                if item and isinstance(item, tuple) and len(item) == 2:
                    _, done_event = item
                    if done_event:
                        done_event.set()
                self._queue.task_done()
            except queue.Empty:
                break

        try:
            if self.backend == "piper":
                process = self._current_process
                if process and process.poll() is None:
                    process.terminate()
                if platform.system().lower().startswith("win"):
                    winsound.PlaySound(None, winsound.SND_PURGE)
            elif self.backend == "windows_speech":
                process = self._current_process
                if process and process.poll() is None:
                    process.terminate()
            elif self.engine:
                self.engine.stop()
        except:
            pass
        print("🛑 TTS: Reprodução interrompida")


