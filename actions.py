# actions.py
import os
import subprocess
import pyautogui
from datetime import datetime, timedelta
import threading
import time
import psutil
import unicodedata
from config import PROGRAMS


def _result(message, kind=None, detail=None, result="ok"):
    """Monta o payload padrão que Actions.execute devolve."""
    return {"message": message, "kind": kind, "detail": detail, "result": result}


class Actions:
    def __init__(self, second_brain=None):
        self.reminders = []  # Lista de lembretes [(hora, mensagem)]
        self.reminder_thread = None
        self.notes_file = "jarvis_notas.txt"
        self.second_brain = second_brain
        self.start_reminder_checker()
    
    def start_reminder_checker(self):
        """Inicia thread que verifica lembretes"""
        if self.reminder_thread is None or not self.reminder_thread.is_alive():
            self.reminder_thread = threading.Thread(target=self._check_reminders, daemon=True)
            self.reminder_thread.start()
    
    def _check_reminders(self):
        """Thread que verifica lembretes a cada minuto"""
        while True:
            try:
                now = datetime.now()
                for reminder_time, message in self.reminders[:]:
                    if now >= reminder_time:
                        print(f"LEMBRETE: {message}")
                        # Remove o lembrete da lista
                        self.reminders.remove((reminder_time, message))
                        # Aqui você pode adicionar TTS para falar o lembrete
                time.sleep(30)  # Verifica a cada 30 segundos
            except Exception as e:
                print(f"Erro no checker de lembretes: {e}")
                time.sleep(60)
    
    def execute(self, text: str, tts=None):
        """Executa ação baseada no comando de voz.

        Retorna um dict {message, kind, detail, result}:
        - message: texto para falar/logar (ou sentinela "CLARIFY_*" / "AGUARDANDO_NOTA")
        - kind: identificador da ação (para o SecondBrain logar)
        - detail: complemento (nome do app, query, etc.)
        - result: "ok" | "error" | "pending" | "clarify"
        Retorna None quando nenhuma ação casou.
        """
        text = text.lower()
        normalized_text = self._normalize_text(text)

        # === PARE (PRIORIDADE MÁXIMA) ===
        if "pare" in text or "parar" in text or "silencio" in text or "cale-se" in text:
            if tts:
                tts.stop()
            return _result("OK, parando.", kind="stop", detail="tts_interrupt")

        # === LEMBRETES ===
        if "criar lembrete" in text or "me lembre" in text:
            message = self.create_reminder(text, tts)
            return _result(message, kind="reminder_created", detail=text, result="ok" if message and "Erro" not in message else "error")

        if "listar lembretes" in text or "quais lembretes" in text:
            return _result(self.list_reminders(), kind="reminder_list", detail="")

        # === AJUDA / COMANDOS ===
        if "ajuda" in text or "o que você pode fazer" in text or "quais comandos" in text or "listar comandos" in text or "comandos disponíveis" in text:
            return _result(self.show_help(), kind="help", detail="")

        # === HORÁRIO E DATA ===
        if self._is_time_intent(text, normalized_text):
            return _result(self.get_time(), kind="time", detail="current")

        if "que dia é hoje" in text or "que dia é" in text or "data de hoje" in text:
            return _result(self.get_date(), kind="date", detail="today")

        if "data de amanhã" in text or "que dia é amanhã" in text:
            return _result(self.get_tomorrow(), kind="date", detail="tomorrow")

        # === ENERGIA DO SISTEMA ===
        if (
            "suspender computador" in text
            or "suspender pc" in text
            or "colocar em suspensão" in text
            or "colocar em suspensao" in text
            or "encerrar por agora" in text
        ):
            message = self.suspend_pc()
            return _result(message, kind="suspend", detail="pc", result="ok" if "Erro" not in message else "error")

        if "desligar computador" in text or "desligar pc" in text:
            message = self.shutdown_pc(text)
            kind = "shutdown_scheduled" if ("desligado em" in message) else "suspend"
            return _result(message, kind=kind, detail=text)

        # === NOTAS ===
        if "criar nota" in text or "anotar" in text or "nota rápida" in text:
            message = self.create_note(text)
            if message == "AGUARDANDO_NOTA":
                return _result("AGUARDANDO_NOTA", kind="note_pending", detail="", result="pending")
            return _result(message, kind="note_created", detail=text, result="ok" if message and "Erro" not in message else "error")

        if "ler notas" in text or "minhas notas" in text or "listar notas" in text:
            return _result(self.read_notes(), kind="note_list", detail="")

        # === MÍDIA ===
        if "tocar música" in text or "abrir spotify" in text or "abrir spot" in text:
            message = self.open_spotify()
            return _result(message, kind="app_open", detail="spotify", result="ok" if "Erro" not in message and "não" not in message.lower() else "error")

        # === STATUS DO SISTEMA ===
        if "status do sistema" in text or "status sistema" in text or "desempenho" in text:
            return _result(self.system_status(), kind="system_status", detail="cpu_ram_disk")

        # === PAUSAR TRABALHO ===
        if "pausar trabalho" in text or "fazer pausa" in text or "pausa de" in text:
            message = self.work_break()
            return _result(message, kind="work_break", detail=text, result="ok" if message and "Erro" not in message else "error")

        # === BOA NOITE ===
        if "boa noite" in text:
            message = self.goodnight_routine()
            return _result(message, kind="goodnight", detail="close_browsers", result="ok" if message and "Erro" not in message else "error")

        # === DORMIR / DESLIGAR MIKE ===
        if "dormir" in text or "durma" in text or "desligar mike" in text or "fechar mike" in text or "desligar jarvis" in text or "fechar jarvis" in text:
            message = self.sleep_mode()
            return _result(message, kind="sleep", detail="shutdown_mike", result="ok" if message and "Erro" not in message else "error")

        # === HORA DE TRABALHAR ===
        if "hora de trabalhar" in text or "modo trabalho" in text or "motor trabalho" in text or "abrir vs code" in text or "abrir vscode" in text:
            message = self.work_mode()
            return _result(message, kind="work_mode", detail="vscode", result="ok" if "Erro" not in message and "Não" not in message else "error")

        # === PROGRAMAS ===
        for name, path in PROGRAMS.items():
            if name in text:
                self.open_app(path)
                return _result(f"Abrindo {name}.", kind="app_open", detail=name)
        if "abrir" in text and not any(name in text for name in PROGRAMS.keys()):
            return _result("CLARIFY_OPEN_APP", kind="clarify_app", detail="", result="clarify")

        # === PESQUISA WEB ===
        if "pesquise por" in text or "pesquisar" in text:
            query = text.replace("pesquise por", "").replace("pesquisar", "").strip()
            if not query:
                return _result("CLARIFY_SEARCH", kind="clarify_search", detail="", result="clarify")
            self.web_search(query)
            return _result(f"Pesquisando por {query}.", kind="web_search", detail=query)

        return None

    def _normalize_text(self, text: str) -> str:
        base = unicodedata.normalize("NFD", text or "")
        without_accents = "".join(ch for ch in base if unicodedata.category(ch) != "Mn")
        return without_accents.lower().strip()

    def _is_time_intent(self, original_text: str, normalized_text: str) -> bool:
        if "que horas sao" in normalized_text or "que horas" in normalized_text or "horario" in normalized_text:
            return True

        has_hora_token = "hora" in normalized_text or "horas" in normalized_text
        has_time_context = any(
            token in normalized_text
            for token in ["agora", "sao", "estao", "esta", "atual", "neste momento"]
        )

        if has_hora_token and has_time_context:
            return True

        if normalized_text in {"hora", "que hora", "que horas", "hora estao", "hora sao"}:
            return True

        return False
    
    def show_help(self):
        """Mostra todos os comandos disponíveis"""
        help_text = """
COMANDOS DISPONÍVEIS:

HORÁRIO E DATA:
  - Que horas são?
  - Que dia é hoje?
  - Qual a data de amanhã?

LEMBRETES:
  - Me lembre em 10 minutos de fazer café
  - Criar lembrete em 2 horas de reunião
  - Listar lembretes

NOTAS:
  - Criar nota: texto aqui
  - Ler minhas notas

TRABALHO:
  - Hora de trabalhar (Abre VS Code)
  - Pausar trabalho (Pausa de 5 minutos)

SISTEMA:
    - Status do sistema (CPU, RAM, Disco)
    - Encerrar por agora (suspende o computador)
    - Desligar totalmente em X minutos

MÍDIA:
  - Tocar música (Abre Spotify)

ROTINAS:
  - Boa noite (Fecha navegadores)
    - Dormir/Durma (Encerra Mike completamente)

PESQUISA:
  - Pesquise por Python tutorial

CONTROLE:
  - Pare ou Silêncio (Interrompe fala)

AJUDA:
  - Ajuda ou O que você pode fazer?

IA GERAL:
  - Qualquer pergunta será respondida pela IA
        """.strip()
        return help_text
    
    def create_reminder(self, text: str, tts=None):
        """Cria um lembrete com tempo relativo"""
        try:
            # Atalho rápido: "lembrete 5 minutos"
            if text.startswith("lembrete ") and "minuto" in text and "de" not in text and "em" not in text:
                # "lembrete 5 minutos" ou "lembrete cinco minutos"
                words = text.replace("lembrete", "").strip().split()
                minutes = int(''.join(filter(str.isdigit, ' '.join(words[:2]))))
                
                if minutes > 0:
                    reminder_time = datetime.now() + timedelta(minutes=minutes)
                    self.reminders.append((reminder_time, "Lembrete"))
                    time_str = reminder_time.strftime("%H:%M")
                    return f"Lembrete criado para {time_str} ({minutes} minutos)"
            
            # Extrai tempo do comando
            if "em" in text and "minuto" in text:
                # "me lembre em 5 minutos de ligar para joão"
                parts = text.split("em")[1].split("minuto")
                minutes = int(''.join(filter(str.isdigit, parts[0])))
                
                # Extrai mensagem
                if "de" in text:
                    message = text.split("de", 1)[1].strip()
                else:
                    message = "Lembrete"
                
                # Calcula horário do lembrete
                reminder_time = datetime.now() + timedelta(minutes=minutes)
                self.reminders.append((reminder_time, message))
                
                time_str = reminder_time.strftime("%H:%M")
                return f"Lembrete criado para {time_str}: {message}"
            
            elif "em" in text and "hora" in text:
                # "me lembre em 2 horas"
                parts = text.split("em")[1].split("hora")
                hours = int(''.join(filter(str.isdigit, parts[0])))
                
                if "de" in text:
                    message = text.split("de", 1)[1].strip()
                else:
                    message = "Lembrete"
                
                reminder_time = datetime.now() + timedelta(hours=hours)
                self.reminders.append((reminder_time, message))
                
                time_str = reminder_time.strftime("%H:%M")
                return f"Lembrete criado para {time_str}: {message}"
            
            else:
                return "Não entendi o tempo. Diga algo como 'lembrete 5 minutos' ou 'me lembre em 10 minutos de fazer café'"
        
        except Exception as e:
            return f"Erro ao criar lembrete: {e}"
    
    def get_time(self):
        """Retorna a hora atual"""
        now = datetime.now()
        time_str = now.strftime("%H:%M")
        return f"São {time_str}"
    
    def get_date(self):
        """Retorna a data atual"""
        now = datetime.now()
        weekdays = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", 
                   "sexta-feira", "sábado", "domingo"]
        months = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
                 "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
        
        weekday = weekdays[now.weekday()]
        day = now.day
        month = months[now.month - 1]
        year = now.year
        
        return f"Hoje é {weekday}, {day} de {month} de {year}"
    
    def get_tomorrow(self):
        """Retorna a data de amanhã"""
        tomorrow = datetime.now() + timedelta(days=1)
        weekdays = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", 
                   "sexta-feira", "sábado", "domingo"]
        months = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
                 "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
        
        weekday = weekdays[tomorrow.weekday()]
        day = tomorrow.day
        month = months[tomorrow.month - 1]
        
        return f"Amanhã será {weekday}, {day} de {month}"
    
    def shutdown_pc(self, text):
        """Ação de energia: por padrão suspende; desliga apenas se explicitamente solicitado."""
        try:
            explicit_shutdown = any(
                phrase in text
                for phrase in [
                    "desligar totalmente",
                    "desligar de verdade",
                    "desligar agora",
                    "desligar completamente",
                ]
            )

            if not explicit_shutdown:
                return self.suspend_pc()

            # Extrai tempo em minutos
            if "em" in text and "minuto" in text:
                parts = text.split("em")[1].split("minuto")
                minutes = int(''.join(filter(str.isdigit, parts[0])))
                seconds = minutes * 60
                
                # Agenda desligamento (Windows)
                subprocess.run(f"shutdown /s /t {seconds}", shell=True)
                return f"Computador será desligado em {minutes} minutos"
            else:
                return "Diga em quantos minutos desligar. Exemplo: desligar computador em 10 minutos"
        except Exception as e:
            return f"Erro ao agendar desligamento: {e}"

    def suspend_pc(self):
        """Coloca o computador em suspensão."""
        try:
            subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
            return "Certo. Colocando o computador em suspensão."
        except Exception as e:
            return f"Erro ao suspender o computador: {e}"
    
    def create_note(self, text):
        """Cria uma nota rápida (via SecondBrain se disponível; senão cai no .txt legado)."""
        try:
            # Remove comandos de ativação
            if ":" in text:
                note_content = text.split(":", 1)[1].strip()
            else:
                note_content = text.replace("criar nota", "").replace("anotar", "").replace("nota rápida", "").strip()

            if not note_content:
                # Retorna sinal especial para pedir interação
                return "AGUARDANDO_NOTA"  # Sinal para o main_vosk.py processar

            if self.second_brain:
                entry = self.second_brain.add_annotation(note_content)
                return f"Nota criada: {entry['text']}"

            # Adiciona timestamp e salva
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
            with open(self.notes_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {note_content}\n")

            return f"Nota criada: {note_content}"
        except Exception as e:
            return f"Erro ao criar nota: {e}"

    def save_note_content(self, content):
        """Salva conteúdo de nota fornecido pelo usuário."""
        try:
            if self.second_brain:
                entry = self.second_brain.add_annotation(content)
                return f"Nota criada: {entry['text']}"

            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
            with open(self.notes_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {content}\n")
            return f"Nota criada: {content}"
        except Exception as e:
            return f"Erro ao salvar nota: {e}"

    def read_notes(self):
        """Lê as notas salvas (SecondBrain se disponível, senão .txt legado)."""
        try:
            if self.second_brain:
                items = self.second_brain.list_annotations(limit=5)
                if not items:
                    return "Você não tem notas salvas ainda"
                lines = ["Suas últimas notas:"]
                for item in items:
                    when = item.get("created_at", "")
                    if when:
                        try:
                            when = datetime.fromisoformat(when).strftime("%d/%m %H:%M")
                        except Exception:
                            when = ""
                    prefix = f"[{when}] " if when else ""
                    lines.append(f"{prefix}{item.get('text', '')}")
                return "\n".join(lines)

            if not os.path.exists(self.notes_file):
                return "Você não tem notas salvas ainda"

            with open(self.notes_file, "r", encoding="utf-8") as f:
                notes = f.read().strip()

            if not notes:
                return "Você não tem notas salvas ainda"

            # Retorna apenas as últimas 5 notas
            notes_list = notes.split("\n")
            recent_notes = notes_list[-5:]

            result = "Suas últimas notas:\n" + "\n".join(recent_notes)
            return result
        except Exception as e:
            return f"Erro ao ler notas: {e}"
    
    def open_spotify(self):
        """Abre o Spotify instalado no Windows"""
        try:
            # Caminhos do Spotify instalado (Windows Store e versão desktop)
            spotify_paths = [
                os.path.expanduser(r"~\AppData\Local\Microsoft\WindowsApps\Spotify.exe"),  # Windows Store
                os.path.expanduser(r"~\AppData\Roaming\Spotify\Spotify.exe"),  # Desktop version
                r"C:\Program Files\Spotify\Spotify.exe",
                r"C:\Program Files (x86)\Spotify\Spotify.exe",
            ]
            
            opened = False
            for path in spotify_paths:
                if os.path.exists(path):
                    subprocess.Popen([path], shell=True)
                    opened = True
                    break
            
            if opened:
                return "Abrindo Spotify"
            else:
                return "Spotify não encontrado. Verifique se está instalado."
            
        except Exception as e:
            return f"Erro ao abrir Spotify: {e}"
    
    def system_status(self):
        """Retorna status do sistema (CPU, RAM, Disco)"""
        try:
            cpu = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            
            status = f"Status do Sistema:\n"
            status += f"• CPU: {cpu}%\n"
            status += f"• RAM: {ram}%\n"
            status += f"• Disco: {disk}%"
            
            return status
        except Exception as e:
            return f"Erro ao obter status: {e}"
    
    def work_break(self):
        """Pausa de trabalho de 5 minutos"""
        try:
            # Cria lembrete de 5 minutos
            reminder_time = datetime.now() + timedelta(minutes=5)
            self.reminders.append((reminder_time, "Fim da pausa! Hora de voltar ao trabalho"))
            
            time_str = reminder_time.strftime("%H:%M")
            return f"Pausa iniciada! Te aviso às {time_str} para voltar ao trabalho"
        except Exception as e:
            return f"Erro ao iniciar pausa: {e}"
    
    def list_reminders(self):
        """Lista todos os lembretes ativos"""
        if not self.reminders:
            return "Você não tem lembretes pendentes."
        
        result = "Seus lembretes:\n"
        for reminder_time, message in sorted(self.reminders):
            time_str = reminder_time.strftime("%H:%M")
            result += f"- {time_str}: {message}\n"
        return result.strip()
    
    def goodnight_routine(self):
        """Rotina de boa noite"""
        try:
            # Fecha navegadores e apps desnecessários
            apps_to_close = ["chrome.exe", "firefox.exe", "msedge.exe"]
            for app in apps_to_close:
                subprocess.run(f"taskkill /F /IM {app}", shell=True, capture_output=True)
            
            return "Boa noite! Fechei os navegadores para você descansar."
        except Exception as e:
            return "Boa noite! Não consegui fechar alguns aplicativos."
    
    def sleep_mode(self):
        """Rotina de dormir - encerra o Mike completamente"""
        try:
            import sys
            print("\n" + "="*50)
            print("MIKE ENTRANDO EM MODO SLEEP")
            print("="*50)
            
            # Encerra o processo Python completamente
            sys.exit(0)
            
        except Exception as e:
            return f"Erro ao entrar em modo sleep: {e}"
    
    def work_mode(self):
        """Rotina de trabalho - abre VSCode"""
        try:
            # Tenta encontrar VSCode em locais comuns
            vscode_paths = [
                r"C:\Users\jvpes\AppData\Local\Programs\Microsoft VS Code\Code.exe",
                r"C:\Program Files\Microsoft VS Code\Code.exe",
                r"C:\Program Files (x86)\Microsoft VS Code\Code.exe",
            ]
            
            vscode_opened = False
            for path in vscode_paths:
                if os.path.exists(path):
                    subprocess.Popen([path])
                    vscode_opened = True
                    break
            
            if not vscode_opened:
                # Tenta abrir pelo comando 'code' se estiver no PATH
                subprocess.Popen(["code"])
                vscode_opened = True
            
            if vscode_opened:
                return "Modo trabalho ativado! Abrindo Visual Studio Code."
            else:
                return "Não encontrei o VS Code instalado."
        
        except Exception as e:
            return f"Erro ao ativar modo trabalho: {e}"
    
    def open_app(self, path):
        subprocess.Popen(path)
    
    def web_search(self, query):
        subprocess.Popen(
            f'start chrome "https://www.google.com/search?q={query}"', shell=True
        )
