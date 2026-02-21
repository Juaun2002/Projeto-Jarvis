# interrupt_listener.py - Escuta contínua para comandos de interrupção
import threading
import json
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import os
import sys
import time

class InterruptListener:
    def __init__(self, on_interrupt_callback, on_mute_callback, can_trigger_callback=None):
        """
        Listener que fica sempre escutando por comandos de interrupção
        on_interrupt_callback: função chamada quando detecta interrupção (pare/parar)
        on_mute_callback: função chamada quando detecta comando de mute (silêncio)
        """
        self.interrupt_keywords = ["pare", "parar", "cale-se", "cale", "stop"]
        self.mute_keywords = ["silêncio", "silencio", "mudo", "quieto"]
        self.on_interrupt_callback = on_interrupt_callback
        self.on_mute_callback = on_mute_callback
        self.can_trigger_callback = can_trigger_callback
        self.listening = False
        self.thread = None
        self._last_trigger_at = 0.0
        self._trigger_cooldown_seconds = 1.2
        
        # Caminho do modelo
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        model_path = os.path.join(base_path, "vosk-model-small-pt-0.3")
        
        try:
            self.model = Model(model_path)
            self.samplerate = 16000
            print("✓ Interrupt Listener inicializado")
        except Exception as e:
            print(f"AVISO: Erro ao inicializar Interrupt Listener: {e}")
            self.model = None

    def _can_trigger(self):
        if self.can_trigger_callback is None:
            return True
        try:
            return bool(self.can_trigger_callback())
        except Exception:
            return False

    def _on_cooldown(self):
        now = time.time()
        if now - self._last_trigger_at < self._trigger_cooldown_seconds:
            return True
        self._last_trigger_at = now
        return False

    def _contains_keyword(self, text: str, keyword: str):
        normalized = f" {(text or '').lower().strip()} "
        if not keyword:
            return False
        return f" {keyword.lower()} " in normalized
    
    def start(self):
        """Inicia thread de escuta contínua"""
        if self.model is None:
            return
        
        if self.listening:
            return
        
        self.listening = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        print("🎧 Interrupt Listener ativo (sempre escutando)")
    
    def stop(self):
        """Para a escuta"""
        self.listening = False
    
    def _listen_loop(self):
        """Loop contínuo de escuta"""
        try:
            recognizer = KaldiRecognizer(self.model, self.samplerate)
            
            with sd.RawInputStream(samplerate=self.samplerate, blocksize=4000,
                                   dtype='int16', channels=1) as stream:
                
                while self.listening:
                    data = stream.read(4000)[0]
                    
                    if recognizer.AcceptWaveform(bytes(data)):
                        result = json.loads(recognizer.Result())
                        if 'text' in result and result['text']:
                            text = result['text'].lower()

                            if not self._can_trigger() or self._on_cooldown():
                                continue
                            
                            # Verifica se é comando de mute
                            for keyword in self.mute_keywords:
                                if self._contains_keyword(text, keyword):
                                    print(f"MUTE DETECTADO: '{text}'")
                                    self.on_mute_callback()
                                    break
                            
                            # Verifica se é comando de interrupção
                            for keyword in self.interrupt_keywords:
                                if self._contains_keyword(text, keyword):
                                    print(f"🛑 INTERRUPÇÃO DETECTADA: '{text}'")
                                    self.on_interrupt_callback()
                                    break
        
        except Exception as e:
            print(f"Erro no Interrupt Listener: {e}")
