# wakeword_openwakeword.py - Detecção de hotword com openWakeWord com fallback local em Vosk
# wakeword_openwakeword.py - Detecção de hotword com openWakeWord com fallback local em Vosk
import json
import os
import re
import sys
import time
import queue
import unicodedata

import numpy as np
import sounddevice as sd

from config import OWW_THRESHOLD, OWW_VAD_THRESHOLD


class HotwordDetector:
    def __init__(self, hotword="mike", aliases=None):
        print(f"Inicializando detector de hotword (openWakeWord) para '{hotword}'...")

        self.mode = "openwakeword"
        self.detected = False

        try:
            import openwakeword
            from openwakeword.model import Model

            self.samplerate = 16000
            self.threshold = float(OWW_THRESHOLD)
            self.vad_threshold = float(OWW_VAD_THRESHOLD)

            configured = [hotword.lower().strip()]
            if aliases:
                configured.extend([alias.lower().strip() for alias in aliases if alias and alias.strip()])

            self.configured_hotwords = [item for item in configured if item]
            self.normalized_hotwords = [self._normalize_text(item) for item in self.configured_hotwords]
            self.normalized_hotwords = [item for item in self.normalized_hotwords if item]

            token_candidates = []
            for expression in self.normalized_hotwords:
                token_candidates.extend(expression.split())

            self.target_tokens = sorted(
                set(token for token in token_candidates if len(token) >= 4),
                key=len,
                reverse=True,
            )
            if not self.target_tokens:
                self.target_tokens = ["mike"]

            print(f"Hotwords configuradas: {', '.join(self.configured_hotwords)}")
            print(f"Tokens-alvo para detecção: {', '.join(self.target_tokens)}")

            try:
                openwakeword.utils.download_models()
            except Exception as exc:
                raise RuntimeError(f"Falha ao preparar modelos openWakeWord: {exc}") from exc

            self.model = Model(vad_threshold=self.vad_threshold)

            model_names = sorted(getattr(self.model, "models", {}).keys())
            print(f"Modelos openWakeWord carregados: {', '.join(model_names)}")
            if model_names and not any(token in " ".join(model_names).lower() for token in self.target_tokens):
                raise RuntimeError("Nenhum modelo openWakeWord compatível com a hotword foi encontrado")

            print("Detector openWakeWord inicializado")

        except Exception as exc:
            print(f"⚠️ openWakeWord falhou na inicialização ({exc}). Usando fallback Vosk local.")
            self._init_vosk_fallback(hotword, aliases)

    def _init_vosk_fallback(self, hotword, aliases=None):
        try:
            from vosk import Model, KaldiRecognizer
        except Exception as exc:
            raise RuntimeError(f"Falha ao importar Vosk para fallback da hotword: {exc}") from exc

        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        model_path = os.path.join(base_path, "vosk-model-small-pt-0.3")
        self.mode = "vosk"
        self.samplerate = 16000
        self.vosk_model = Model(model_path)
        self.vosk_recognizer = KaldiRecognizer(self.vosk_model, self.samplerate)
        self.vosk_recognizer.SetWords(True)

        configured = [hotword.lower().strip()]
        if aliases:
            configured.extend([alias.lower().strip() for alias in aliases if alias and alias.strip()])
        self.vosk_hotword_tokens = [self._normalize_text(item) for item in configured if item]
        self.vosk_hotword_tokens = [item for item in self.vosk_hotword_tokens if item]

        print(f"Detector Vosk local inicializado para hotwords: {', '.join(self.vosk_hotword_tokens)}")

    @staticmethod
    def _normalize_text(text: str):
        normalized = unicodedata.normalize("NFD", (text or "").lower())
        normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
        normalized = re.sub(r"[^a-z0-9\s_-]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def _matching_score(self, predictions: dict):
        best_label = None
        best_score = 0.0

        for label, score in (predictions or {}).items():
            normalized_label = self._normalize_text(str(label).replace("_", " ").replace("-", " "))
            if not normalized_label:
                continue

            if any(token in normalized_label for token in self.target_tokens):
                numeric_score = float(score)
                if numeric_score > best_score:
                    best_label = str(label)
                    best_score = numeric_score

        return best_label, best_score

    def listen(self):
        """Aguarda a hotword ser detectada com openWakeWord."""
        if self.mode == "vosk":
            return self._listen_vosk()

        print("\n🎧 Hotword: Ouvindo continuamente com openWakeWord...")

        stream = None
        last_debug_at = 0.0
        try:
            stream = sd.InputStream(
                samplerate=self.samplerate,
                blocksize=1280,
                channels=1,
                dtype="int16",
            )
            stream.start()

            while True:
                frame, _ = stream.read(1280)
                frame_int16 = np.squeeze(frame).astype(np.int16)

                predictions = self.model.predict(frame_int16)
                label, score = self._matching_score(predictions)

                now = time.time()
                if label and (now - last_debug_at) >= 0.8:
                    print(f"\r   Ouvindo: {label} ({score:.2f})...", end="", flush=True)
                    last_debug_at = now

                if label and score >= self.threshold:
                    print(f"\n✅ Hotword detectada via openWakeWord: {label} ({score:.2f})")
                    print("🎧 Hotword: Fechando stream...")
                    stream.stop()
                    stream.close()
                    sd.stop()
                    time.sleep(0.3)
                    print("🎧 Hotword: Microfone liberado!")
                    return True

        except Exception as e:
            print(f"❌ Erro no hotword detector (openWakeWord): {e}")
            if stream:
                try:
                    stream.stop()
                    stream.close()
                    sd.stop()
                except Exception:
                    pass
            return False

    def _listen_vosk(self):
        print("\n🎧 Hotword: Ouvindo continuamente com Vosk local...")

        stream = None
        q = queue.Queue()
        try:
            def callback(indata, frames, time_info, status):
                if status:
                    print(f"⚠️ Hotword Vosk status: {status}")
                q.put(bytes(indata))

            stream = sd.RawInputStream(
                samplerate=self.samplerate,
                blocksize=4000,
                dtype="int16",
                channels=1,
                callback=callback,
            )
            stream.start()

            last_debug_at = 0.0
            while True:
                data = q.get()
                if self.vosk_recognizer.AcceptWaveform(data):
                    result = json.loads(self.vosk_recognizer.Result())
                    text = self._normalize_text(result.get("text", ""))
                    if text:
                        now = time.time()
                        if (now - last_debug_at) >= 0.8:
                            print(f"\r   Ouvindo: {text}", end="", flush=True)
                            last_debug_at = now

                        if any(token in text for token in self.vosk_hotword_tokens):
                            print(f"\n✅ Hotword detectada via Vosk local: {text}")
                            print("🎧 Hotword: Fechando stream...")
                            stream.stop()
                            stream.close()
                            sd.stop()
                            time.sleep(0.3)
                            print("🎧 Hotword: Microfone liberado!")
                            self.detected = True
                            return True

        except Exception as e:
            print(f"❌ Erro no hotword detector (Vosk local): {e}")
            if stream:
                try:
                    stream.stop()
                    stream.close()
                    sd.stop()
                except Exception:
                    pass
            return False