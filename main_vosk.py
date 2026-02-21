# main_vosk.py - JARVIS com Vosk (gratuito) e hotword
import sys
import threading
import time
import re
import unicodedata
import onnxruntime  # Pré-carrega runtime ONNX antes do Qt para evitar conflito de DLL no Windows
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import pyqtSignal, QObject
from stt_vosk import STT
from wakeword_openwakeword import HotwordDetector
from interrupt_listener import InterruptListener
from gesture_control import GestureThread
from tts import TTS
from brain import Brain
from actions import Actions
from jarvis_ui import JarvisUI
from personality import JarvisPersonality
from config import FOLLOW_UP_WINDOW_SECONDS, FOLLOW_UP_LISTEN_SECONDS

class JarvisSignals(QObject):
    update_status = pyqtSignal(str)
    add_log = pyqtSignal(str)

class Jarvis:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.ui = JarvisUI()
        self.signals = JarvisSignals()
        
        self.signals.update_status.connect(self.ui.show_status)
        self.signals.add_log.connect(self.ui.add_log)
        
        self.tts = None
        self.stt = None
        self.brain = None
        self.actions = None
        self.hotword = None
        self.interrupt_listener = None
        self.interrupted = False
        self.muted = False
        self.running = True
        self.gesture_thread = None
        self.gesture_mode = False  # Modo gestos desativado por padrão
        self.follow_up_until = 0
        self.follow_up_window_seconds = FOLLOW_UP_WINDOW_SECONDS
        self.follow_up_listen_seconds = FOLLOW_UP_LISTEN_SECONDS
        self.tone_mode = "formal"  # formal | informal

    def _conversation_active(self):
        return time.time() < self.follow_up_until

    def _normalize_text(self, text: str):
        normalized = unicodedata.normalize("NFD", (text or "").lower())
        normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
        normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def _is_end_phrase(self, text: str):
        normalized = self._normalize_text(text)
        if not normalized:
            return False

        tokens = normalized.split()
        end_markers = [
            "obrigado",
            "obrigada",
            "brigado",
            "brigada",
            "obg",
            "valeu",
            "é só",
            "e so",
            "pode encerrar",
            "até mais",
            "ate mais",
            "ate logo",
            "tchau",
            "falou",
            "encerrar",
            "finalizar",
        ]

        if any(marker in normalized for marker in end_markers):
            return True

        return any(token.startswith("obrigad") or token.startswith("brigad") for token in tokens)

    def _apply_tone(self, text: str):
        """Aplica tom formal/informal na resposta final."""
        if not text:
            return text

        if self.tone_mode == "informal":
            toned = re.sub(r"\bsenhor\b", "você", text, flags=re.IGNORECASE)
            toned = re.sub(r"\bchefe\b", "você", toned, flags=re.IGNORECASE)
            toned = re.sub(r"\bàs suas ordens\b", "beleza", toned, flags=re.IGNORECASE)
            return toned
        return text

    def _maybe_switch_tone(self, text: str):
        """Detecta e troca preferência de tom por comando de voz."""
        normalized = (text or "").lower().strip()

        informal_markers = [
            "modo informal",
            "fale informal",
            "mais informal",
            "sem formalidade",
            "me chama de você",
        ]
        formal_markers = [
            "modo formal",
            "fale formal",
            "mais formal",
            "me chama de senhor",
            "me chama de chefe",
        ]

        if any(marker in normalized for marker in informal_markers):
            self.tone_mode = "informal"
            return "Perfeito. Vou falar de forma mais natural e informal."

        if any(marker in normalized for marker in formal_markers):
            self.tone_mode = "formal"
            return "Perfeito. Vou manter um tom formal."

        return None

    def _is_sensitive_command(self, text: str):
        """Comandos que exigem confirmação explícita antes de executar."""
        normalized = (text or "").lower()
        sensitive_markers = [
            "desligar computador",
            "desligar pc",
            "suspender computador",
            "suspender pc",
            "colocar em suspensão",
            "colocar em suspensao",
            "fechar jarvis",
            "desligar jarvis",
            "durma",
            "dormir",
            "boa noite",
        ]
        return any(marker in normalized for marker in sensitive_markers)

    def _confirm_sensitive_action(self, text: str):
        """Pede confirmação de voz para ações sensíveis."""
        if not self.stt:
            return False

        prompt = self._apply_tone("Essa ação é sensível. Confirma executar? Diga sim ou não.")
        self.signals.update_status.emit("Confirmação necessária")
        self.signals.add_log.emit(f"Jarvis: {prompt}")
        print(f">>> Jarvis: {prompt}")
        if self.tts and not self.muted:
            self.tts.speak(prompt)

        confirmation = self.stt.listen(seconds=3)
        self.signals.add_log.emit(f"Você (confirmação): {confirmation}")
        print(f">>> Você (confirmação): {confirmation}")

        normalized = (confirmation or "").lower().strip()
        shutdown_intent = any(marker in (text or "").lower() for marker in ["desligar computador", "desligar pc", "desligar totalmente"])

        if shutdown_intent:
            if "sim" in normalized and ("deslig" in normalized or "total" in normalized):
                return True
        else:
            if any(word in normalized for word in ["sim", "confirmo", "pode", "ok", "pode executar"]):
                return True

        cancel_msg = self._apply_tone("Certo, ação cancelada.")
        self.signals.add_log.emit(f"Jarvis: {cancel_msg}")
        if self.tts and not self.muted:
            self.tts.speak(cancel_msg)
        return False

    def init_components(self):
        print("\n" + "="*60)
        print("INICIALIZANDO JARVIS COM VOSK")
        print("="*60)
        
        self.signals.add_log.emit("=== INICIALIZAÇÃO ===")
        
        # TTS
        try:
            print("[1/5] TTS...")
            self.signals.add_log.emit("[1/5] Carregando TTS...")
            self.tts = TTS(ui=self.ui)  # Passa UI para controlar espectro
            print("      OK")
            self.signals.add_log.emit("      TTS OK")
        except Exception as e:
            print(f"      ERRO: {e}")
            self.signals.add_log.emit("      TTS falhou")
        
        # STT (Vosk)
        try:
            print("[2/5] STT (Vosk)...")
            self.signals.add_log.emit("[2/5] Carregando STT (Vosk)...")
            self.stt = STT()
            print("      OK")
            self.signals.add_log.emit("      STT OK")
        except Exception as e:
            print(f"      ERRO: {e}")
            self.signals.add_log.emit(f"      STT falhou: {e}")
            import traceback
            traceback.print_exc()
        
        # Brain
        try:
            print("[3/5] Brain...")
            self.signals.add_log.emit("[3/5] Carregando Brain...")
            self.brain = Brain()
            print("      OK")
            self.signals.add_log.emit("      Brain OK")
        except Exception as e:
            print(f"      ERRO: {e}")
            self.signals.add_log.emit("      Brain falhou")
        
        # Actions
        try:
            print("[4/5] Actions...")
            self.signals.add_log.emit("[4/5] Carregando Actions...")
            self.actions = Actions()
            print("      OK")
            self.signals.add_log.emit("      Actions OK")
        except Exception as e:
            print(f"      ERRO: {e}")
            self.signals.add_log.emit("      Actions falhou")
        
        # Hotword
        try:
            print("[5/5] Hotword (Vosk)...")
            self.signals.add_log.emit("[5/5] Carregando Hotword...")
            from config import HOTWORD, HOTWORD_ALIASES
            self.hotword = HotwordDetector(hotword=HOTWORD, aliases=HOTWORD_ALIASES)
            print("      OK")
            self.signals.add_log.emit("      Hotword OK")
        except Exception as e:
            print(f"      ERRO: {e}")
            self.signals.add_log.emit(f"      Hotword falhou: {e}")
        
        # Interrupt Listener (sempre ativo)
        try:
            print("[EXTRA] Interrupt Listener...")
            self.interrupt_listener = InterruptListener(
                self.on_interrupt,
                self.on_mute,
                can_trigger_callback=lambda: bool(self.tts and self.tts.is_speaking),
            )
            self.interrupt_listener.start()
            print("      OK")
        except Exception as e:
            print(f"      X {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "="*60)
        print("RESUMO")
        print("="*60)
        print(f"TTS:     {'OK' if self.tts else 'FALHOU'}")
        print(f"STT:     {'OK' if self.stt else 'FALHOU'}")
        print(f"Brain:   {'OK' if self.brain else 'FALHOU'}")
        print(f"Actions: {'OK' if self.actions else 'FALHOU'}")
        print(f"Hotword: {'OK' if self.hotword else 'FALHOU'}")
        print("="*60 + "\n")
        
        self.signals.add_log.emit("\n=== SISTEMA PRONTO ===")
        
        if not self.hotword:
            self.signals.add_log.emit("AVISO: Hotword não disponível!")
            print("\nAVISO: HOTWORD NÃO DISPONÍVEL")
            print("📥 Baixe o modelo de: https://alphacephei.com/vosk/models")
            print("📁 Extraia 'vosk-model-small-pt-0.3' na pasta do projeto\n")
        else:
            print(f"✅ Diga 'olá' para ativar!")
            self.signals.add_log.emit("Diga 'olá' para ativar")
        
        self.signals.update_status.emit("Pronto - Aguardando hotword")
    
    def on_interrupt(self):
        """É chamado quando o Interrupt Listener detecta comando de parada"""
        print("\n🛑 INTERRUPÇÃO! Parando tudo...")
        self.interrupted = True
        
        # Para TTS imediatamente
        if self.tts:
            self.tts.stop()
        
        # Responde com personalidade
        interrupted_msg = JarvisPersonality.get_interrupted()
        interrupted_msg = self._apply_tone(interrupted_msg)
        self.signals.update_status.emit("Interrompido")
        self.signals.add_log.emit(f"🛑 {interrupted_msg}")
        
        # Após 4 segundos, volta ao normal (reset da flag)
        def reset_interrupt():
            import time
            time.sleep(4)
            self.interrupted = False
            print("✅ Sistema pronto novamente")
            self.signals.update_status.emit("Aguardando comando")
        
        threading.Thread(target=reset_interrupt, daemon=True).start()
    
    def on_mute(self):
        """É chamado quando detecta 'silêncio' - muta o assistente"""
        print("\nMODO MUDO ativado")
        self.muted = not self.muted  # Toggle mute
        
        if self.muted:
            # Para o que estiver falando
            if self.tts:
                self.tts.stop()
            muted_msg = JarvisPersonality.get_muted()
            muted_msg = self._apply_tone(muted_msg)
            self.signals.update_status.emit("Modo Mudo")
            self.signals.add_log.emit(f"MUDO: {muted_msg}")
            print(f"MUDO: {muted_msg}")
        else:
            unmuted_msg = JarvisPersonality.get_unmuted()
            unmuted_msg = self._apply_tone(unmuted_msg)
            self.signals.update_status.emit("Modo Normal")
            self.signals.add_log.emit(f"SOM: {unmuted_msg}")
            print(f"SOM: {unmuted_msg}")
            if self.tts:
                self.tts.speak(unmuted_msg)

    def jarvis_loop(self):
        """Loop principal - aguarda hotword e processa comandos"""
        
        if not self.hotword:
            print("ERRO: Não é possível iniciar sem hotword detector")
            self.signals.add_log.emit("Sistema não pode iniciar sem hotword")
            return
        
        while self.running:
            try:
                # Reset da flag de interrupção
                self.interrupted = False

                # Aguarda hotword apenas fora da janela de continuidade
                if not self._conversation_active():
                    self.signals.update_status.emit("Aguardando 'olá'...")
                    self.hotword.listen()
                    # Pausa para liberar o microfone completamente
                    print("⏳ Main: Aguardando liberação do microfone...")
                    time.sleep(0.5)
                    print("✅ Main: Microfone deve estar liberado agora")
                else:
                    self.signals.update_status.emit("Continuidade ativa...")
                
                # Verifica se foi interrompido
                if self.interrupted:
                    continue

                # Saudação apenas quando entrou por hotword
                if not self._conversation_active():
                    self.signals.update_status.emit("Ativo!")
                    self.signals.add_log.emit("JARVIS ATIVADO!")
                    print("\n" + "="*60)
                    print("JARVIS ATIVADO!")
                    print("="*60)

                    greeting = JarvisPersonality.get_greeting()
                    greeting = self._apply_tone(greeting)
                    print(f"💬 Main: Falando saudação: '{greeting}'")
                    if self.tts and not self.interrupted and not self.muted:
                        self.tts.speak(greeting)
                    print("💬 Main: Saudação concluída")
                
                if self.interrupted:
                    print("🛑 Main: Interrompido após saudação")
                    continue

                self.signals.update_status.emit("Ouvindo...")
                if self._conversation_active():
                    self.signals.add_log.emit("Continuidade: pode falar...")
                else:
                    self.signals.add_log.emit("Aguardando comando...")
                print("\n⏺️ Main: Preparando para escutar comando...")
                
                if not self.stt:
                    print("❌ ERRO: STT não disponível")
                    continue

                print(f"⏺️ Main: Chamando STT.listen()...")
                listen_seconds = self.follow_up_listen_seconds if self._conversation_active() else 4
                text = self.stt.listen(seconds=listen_seconds)
                print(f"⏺️ Main: STT.listen() retornou: '{text}'")
                
                if self.interrupted:
                    print("🛑 Main: Interrompido após escuta")
                    continue
                
                self.signals.add_log.emit(f"Você: {text}")
                print(f"\n>>> Você: '{text}'")

                if not text:
                    if self._conversation_active():
                        continue
                    confusion = JarvisPersonality.get_confusion()
                    confusion = self._apply_tone(confusion)
                    print(f"AVISO: {confusion}")
                    if self.tts and not self.muted:
                        self.tts.speak(confusion)
                    continue

                tone_switch = self._maybe_switch_tone(text)
                if tone_switch:
                    self.signals.add_log.emit(f"Jarvis: {tone_switch}")
                    print(f">>> Jarvis: {tone_switch}")
                    if self.tts and not self.muted:
                        self.tts.speak(tone_switch)
                    self.follow_up_until = time.time() + self.follow_up_window_seconds
                    continue

                if self._is_end_phrase(text):
                    self.follow_up_until = 0
                    self.signals.update_status.emit("Pronto - Aguardando hotword")
                    closing = self._apply_tone("Perfeito. Se precisar, é só chamar.")
                    self.signals.add_log.emit(f"Jarvis: {closing}")
                    if self.tts and not self.muted:
                        self.tts.speak(closing)
                    continue

                if self._is_sensitive_command(text):
                    if not self._confirm_sensitive_action(text):
                        self.follow_up_until = time.time() + self.follow_up_window_seconds
                        continue

                # Tenta executar ação
                action_result = None
                if self.actions and not self.interrupted:
                    # Verificar comandos de gestos primeiro
                    if "ativar gestos" in text or "ativar gesto" in text or "ligar gestos" in text:
                        self.enable_gestures()
                        continue
                    elif "desativar gestos" in text or "desativar gesto" in text or "desligar gestos" in text:
                        self.disable_gestures()
                        continue
                    
                    action_result = self.actions.execute(text, self.tts)
                
                if self.interrupted:
                    continue
                
                if action_result:
                    if action_result == "CLARIFY_OPEN_APP":
                        clarify = self._apply_tone("Qual aplicativo você quer abrir? Por exemplo: chrome ou whatsapp.")
                        self.signals.update_status.emit("Aguardando esclarecimento...")
                        self.signals.add_log.emit(f"Jarvis: {clarify}")
                        print(f">>> Jarvis: {clarify}")
                        if self.tts and not self.interrupted and not self.muted:
                            self.tts.speak(clarify)

                        app_answer = self.stt.listen(seconds=4) if self.stt else ""
                        self.signals.add_log.emit(f"Você: {app_answer}")
                        print(f">>> Você: {app_answer}")

                        if app_answer and self.actions and not self.interrupted:
                            action_result = self.actions.execute(f"abrir {app_answer}", self.tts)
                        else:
                            action_result = self._apply_tone("Tudo bem, comando cancelado.")

                    elif action_result == "CLARIFY_SEARCH":
                        clarify = self._apply_tone("O que você quer pesquisar?")
                        self.signals.update_status.emit("Aguardando esclarecimento...")
                        self.signals.add_log.emit(f"Jarvis: {clarify}")
                        print(f">>> Jarvis: {clarify}")
                        if self.tts and not self.interrupted and not self.muted:
                            self.tts.speak(clarify)

                        query_answer = self.stt.listen(seconds=5) if self.stt else ""
                        self.signals.add_log.emit(f"Você: {query_answer}")
                        print(f">>> Você: {query_answer}")

                        if query_answer and self.actions and not self.interrupted:
                            action_result = self.actions.execute(f"pesquise por {query_answer}", self.tts)
                        else:
                            action_result = self._apply_tone("Certo, pesquisa cancelada.")

                    # Verifica se precisa de interação (criar nota sem conteúdo)
                    if action_result == "AGUARDANDO_NOTA":
                        self.signals.update_status.emit("Aguardando resposta...")
                        note_prompt = self._apply_tone("O que deseja anotar?")
                        self.signals.add_log.emit(f"Jarvis: {note_prompt}")
                        print(f">>> Jarvis: {note_prompt}")
                        
                        if self.tts and not self.muted:
                            self.tts.speak(note_prompt)
                        
                        # Espera resposta do usuário
                        if self.interrupted:
                            continue
                        
                        print("\nFale agora... (esperando conteúdo da nota)")
                        note_content = self.stt.listen(seconds=6)
                        
                        if self.interrupted:
                            continue
                        
                        self.signals.add_log.emit(f"Você: {note_content}")
                        print(f"\n>>> Você: '{note_content}'")
                        
                        if note_content:
                            # Salva a nota
                            result = self.actions.save_note_content(note_content)
                            result = self._apply_tone(result)
                            self.signals.add_log.emit(f"Jarvis: {result}")
                            print(f">>> Jarvis: {result}")
                            if self.tts and not self.interrupted and not self.muted:
                                self.tts.speak(result)
                        else:
                            cancel_msg = "Nota cancelada"
                            cancel_msg = self._apply_tone(cancel_msg)
                            self.signals.add_log.emit(f"Jarvis: {cancel_msg}")
                            print(f">>> Jarvis: {cancel_msg}")
                            if self.tts and not self.muted:
                                self.tts.speak(cancel_msg)
                        continue
                    
                    # Ação normal
                    self.signals.update_status.emit("Executando ação...")
                    action_result = self._apply_tone(action_result)
                    self.signals.add_log.emit(f"Jarvis: {action_result}")
                    print(f">>> Jarvis: {action_result}")
                    if self.tts and not self.interrupted and not self.muted:
                        self.tts.speak(action_result)
                    self.follow_up_until = time.time() + self.follow_up_window_seconds
                    continue

                # Consulta IA
                if self.interrupted:
                    continue
                    
                self.signals.update_status.emit("Pensando...")
                print("Pensando...")
                
                if self.brain and not self.interrupted:
                    response = self.brain.ask(text)
                    # Remove emojis da resposta antes de falar (já limpo no brain.py, mas garante)
                    response = response.replace('*', '').strip()
                    response = self._apply_tone(response)
                else:
                    response = "Desculpe, o cérebro não está disponível."
                
                if self.interrupted:
                    continue
                    
                self.signals.add_log.emit(f"Jarvis: {response}")
                print(f">>> Jarvis: {response}\n")

                self.signals.update_status.emit("Falando...")
                if self.tts and not self.interrupted and not self.muted:
                    self.tts.speak(response)

                self.follow_up_until = time.time() + self.follow_up_window_seconds
                
                print("="*60)
                print("Continuidade ativa por alguns segundos...")
                print("="*60 + "\n")
                    
            except KeyboardInterrupt:
                print("\n\nEncerrando JARVIS...")
                self.running = False
                break
            except Exception as e:
                print(f"\nERRO: {e}")
                self.signals.add_log.emit(f"ERRO: {e}")
                import traceback
                traceback.print_exc()
    
    def enable_gestures(self):
        """Ativa modo de controle por gestos"""
        if not self.gesture_mode:
            try:
                self.gesture_thread = GestureThread()
                self.gesture_thread.gesture_detected.connect(self.handle_gesture)
                self.gesture_thread.frame_ready.connect(self.ui.show_gesture_frame)
                self.gesture_thread.start()
                
                # Mostrar mini janela
                self.ui.gesture_label.show()
                
                self.gesture_mode = True
                msg = "Modo gestos ativado! Punho=Parar, 1 dedo=Ativar, 2=Vol+, 3=Vol-, Mão aberta=OK"
                self.signals.add_log.emit(msg)
                print(msg)
                if self.tts and not self.muted:
                    self.tts.speak("Modo gestos ativado.")
            except Exception as e:
                msg = f"Erro ao ativar gestos: {e}"
                self.signals.add_log.emit(msg)
                print(msg)
        else:
            msg = "Gestos já ativos"
            if self.tts and not self.muted:
                self.tts.speak(msg)
    
    def disable_gestures(self):
        """Desativa modo de controle por gestos"""
        if self.gesture_mode and self.gesture_thread:
            self.gesture_thread.stop()
            self.gesture_mode = False
            
            # Esconder mini janela
            self.ui.gesture_label.hide()
            
            msg = "Modo gestos desativado"
            self.signals.add_log.emit(msg)
            print(msg)
            if self.tts and not self.muted:
                self.tts.speak(msg)
    
    def handle_gesture(self, gesture):
        """Processa gesto detectado"""
        print(f">>> GESTO: {gesture}")
        self.signals.add_log.emit(f"GESTO: {gesture}")
        
        if gesture == "FIST":
            # Punho ativa a hotword (simula dizer "olá")
            print(">>> GESTO PUNHO: Ativando hotword...")
            self.signals.add_log.emit("GESTO: Ativando JARVIS")
            
            # Simula detecção da hotword pulando para o estado ativo
            if self.hotword:
                self.hotword.detected = True
            
            if self.tts and not self.muted:
                greeting = JarvisPersonality.get_greeting()
                self.tts.speak(greeting)
        elif gesture == "ONE":
            if self.tts and not self.muted:
                self.tts.speak("Sim chefe")
        elif gesture == "TWO":
            if self.tts and not self.muted:
                self.tts.speak("Volume mais")
        elif gesture == "THREE":
            if self.tts and not self.muted:
                self.tts.speak("Volume menos")
        elif gesture == "OPEN":
            if self.tts and not self.muted:
                self.tts.speak("OK")

    def start(self):
        self.ui.show()
        self.ui.show_status("Inicializando...")
        
        # Thread de inicialização
        init_thread = threading.Thread(target=self.init_components, daemon=True)
        init_thread.start()
        
        # Thread principal (non-daemon)
        def run_jarvis():
            init_thread.join()
            self.jarvis_loop()
        
        main_thread = threading.Thread(target=run_jarvis, daemon=False)
        main_thread.start()
        
        # Loop da UI
        sys.exit(self.app.exec())

if __name__ == "__main__":
    print("\n" + "="*60)
    print("JARVIS - Assistente Virtual")
    print("="*60)
    print("STT com Vosk (offline) + IA Groq (online)")
    print("Diga 'olá' para ativar")
    print("="*60 + "\n")
    
    jarvis = Jarvis()
    jarvis.start()
