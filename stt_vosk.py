# stt_vosk.py - Speech-to-Text usando Vosk (gratuito e offline)
import json
import queue
import os
import sys
import sounddevice as sd
from vosk import Model, KaldiRecognizer

class STT:
    def __init__(self):
        print("Inicializando Vosk STT...")
        
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
            print("Vosk STT inicializado")
        except Exception as e:
            print(f"AVISO: Modelo não encontrado em '{model_path}'")
            print(f"Erro: {e}")
            print("Baixe de: https://alphacephei.com/vosk/models")
            print("Extraia a pasta 'vosk-model-small-pt-0.3' aqui")
            raise Exception("Modelo Vosk não encontrado")

    def listen(self, seconds=4):
        """Grava áudio e converte para texto com qualidade melhorada"""
        try:
            print(f"\n🎤 STT: Iniciando escuta por {seconds} segundos...")
            
            # Força parada de qualquer stream anterior
            try:
                sd.stop()
            except:
                pass
            
            # Pausa antes de abrir novo stream
            import time
            time.sleep(0.5)
            
            q = queue.Queue()
            audio_received = False
            
            def callback(indata, frames, time_info, status):
                nonlocal audio_received
                if status:
                    print(f"⚠️ Status callback: {status}")
                if len(indata) > 0:
                    audio_received = True
                q.put(bytes(indata))
            
            # Limpa a queue antes de começar
            while not q.empty():
                q.get()
            
            recognizer = KaldiRecognizer(self.model, self.samplerate)
            recognizer.SetWords(True)
            
            # Lista para acumular textos reconhecidos
            recognized_texts = []
            
            print("🎤 STT: Abrindo stream de áudio...")
            # Aumenta sensibilidade e qualidade do reconhecimento
            with sd.RawInputStream(samplerate=self.samplerate, blocksize=4000, 
                                   dtype='int16', channels=1, callback=callback):
                
                print("🎤 STT: Stream aberto! Fale agora...")
                start_time = time.time()
                
                # Escuta com feedback em tempo real
                while (time.time() - start_time) < seconds:
                    sd.sleep(100)
                    
                    # Processa áudio em tempo real
                    while not q.empty():
                        data = q.get()
                        if recognizer.AcceptWaveform(data):
                            result = json.loads(recognizer.Result())
                            if 'text' in result and result['text']:
                                text_chunk = result['text']
                                recognized_texts.append(text_chunk)
                                print(f"\r   Captando: '{text_chunk}'", end='', flush=True)
                        else:
                            # Mostra reconhecimento parcial
                            partial = json.loads(recognizer.PartialResult())
                            if 'partial' in partial and partial['partial']:
                                print(f"\r   Ouvindo: {partial['partial']}...", end='', flush=True)
                
                print()  # Nova linha
                
                if not audio_received:
                    print("⚠️ STT: NENHUM ÁUDIO FOI RECEBIDO!")
                else:
                    print(f"✅ STT: Áudio recebido, processando...")
                
                # Processa áudio final restante
                while not q.empty():
                    data = q.get()
                    if recognizer.AcceptWaveform(data):
                        result = json.loads(recognizer.Result())
                        if 'text' in result and result['text']:
                            recognized_texts.append(result['text'])
                
                # Resultado final
                final_result = json.loads(recognizer.FinalResult())
                if 'text' in final_result and final_result['text']:
                    recognized_texts.append(final_result['text'])
                
                # Junta todos os textos reconhecidos
                full_text = ' '.join(recognized_texts).strip()
                
                print(f"🎤 STT: Texto reconhecido: '{full_text}' ({len(recognized_texts)} chunks)")
                
            # Pequena pausa para garantir que o stream foi fechado completamente
            time.sleep(0.2)
            
            return full_text
            
        except Exception as e:
            print(f"Erro no STT: {e}")
            return ""
