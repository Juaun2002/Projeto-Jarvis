# personality.py - Personalidade e respostas naturais do JARVIS
import random

class JarvisPersonality:
    """Gerencia respostas naturais e personalidade do JARVIS"""
    
    # Saudações ao ser ativado
    GREETINGS = [
        "Sim, senhor. O que deseja?",
        "Às suas ordens, senhor.",
        "Prontinho, senhor. Como posso ajudar?",
        "Estou aqui, senhor.",
        "Ao seu dispor, senhor.",
        "Sim, chefe. O que precisa?",
        "Pronto para ajudar, senhor.",
        "Disponível, senhor. Em que posso ser útil?",
    ]
    
    # Respostas para quando não entender
    CONFUSION = [
        "Desculpe, não compreendi. Pode repetir?",
        "Perdão, senhor, não captei isso. Pode reformular?",
        "Não entendi direito. Quer tentar de novo?",
        "Hmm, não peguei essa. Pode explicar melhor?",
        "Desculpe, senhor, mas não consegui processar. Novamente?",
    ]
    
    # Confirmações de ações
    CONFIRMATIONS = [
        "Feito, senhor.",
        "Concluído.",
        "Está pronto.",
        "Executado com sucesso.",
        "Pronto, senhor.",
        "Realizado.",
        "Tarefa concluída.",
    ]
    
    # Respostas ao ser interrompido
    INTERRUPTED = [
        "Entendido. Cancelando.",
        "Interrompendo, senhor.",
        "OK, parando.",
        "Cancelado, senhor.",
        "Compreendido. Parando.",
    ]
    
    # Resposta ao ativar mudo
    MUTED = [
        "Modo silencioso ativado.",
        "Entrando em modo mudo.",
        "Ficarei quieto, senhor.",
        "Silenciando.",
    ]
    
    # Resposta ao desativar mudo
    UNMUTED = [
        "Voltando ao normal, senhor.",
        "Saindo do modo silencioso.",
        "Pode falar, estou ouvindo.",
        "Modo normal restaurado.",
    ]
    
    # Despedidas ao desligar
    GOODBYES = [
        "Até logo, senhor.",
        "Encerrando. Até breve.",
        "Desligando. Até mais, senhor.",
        "Até a próxima.",
        "Até logo, chefe.",
    ]
    
    # Quando está processando algo
    THINKING = [
        "Deixe-me ver...",
        "Um momento...",
        "Verificando...",
        "Processando...",
        "Analisando...",
        "Hmm, vamos ver...",
        "Calculando...",
    ]
    
    @staticmethod
    def get_greeting():
        """Retorna uma saudação aleatória"""
        return random.choice(JarvisPersonality.GREETINGS)
    
    @staticmethod
    def get_confusion():
        """Retorna uma mensagem de confusão"""
        return random.choice(JarvisPersonality.CONFUSION)
    
    @staticmethod
    def get_confirmation():
        """Retorna uma confirmação"""
        return random.choice(JarvisPersonality.CONFIRMATIONS)
    
    @staticmethod
    def get_interrupted():
        """Retorna resposta de interrupção"""
        return random.choice(JarvisPersonality.INTERRUPTED)
    
    @staticmethod
    def get_muted():
        """Retorna resposta ao mutar"""
        return random.choice(JarvisPersonality.MUTED)
    
    @staticmethod
    def get_unmuted():
        """Retorna resposta ao desmutar"""
        return random.choice(JarvisPersonality.UNMUTED)
    
    @staticmethod
    def get_goodbye():
        """Retorna uma despedida"""
        return random.choice(JarvisPersonality.GOODBYES)
    
    @staticmethod
    def get_thinking():
        """Retorna mensagem de processamento"""
        return random.choice(JarvisPersonality.THINKING)
    
    @staticmethod
    def contextualize_response(response, context=None):
        """Adiciona contexto natural à resposta"""
        if context == "time":
            prefixes = ["", "No momento são ", "Agora são ", ""]
            return random.choice(prefixes) + response
        
        if context == "reminder":
            prefixes = ["Certamente. ", "Claro, senhor. ", "Perfeito. ", ""]
            return random.choice(prefixes) + response
        
        if context == "action":
            prefixes = ["Executando. ", "Em andamento. ", "Iniciando. ", ""]
            return random.choice(prefixes) + response
        
        return response
