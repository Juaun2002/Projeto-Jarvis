# main_vosk.py - Mike com Vosk (gratuito) e hotword
import sys
import threading
import time
import re
import unicodedata
from datetime import datetime
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
from second_brain import SecondBrain
from jarvis_ui import JarvisUI
from personality import JarvisPersonality
from config import ASSISTANT_NAME, FOLLOW_UP_WINDOW_SECONDS, FOLLOW_UP_LISTEN_SECONDS, HOTWORD, HOTWORD_ALIASES

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
        self.second_brain = None
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
            self._log_sb_action("tone_switch", "informal", "ok")
            return "Perfeito. Vou falar de forma mais natural e informal."

        if any(marker in normalized for marker in formal_markers):
            self.tone_mode = "formal"
            self._log_sb_action("tone_switch", "formal", "ok")
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
        self.signals.add_log.emit(f"Mike: {prompt}")
        print(f">>> Mike: {prompt}")
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
        self.signals.add_log.emit(f"Mike: {cancel_msg}")
        if self.tts and not self.muted:
            self.tts.speak(cancel_msg)
        return False

    def init_components(self):
        print("\n" + "="*60)
        print("INICIALIZANDO MIKE COM VOSK")
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
        
        # Second Brain (memória unificada)
        try:
            print("[2.5/5] Second Brain...")
            self.signals.add_log.emit("[2.5/5] Carregando Second Brain...")
            self.second_brain = SecondBrain()
            self.second_brain.index_local_files()
            print("      OK")
            self.signals.add_log.emit("      Second Brain OK")
        except Exception as e:
            print(f"      ERRO: {e}")
            self.signals.add_log.emit(f"      Second Brain falhou: {e}")
            self.second_brain = None

        # Brain
        try:
            print("[3/5] Brain...")
            self.signals.add_log.emit("[3/5] Carregando Brain...")
            self.brain = Brain(second_brain=self.second_brain)
            print("      OK")
            self.signals.add_log.emit("      Brain OK")
        except Exception as e:
            print(f"      ERRO: {e}")
            self.signals.add_log.emit("      Brain falhou")

        # Actions
        try:
            print("[4/5] Actions...")
            self.signals.add_log.emit("[4/5] Carregando Actions...")
            self.actions = Actions(second_brain=self.second_brain)
            print("      OK")
            self.signals.add_log.emit("      Actions OK")
        except Exception as e:
            print(f"      ERRO: {e}")
            self.signals.add_log.emit("      Actions falhou")
        
        # Hotword
        try:
            print("[5/5] Hotword (Vosk)...")
             self.signals.add_log.emit("[5/5] Carregando Hotword...")
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
        print(f"TTS:     {'OK' if self.tts else 'FALHOU'}")""
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
            print(f"✅ Diga '{HOTWORD}' para ativar!")
            self.signals.add_log.emit(f"Diga '{HOTWORD}' para ativar")
        
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
                    self.signals.update_status.emit(f"Aguardando '{HOTWORD}'...")
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
                    self.signals.add_log.emit("MIKE ATIVADO!")
                    print("\n" + "="*60)
                    print("MIKE ATIVADO!")
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
                    self.signals.add_log.emit(f"Mike: {tone_switch}")
                    print(f">>> Mike: {tone_switch}")
                    if self.tts and not self.muted:
                        self.tts.speak(tone_switch)
                    self.follow_up_until = time.time() + self.follow_up_window_seconds
                    continue

                if self._is_end_phrase(text):
                    self.follow_up_until = 0
                    self.signals.update_status.emit("Pronto - Aguardando hotword")
                    closing = self._apply_tone("Perfeito. Se precisar, é só chamar.")
                    self.signals.add_log.emit(f"Mike: {closing}")
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

                    # Comandos de Second Brain (não dependem do roteador do Actions)
                    sb_handled = self._handle_second_brain_command(text)
                    if sb_handled is not None:
                        if sb_handled:
                            self.follow_up_until = time.time() + self.follow_up_window_seconds
                        continue

                    action_result = self.actions.execute(text, self.tts)

                if self.interrupted:
                    continue

                if action_result:
                    # Actions.execute agora devolve dict {message, kind, detail, result}
                    if isinstance(action_result, dict):
                        action_message = action_result.get("message", "")
                        action_kind = action_result.get("kind")
                        action_detail = action_result.get("detail", "")
                        action_status = action_result.get("result", "ok")
                    else:
                        action_message = str(action_result)
                        action_kind = None
                        action_detail = ""
                        action_status = "ok"

                    if action_message == "CLARIFY_OPEN_APP":
                        clarify = self._apply_tone("Qual aplicativo você quer abrir? Por exemplo: chrome ou whatsapp.")
                        self.signals.update_status.emit("Aguardando esclarecimento...")
                        self.signals.add_log.emit(f"Mike: {clarify}")
                        print(f">>> Mike: {clarify}")
                        if self.tts and not self.interrupted and not self.muted:
                            self.tts.speak(clarify)

                        app_answer = self.stt.listen(seconds=4) if self.stt else ""
                        self.signals.add_log.emit(f"Você: {app_answer}")
                        print(f">>> Você: {app_answer}")

                        if app_answer and self.actions and not self.interrupted:
                            sub = self.actions.execute(f"abrir {app_answer}", self.tts)
                            if isinstance(sub, dict):
                                self._log_sb_action(sub.get("kind"), sub.get("detail", app_answer), sub.get("result", "ok"))
                                sub_msg = self._apply_tone(sub.get("message", ""))
                            else:
                                sub_msg = self._apply_tone(str(sub))
                            self.signals.add_log.emit(f"Mike: {sub_msg}")
                            print(f">>> Mike: {sub_msg}")
                            if self.tts and not self.interrupted and not self.muted:
                                self.tts.speak(sub_msg)
                        else:
                            cancel_msg = self._apply_tone("Tudo bem, comando cancelado.")
                            self.signals.add_log.emit(f"Mike: {cancel_msg}")
                            print(f">>> Mike: {cancel_msg}")
                            if self.tts and not self.interrupted and not self.muted:
                                self.tts.speak(cancel_msg)
                        self.follow_up_until = time.time() + self.follow_up_window_seconds
                        continue

                    if action_message == "CLARIFY_SEARCH":
                        clarify = self._apply_tone("O que você quer pesquisar?")
                        self.signals.update_status.emit("Aguardando esclarecimento...")
                        self.signals.add_log.emit(f"Mike: {clarify}")
                        print(f">>> Mike: {clarify}")
                        if self.tts and not self.interrupted and not self.muted:
                            self.tts.speak(clarify)

                        query_answer = self.stt.listen(seconds=5) if self.stt else ""
                        self.signals.add_log.emit(f"Você: {query_answer}")
                        print(f">>> Você: {query_answer}")

                        if query_answer and self.actions and not self.interrupted:
                            sub = self.actions.execute(f"pesquise por {query_answer}", self.tts)
                            if isinstance(sub, dict):
                                self._log_sb_action(sub.get("kind"), sub.get("detail", query_answer), sub.get("result", "ok"))
                                sub_msg = self._apply_tone(sub.get("message", ""))
                            else:
                                sub_msg = self._apply_tone(str(sub))
                            self.signals.add_log.emit(f"Mike: {sub_msg}")
                            print(f">>> Mike: {sub_msg}")
                            if self.tts and not self.interrupted and not self.muted:
                                self.tts.speak(sub_msg)
                        else:
                            cancel_msg = self._apply_tone("Certo, pesquisa cancelada.")
                            self.signals.add_log.emit(f"Mike: {cancel_msg}")
                            print(f">>> Mike: {cancel_msg}")
                            if self.tts and not self.interrupted and not self.muted:
                                self.tts.speak(cancel_msg)
                        self.follow_up_until = time.time() + self.follow_up_window_seconds
                        continue

                    # Verifica se precisa de interação (criar nota sem conteúdo)
                    if action_message == "AGUARDANDO_NOTA":
                        self.signals.update_status.emit("Aguardando resposta...")
                        note_prompt = self._apply_tone("O que deseja anotar?")
                        self.signals.add_log.emit(f"Mike: {note_prompt}")
                        print(f">>> Mike: {note_prompt}")

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
                            result_msg = self.actions.save_note_content(note_content)
                            result_msg = self._apply_tone(result_msg)
                            self._log_sb_action("note_created", note_content, "ok")
                            self.signals.add_log.emit(f"Mike: {result_msg}")
                            print(f">>> Mike: {result_msg}")
                            if self.tts and not self.interrupted and not self.muted:
                                self.tts.speak(result_msg)
                        else:
                            cancel_msg = "Nota cancelada"
                            cancel_msg = self._apply_tone(cancel_msg)
                            self.signals.add_log.emit(f"Mike: {cancel_msg}")
                            print(f">>> Mike: {cancel_msg}")
                            if self.tts and not self.muted:
                                self.tts.speak(cancel_msg)
                        self.follow_up_until = time.time() + self.follow_up_window_seconds
                        continue

                    # Ação normal: loga na Second Brain e fala
                    self._log_sb_action(action_kind or "action", action_detail or text, action_status)
                    self.signals.update_status.emit("Executando ação...")
                    spoken = self._apply_tone(action_message)
                    self.signals.add_log.emit(f"Mike: {spoken}")
                    print(f">>> Mike: {spoken}")
                    if self.tts and not self.interrupted and not self.muted:
                        self.tts.speak(spoken)
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
                    
                self.signals.add_log.emit(f"Mike: {response}")
                print(f">>> Mike: {response}\n")

                self.signals.update_status.emit("Falando...")
                if self.tts and not self.interrupted and not self.muted:
                    self.tts.speak(response)

                self.follow_up_until = time.time() + self.follow_up_window_seconds
                
                print("="*60)
                print("Continuidade ativa por alguns segundos...")
                print("="*60 + "\n")
                    
            except KeyboardInterrupt:
                print("\n\nEncerrando Mike...")
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
                self._log_sb_action("gesture_on", "user_command", "ok")
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

            self._log_sb_action("gesture_off", "user_command", "ok")
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
            self.signals.add_log.emit(f"GESTO: Ativando {ASSISTANT_NAME}")
            
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

    # ----------------------------------------------- helpers Second Brain

    def _speak_response(self, message: str):
        """Aplica o tom atual, loga e fala uma resposta curta."""
        if not message:
            return
        spoken = self._apply_tone(message)
        self.signals.add_log.emit(f"Mike: {spoken}")
        print(f">>> Mike: {spoken}")
        if self.tts and not self.interrupted and not self.muted:
            self.tts.speak(spoken)

    def _log_sb_action(self, kind: str | None, detail: str, result: str = "ok"):
        if not self.second_brain or not kind:
            return
        try:
            self.second_brain.log_action(kind, detail or "", result or "ok")
        except Exception as exc:
            print(f"[SecondBrain] erro log_action: {exc}")

    def _handle_second_brain_command(self, text: str):
        """Comandos de voz que consultam/atualizam a Second Brain.

        Retorna:
        - True  se o comando foi tratado e já houve fala (continue normalmente).
        - False se o comando foi tratado e NÃO deve continuar (sem fala).
        - None  se nenhum comando casou (deixa o Actions tratar).
        """
        if not self.second_brain:
            return None
        lower = (text or "").lower().strip()

        # "o que você sabe sobre mim" / "o que lembra de mim"
        if (
            "o que você sabe sobre mim" in lower
            or "o que voce sabe sobre mim" in lower
            or "o que lembra de mim" in lower
            or "o que você lembra sobre mim" in lower
            or "o que voce lembra sobre mim" in lower
        ):
            if self.brain:
                self._speak_response(self.brain.summarize_profile())
            else:
                self._speak_response("Ainda não tenho muitas informações sobre você.")
            self._log_sb_action("profile_summary", "user_requested", "ok")
            return True

        # "minhas anotações" / "o que eu anotei" / "ler anotações"
        if (
            "minhas anotações" in lower
            or "minhas anotacoes" in lower
            or "o que eu anotei" in lower
            or "ler anotações" in lower
            or "listar anotações" in lower
            or "listar anotacoes" in lower
        ):
            items = self.second_brain.list_annotations(limit=5)
            if not items:
                self._speak_response("Você ainda não tem anotações salvas.")
            else:
                lines = ["Suas últimas anotações são:"]
                for it in items:
                    when = it.get("created_at", "")
                    if when:
                        try:
                            when = datetime.fromisoformat(when).strftime("%d/%m")
                        except Exception:
                            when = ""
                    prefix = f"em {when}, " if when else ""
                    lines.append(f"{prefix}{it.get('text', '')}")
                self._speak_response(". ".join(lines) + ".")
            self._log_sb_action("annotation_list", "user_requested", "ok")
            return True

        # "esqueça a anotação X"
        if lower.startswith("esqueça a anotação") or lower.startswith("esqueca a anotacao") or lower.startswith("apague a anotação") or lower.startswith("apague a anotacao"):
            for prefix in ("esqueça a anotação", "esqueca a anotacao", "apague a anotação", "apague a anotacao"):
                if lower.startswith(prefix):
                    query = text[len(prefix):].strip(" .,!?")
                    if not query:
                        self._speak_response("Qual anotação você quer que eu esqueça?")
                        return True
                    removed = self.second_brain.forget_annotation(query)
                    if removed:
                        self._speak_response(f"Apaguei a anotação: {removed.get('text', '')}.")
                    else:
                        self._speak_response("Não encontrei essa anotação.")
                    self._log_sb_action("annotation_forget", query, "ok" if removed else "not_found")
                    return True

        # "esqueça que X" — remove um fato do perfil
        if lower.startswith("esqueça que") or lower.startswith("esqueca que"):
            for prefix in ("esqueça que", "esqueca que"):
                if lower.startswith(prefix):
                    query = text[len(prefix):].strip(" .,!?")
                    removed = self.second_brain.remove_fact(query) if query else None
                    if removed:
                        self._speak_response(f"Apaguei da minha memória: {removed}.")
                    elif query:
                        self._speak_response("Não encontrei esse fato para apagar.")
                    else:
                        self._speak_response("O que você quer que eu esqueça?")
                    self._log_sb_action("fact_forget", query or "", "ok" if removed else "not_found")
                    return True

        # "anotar X" / "anota que X" / "lembre que X" também caem no roteador
        # explícito do Brain, mas o usuário pode preferir o canal direto:
        if lower.startswith(("anotar que", "anote que", "anota ai", "anota aí")):
            for prefix in ("anotar que", "anote que", "anota ai", "anota aí"):
                if lower.startswith(prefix):
                    payload = text[len(prefix):].strip(" .,!?")
                    if not payload:
                        self._speak_response("O que você quer anotar?")
                        return True
                    entry = self.second_brain.add_annotation(payload)
                    self._speak_response(f"Anotado: {entry['text']}.")
                    self._log_sb_action("annotation_direct", payload, "ok")
                    return True

        # "o que você fez hoje" / "histórico de hoje"
        if "o que você fez" in lower or "o que voce fez" in lower or "histórico de hoje" in lower or "historico de hoje" in lower:
            actions = self.second_brain.recent_actions(limit=10)
            if not actions:
                self._speak_response("Não tenho ações registradas ainda.")
            else:
                lines = ["Hoje eu registrei:"]
                for it in actions:
                    detail = it.get("detail", "").strip()
                    if detail and len(detail) > 50:
                        detail = detail[:47] + "..."
                    lines.append(f"{it.get('kind', '').replace('_', ' ')}: {detail or 'ok'}")
                self._speak_response(". ".join(lines) + ".")
            self._log_sb_action("action_summary", "user_requested", "ok")
            return True

        # "indexar pasta" / "reindexar" — reindexa data/second_brain/files/
        if "indexar pasta" in lower or "reindexar" in lower or "indexar arquivos" in lower:
            try:
                count = self.second_brain.index_local_files()
                if count == 0:
                    self._speak_response(
                        "Não encontrei arquivos na pasta de notas. Coloque arquivos .md ou .txt em data/second_brain/files."
                    )
                else:
                    self._speak_response(f"Indexei {count} arquivo(s) da pasta de notas.")
                self._log_sb_action("files_index", "user_requested", "ok" if count else "empty")
            except Exception as exc:
                self._speak_response(f"Erro ao indexar: {exc}")
            return True

        return None

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
    print(f"{ASSISTANT_NAME} - Assistente Virtual")
    print("="*60)
    print("STT com Vosk (offline) + IA local Ollama")
    print(f"Diga '{HOTWORD}' (maique) para ativar")
    print("="*60 + "\n")
    
    jarvis = Jarvis()
    jarvis.start()
