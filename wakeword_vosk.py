# wakeword_vosk.py - Detecção de hotword usando Vosk
import json
import os
import sys
import re
import unicodedata
import sounddevice as sd
from vosk import Model, KaldiRecognizer

class HotwordDetector:
    def __init__(self, hotword="jarvis", aliases=None):
        print(f"Inicializando detector de hotword '{hotword}'...")
        
        # Aceita hotword principal e aliases
        self.hotwords = [hotword.lower()]
        if aliases:
            self.hotwords.extend([alias.lower() for alias in aliases])

        self.hotwords = [hw for hw in self.hotwords if hw.strip()]
        self.normalized_hotwords = sorted(
            set(self._normalize_text(hw) for hw in self.hotwords if self._normalize_text(hw)),
            key=len,
            reverse=True,
        )
        self._hotword_token_map = {hw: hw.split() for hw in self.normalized_hotwords}

        grammar_candidates = set(self.hotwords)
        grammar_candidates.update(self.normalized_hotwords)
        self.grammar_terms = sorted(term for term in grammar_candidates if term)
        
        print(f"Hotwords aceitas: {', '.join(self.hotwords)}")
        
        # Caminho do modelo (funciona em dev e como executável)
        if getattr(sys, 'frozen', False):
            # Executável PyInstaller
            base_path = sys._MEIPASS
        else:
            # Desenvolvimento
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        model_path = os.path.join(base_path, "vosk-model-small-pt-0.3")
        
        try:
            self.model = Model(model_path)
            self.samplerate = 16000
            self.hotword = hotword.lower()
            print(f"Detector de hotword '{hotword}' inicializado")
        except:
            print(f"AVISO: Modelo não encontrado em '{model_path}'")
            raise Exception("Modelo Vosk não encontrado")

    @staticmethod
    def _normalize_text(text: str):
        normalized = unicodedata.normalize("NFD", (text or "").lower())
        normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
        normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def _contains_hotword(self, text: str):
        normalized_text = self._normalize_text(text)
        if not normalized_text:
            return None

        tokens = normalized_text.split()
        for hotword, hotword_tokens in self._hotword_token_map.items():
            if len(hotword_tokens) == 1:
                if hotword_tokens[0] in tokens:
                    return hotword
                continue

            window_size = len(hotword_tokens)
            for idx in range(0, max(0, len(tokens) - window_size + 1)):
                if tokens[idx:idx + window_size] == hotword_tokens:
                    return hotword

        return None

    def _build_recognizer(self):
        try:
            grammar_json = json.dumps(self.grammar_terms + ["[unk]"], ensure_ascii=False)
            return KaldiRecognizer(self.model, self.samplerate, grammar_json)
        except Exception:
            return KaldiRecognizer(self.model, self.samplerate)

    def listen(self):
        """Aguarda a hotword ser detectada"""
        print(f"\n🎧 Hotword: Ouvindo continuamente... Diga '{self.hotword}' para ativar")
        
        recognizer = self._build_recognizer()
        recognizer.SetWords(False)
        
        stream = None
        try:
            stream = sd.RawInputStream(samplerate=self.samplerate, blocksize=8000,
                                   dtype='int16', channels=1)
            stream.start()
            
            while True:
                data = stream.read(8000)[0]
                
                if recognizer.AcceptWaveform(bytes(data)):
                    result = json.loads(recognizer.Result())
                    text = result.get('text', '').lower()
                    
                    # Mostra o que foi ouvido (para debug)
                    if text:
                        print(f"   [Ouvi: '{text}']")
                    
                    detected_hotword = self._contains_hotword(text)
                    if detected_hotword:
                        print(f"\n✅ Hotword '{detected_hotword}' detectada!")
                        print("🎧 Hotword: Fechando stream...")
                        stream.stop()
                        stream.close()
                        sd.stop()
                        print("🎧 Hotword: Stream fechado, liberando microfone...")
                        import time
                        time.sleep(0.5)
                        print("🎧 Hotword: Microfone liberado!")
                        return True
                else:
                    # Resultado parcial (mostra em tempo real)
                    partial = json.loads(recognizer.PartialResult())
                    partial_text = partial.get('partial', '').lower()
                    if partial_text:
                        detected_hotword = self._contains_hotword(partial_text)
                        if detected_hotword:
                            print(f"\n✅ Hotword '{detected_hotword}' detectada!")
                            print("🎧 Hotword: Fechando stream...")
                            stream.stop()
                            stream.close()
                            sd.stop()
                            print("🎧 Hotword: Stream fechado, liberando microfone...")
                            import time
                            time.sleep(0.5)
                            print("🎧 Hotword: Microfone liberado!")
                            return True
                        print(f"\r   Ouvindo: {partial_text}...", end='', flush=True)
        except Exception as e:
            print(f"❌ Erro no hotword detector: {e}")
            if stream:
                try:
                    stream.stop()
                    stream.close()
                    sd.stop()
                except:
                    pass
            return False
