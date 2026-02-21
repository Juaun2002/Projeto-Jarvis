import json
import os
import re
import time
from datetime import datetime
from urllib import request, error

from config import GROQ_MODEL, GROQ_FALLBACK_MODELS, GROQ_API_KEY, BASE_PATH


class Brain:
    def __init__(self):
        """Inicializa o Brain com contexto conversacional e memória persistente."""
        self.system_context = """Você é JARVIS, assistente de voz em português do Brasil.
Fale de forma natural, confiante e útil, com tom humano e cordial.
Responda em geral entre 1 e 3 frases curtas, com linguagem simples.
Use micro-confirmações naturais quando fizer sentido (ex: "certo", "entendi").
Evite emojis, markdown, listas longas e símbolos decorativos.
Evite repetir exatamente o mesmo começo de resposta em interações seguidas.
Se faltar contexto, faça 1 pergunta curta de esclarecimento."""

        self.conversation_history = []
        self.max_history = 12
        self.session_memories = []
        self.max_session_memories = 12
        self.long_term_memories = []
        self.max_long_term_memories = 80
        self.recent_response_starts = []
        self.user_profile = {
            "name": None,
            "form_of_address": "senhor",
            "preferences": [],
        }
        self._accessible_models_cache = []
        self._accessible_models_cache_at = 0.0

        self.memory_file = os.path.join(BASE_PATH, "jarvis_memoria.json")
        self._load_memory()

    def _groq_headers(self):
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "User-Agent": "jarvis-voice-assistant/1.0 (+python-urllib)",
        }

    def _load_memory(self):
        """Carrega memória de conversas anteriores."""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, "r", encoding="utf-8") as file:
                    data = json.load(file)

                self.conversation_history = data.get("history", [])[-self.max_history :]
                self.session_memories = data.get("session_memories", [])[-self.max_session_memories :]
                self.long_term_memories = data.get("long_term_memories", [])[-self.max_long_term_memories :]
                profile = data.get("profile", {})
                self.user_profile["name"] = profile.get("name")
                self.user_profile["form_of_address"] = profile.get("form_of_address", "senhor")
                self.user_profile["preferences"] = profile.get("preferences", [])[:12]

                for item in self.conversation_history[-3:]:
                    assistant_text = item.get("assistant", "")
                    if assistant_text:
                        self.recent_response_starts.append(assistant_text[:24].lower())
                self.recent_response_starts = self.recent_response_starts[-3:]

                print(f"Memória carregada: {len(self.conversation_history)} interações")
        except Exception as exc:
            print(f"Aviso: Não foi possível carregar memória: {exc}")
            self.conversation_history = []

    def _save_memory(self):
        """Salva memória em arquivo."""
        try:
            with open(self.memory_file, "w", encoding="utf-8") as file:
                json.dump(
                    {
                        "history": self.conversation_history[-self.max_history :],
                        "session_memories": self.session_memories[-self.max_session_memories :],
                        "long_term_memories": self.long_term_memories[-self.max_long_term_memories :],
                        "profile": self.user_profile,
                        "last_updated": datetime.now().isoformat(),
                    },
                    file,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception as exc:
            print(f"Aviso: Não foi possível salvar memória: {exc}")

    def _update_user_profile(self, prompt: str):
        """Extrai preferências simples e forma de tratamento a partir da fala do usuário."""
        text = (prompt or "").strip()
        text_lower = text.lower()

        name_patterns = [
            r"meu nome é\s+([a-zA-ZÀ-ÿ\-']{2,})",
            r"pode me chamar de\s+([a-zA-ZÀ-ÿ\-']{2,})",
            r"me chama de\s+([a-zA-ZÀ-ÿ\-']{2,})",
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text_lower)
            if match:
                self.user_profile["name"] = match.group(1).strip().title()
                break

        if "me chama de chefe" in text_lower:
            self.user_profile["form_of_address"] = "chefe"
        elif "me chama de senhor" in text_lower:
            self.user_profile["form_of_address"] = "senhor"

        pref_patterns = [
            r"eu gosto de\s+(.+)",
            r"eu prefiro\s+(.+)",
            r"minha preferência é\s+(.+)",
        ]
        for pattern in pref_patterns:
            match = re.search(pattern, text_lower)
            if match:
                pref = match.group(1).strip(" .,!?")
                if pref and pref not in self.user_profile["preferences"]:
                    self.user_profile["preferences"].append(pref)
                    self.user_profile["preferences"] = self.user_profile["preferences"][-12:]

    def _tokenize(self, text: str):
        return {token for token in re.findall(r"[a-zA-ZÀ-ÿ0-9]+", (text or "").lower()) if len(token) >= 3}

    def _add_session_memory(self, memory_text: str):
        memory_text = (memory_text or "").strip()
        if not memory_text:
            return

        self.session_memories.append(
            {
                "content": memory_text,
                "timestamp": datetime.now().isoformat(),
            }
        )
        if len(self.session_memories) > self.max_session_memories:
            self.session_memories = self.session_memories[-self.max_session_memories :]

    def _add_long_term_memory(self, memory_text: str, source: str = "inferred", importance: int = 1):
        memory_text = (memory_text or "").strip(" .,!?")
        if not memory_text:
            return

        content_lower = memory_text.lower()
        for existing in self.long_term_memories:
            if existing.get("content", "").lower() == content_lower:
                existing["timestamp"] = datetime.now().isoformat()
                existing["importance"] = max(int(existing.get("importance", 1)), int(importance))
                existing["source"] = source
                return

        self.long_term_memories.append(
            {
                "content": memory_text,
                "source": source,
                "importance": max(1, min(3, int(importance))),
                "timestamp": datetime.now().isoformat(),
            }
        )
        if len(self.long_term_memories) > self.max_long_term_memories:
            self.long_term_memories = self.long_term_memories[-self.max_long_term_memories :]

    def _extract_explicit_memory(self, prompt: str):
        """Captura comandos explícitos de memória do usuário."""
        text_lower = (prompt or "").lower().strip()
        patterns = [
            r"lembre\s+(?:que\s+)?(.+)",
            r"não\s+esquece\s+(?:que\s+)?(.+)",
            r"nao\s+esquece\s+(?:que\s+)?(.+)",
            r"guarde\s+(?:que\s+)?(.+)",
            r"anota\s+que\s+(.+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                content = match.group(1).strip(" .,!?")
                if content:
                    self._add_long_term_memory(content, source="explicit", importance=3)
                    return content
        return None

    def _get_relevant_session_memories(self, user_prompt: str, limit: int = 3):
        if not self.session_memories:
            return []

        prompt_tokens = self._tokenize(user_prompt)
        if not prompt_tokens:
            return [item.get("content", "") for item in self.session_memories[-limit:]]

        scored = []
        for item in self.session_memories[-self.max_session_memories :]:
            content = item.get("content", "")
            tokens = self._tokenize(content)
            overlap = len(prompt_tokens & tokens)
            if overlap > 0:
                scored.append((overlap, content))

        scored.sort(key=lambda entry: entry[0], reverse=True)
        selected = [content for _, content in scored[:limit]]

        if not selected:
            selected = [item.get("content", "") for item in self.session_memories[-limit:]]
        return selected

    def _get_relevant_long_term_memories(self, user_prompt: str, limit: int = 4):
        if not self.long_term_memories:
            return []

        prompt_tokens = self._tokenize(user_prompt)
        scored = []
        now = datetime.now()

        for item in self.long_term_memories:
            content = item.get("content", "")
            tokens = self._tokenize(content)
            overlap = len(prompt_tokens & tokens) if prompt_tokens else 0

            timestamp = item.get("timestamp")
            recency_bonus = 0.0
            if timestamp:
                try:
                    age_seconds = max(1.0, (now - datetime.fromisoformat(timestamp)).total_seconds())
                    recency_bonus = min(1.0, 86400.0 / age_seconds)
                except Exception:
                    recency_bonus = 0.0

            importance = float(item.get("importance", 1))
            score = (overlap * 1.7) + (importance * 0.9) + recency_bonus
            scored.append((score, content))

        scored.sort(key=lambda entry: entry[0], reverse=True)
        return [content for _, content in scored[:limit] if content]

    def _get_relevant_history(self, user_prompt: str):
        """Seleciona histórico recente e relevante por palavras-chave simples."""
        if not self.conversation_history:
            return []

        tokens = {token for token in re.findall(r"[a-zA-ZÀ-ÿ0-9]+", user_prompt.lower()) if len(token) >= 4}
        if not tokens:
            return self.conversation_history[-3:]

        scored = []
        for item in self.conversation_history[-10:]:
            text = f"{item.get('user', '')} {item.get('assistant', '')}".lower()
            score = sum(1 for token in tokens if token in text)
            if score > 0:
                scored.append((score, item))

        scored.sort(key=lambda entry: entry[0], reverse=True)
        relevant = [item for _, item in scored[:2]]

        recent = self.conversation_history[-2:]
        merged = []
        for item in relevant + recent:
            if item not in merged:
                merged.append(item)
        return merged[-4:]

    def _is_simple_factual_question(self, user_prompt: str) -> bool:
        text = (user_prompt or "").strip().lower()
        if not text:
            return False
        if len(text) > 90:
            return False

        starts = (
            "qual ",
            "quem ",
            "quando ",
            "onde ",
            "quanto ",
            "como ",
            "por que ",
            "o que ",
            "quais ",
            "que "
        )
        return text.endswith("?") or text.startswith(starts)

    def _build_prompt_with_context(self, user_prompt: str) -> str:
        """Monta prompt com perfil e contexto recente/relevante."""
        sections = [self.system_context]
        factual_mode = self._is_simple_factual_question(user_prompt)

        profile_lines = []
        if self.user_profile.get("name"):
            profile_lines.append(f"Nome do usuário: {self.user_profile['name']}")
        if self.user_profile.get("form_of_address"):
            profile_lines.append(f"Tratamento preferido: {self.user_profile['form_of_address']}")
        if self.user_profile.get("preferences"):
            profile_lines.append("Preferências: " + ", ".join(self.user_profile["preferences"][-5:]))

        if profile_lines:
            sections.append("Contexto de perfil:\n" + "\n".join(profile_lines))

        if not factual_mode:
            relevant_history = self._get_relevant_history(user_prompt)
            if relevant_history:
                lines = []
                for item in relevant_history:
                    lines.append(f"Usuário: {item.get('user', '')}")
                    lines.append(f"Jarvis: {item.get('assistant', '')}")
                sections.append("Contexto de conversa:\n" + "\n".join(lines))

            relevant_session = self._get_relevant_session_memories(user_prompt)
            if relevant_session:
                sections.append("Memória da sessão:\n" + "\n".join(f"- {item}" for item in relevant_session))

            relevant_long_term = self._get_relevant_long_term_memories(user_prompt)
            if relevant_long_term:
                sections.append("Memória de longo prazo relevante:\n" + "\n".join(f"- {item}" for item in relevant_long_term))

        sections.append(f"Usuário: {user_prompt}\nJarvis:")
        return "\n\n".join(sections)

    def _ask_groq_with_model(self, prompt_text: str, model_name: str) -> str:
        payload = {
            "model": model_name,
            "temperature": 0.55,
            "messages": [
                {"role": "system", "content": self.system_context},
                {"role": "user", "content": prompt_text},
            ],
        }

        req = request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=self._groq_headers(),
            method="POST",
        )

        with request.urlopen(req, timeout=25) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw)
            return data["choices"][0]["message"]["content"].strip()

    def _parse_groq_http_error(self, http_err: error.HTTPError):
        raw_details = ""
        code = None
        message = ""

        try:
            raw_details = http_err.read().decode("utf-8", errors="ignore")
            payload = json.loads(raw_details) if raw_details else {}
            err_obj = payload.get("error", {}) if isinstance(payload, dict) else {}
            code = err_obj.get("code")
            message = (err_obj.get("message") or "").strip()
        except Exception:
            pass

        if not code and raw_details:
            code_match = re.search(r"error\s*code\s*:\s*(\d+)", raw_details, flags=re.IGNORECASE)
            if code_match:
                code = code_match.group(1)

        if not message:
            message = str(http_err.reason or "")

        return {
            "http_status": getattr(http_err, "code", None),
            "code": code,
            "message": message,
            "raw": raw_details,
        }

    def _fetch_accessible_groq_models(self, force_refresh: bool = False):
        """Busca modelos acessíveis para a chave atual usando endpoint /models."""
        now = time.time()
        if (
            not force_refresh
            and self._accessible_models_cache
            and (now - self._accessible_models_cache_at) < 300
        ):
            return self._accessible_models_cache[:]

        req = request.Request(
            "https://api.groq.com/openai/v1/models",
            headers=self._groq_headers(),
            method="GET",
        )

        with request.urlopen(req, timeout=15) as response:
            raw = response.read().decode("utf-8")
            payload = json.loads(raw)

        data = payload.get("data", []) if isinstance(payload, dict) else []
        model_ids = []
        for item in data:
            if isinstance(item, dict):
                model_id = (item.get("id") or "").strip()
                if model_id:
                    model_ids.append(model_id)

        self._accessible_models_cache = model_ids
        self._accessible_models_cache_at = now
        return model_ids[:]

    def _ask_groq(self, prompt_text: str) -> str:
        """Consulta Groq com fallback entre modelos permitidos."""
        if not GROQ_API_KEY:
            return "Desculpe, senhor, a chave da Groq não foi configurada. Defina GROQ_API_KEY."

        model_candidates = [GROQ_MODEL] + [model for model in GROQ_FALLBACK_MODELS if model != GROQ_MODEL]
        last_error = None
        last_http_status = 0
        last_error_code = ""
        transient_failures = 0
        discovered_after_403 = False
        attempted_models = set()

        print(f"🤖 Brain: Tentando Groq com modelos: {', '.join(model_candidates)}")

        while model_candidates:
            model_name = model_candidates.pop(0)
            if model_name in attempted_models:
                continue
            attempted_models.add(model_name)

            for attempt in range(2):
                try:
                    return self._ask_groq_with_model(prompt_text, model_name)
                except error.HTTPError as http_err:
                    err_info = self._parse_groq_http_error(http_err)
                    last_error = err_info.get("message") or err_info.get("raw") or str(http_err)
                    error_code = str(err_info.get("code") or "").strip()
                    http_status = int(err_info.get("http_status") or 0)
                    last_http_status = http_status
                    last_error_code = error_code

                    print(
                        f"⚠️ Groq falhou | modelo={model_name} | tentativa={attempt + 1}/2 | "
                        f"http={http_status} | code={error_code or '-'} | detalhe={last_error}"
                    )

                    if http_status == 403 and not discovered_after_403:
                        discovered_after_403 = True
                        try:
                            discovered_models = self._fetch_accessible_groq_models(force_refresh=True)
                            extras = [m for m in discovered_models if m not in attempted_models and m not in model_candidates]
                            if extras:
                                print(f"🔎 Groq: modelos acessíveis detectados: {', '.join(extras)}")
                                model_candidates.extend(extras)
                        except Exception as discover_exc:
                            print(f"⚠️ Groq: não foi possível listar modelos acessíveis: {discover_exc}")

                    is_transient = error_code == "1010" or http_status in (429, 500, 502, 503, 504)
                    if is_transient:
                        transient_failures += 1
                        if attempt == 0:
                            time.sleep(0.6)
                            continue
                except Exception as exc:
                    last_error = str(exc)
                    print(
                        f"⚠️ Groq exceção | modelo={model_name} | tentativa={attempt + 1}/2 | detalhe={last_error}"
                    )
                    if attempt == 0:
                        time.sleep(0.4)
                        continue

                break

        if transient_failures > 0:
            return "Desculpe, senhor, a Groq está instável no momento. Tente novamente em alguns segundos."

        if last_http_status == 403 and last_error_code == "1010":
            return "Desculpe, senhor, o acesso à Groq foi bloqueado (erro 1010). Verifique rede, VPN/proxy e permissões da chave no painel Groq."

        if last_http_status == 401:
            return "Desculpe, senhor, a chave da Groq parece inválida ou expirada."
        if last_http_status == 403:
            return "Desculpe, senhor, sua conta não tem permissão para este modelo gratuito agora."
        if last_http_status == 404:
            return "Desculpe, senhor, não encontrei um modelo gratuito disponível com essa configuração."
        if last_http_status == 429:
            return "Desculpe, senhor, o limite da Groq foi atingido agora. Tente novamente em instantes."
        if last_error_code == "insufficient_quota":
            return "Desculpe, senhor, a cota gratuita da Groq foi atingida."

        return "Desculpe, senhor, não consegui resposta da Groq agora. Verifique a chave e os modelos gratuitos configurados."

    def _clean_response(self, text: str) -> str:
        """Remove ruído visual da resposta e compacta espaços."""
        emoji_pattern = re.compile(
            "["
            u"\U0001F600-\U0001F64F"
            u"\U0001F300-\U0001F5FF"
            u"\U0001F680-\U0001F6FF"
            u"\U0001F1E0-\U0001F1FF"
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            u"\U0001F900-\U0001F9FF"
            u"\U0001FA00-\U0001FAFF"
            "]+",
            flags=re.UNICODE,
        )

        text = emoji_pattern.sub("", text or "")
        text = text.replace("*", "")
        text = text.replace("```", "")
        text = re.sub(r"^\s*[-•]\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _humanize_response(self, text: str) -> str:
        """Ajusta tom final para resposta curta e natural."""
        if not text:
            return "Desculpe, não consegui formular uma resposta agora."

        cleaned = text.strip()
        if len(cleaned) > 420:
            sentences = re.split(r"(?<=[.!?])\s+", cleaned)
            cleaned = " ".join(sentences[:3]).strip()

        start = cleaned[:24].lower()
        if start in self.recent_response_starts and len(cleaned) > 30:
            cleaned = cleaned[0].lower() + cleaned[1:]

        self.recent_response_starts.append(cleaned[:24].lower())
        self.recent_response_starts = self.recent_response_starts[-3:]

        return cleaned

    def _looks_like_unavailability_reply(self, user_prompt: str, assistant_text: str) -> bool:
        prompt_lower = (user_prompt or "").lower()
        if any(token in prompt_lower for token in ["groq", "api", "modelo", "chave"]):
            return False

        text_lower = (assistant_text or "").lower()
        markers = [
            "groq",
            "indisponível",
            "não está disponível",
            "nao está disponível",
            "sem resposta",
            "verificar minha conta",
            "alternativa",
            "banco de dados interno",
        ]
        return any(marker in text_lower for marker in markers)

    def _strip_unavailability_preface(self, text: str) -> str:
        sentences = [item.strip() for item in re.split(r"(?<=[.!?])\s+", (text or "").strip()) if item.strip()]
        if len(sentences) <= 1:
            return text

        markers = [
            "groq",
            "indisponível",
            "não está disponível",
            "nao está disponível",
            "sem resposta",
            "alternativa",
            "banco de dados interno",
        ]

        filtered = [s for s in sentences if not any(marker in s.lower() for marker in markers)]
        if filtered:
            return " ".join(filtered).strip()
        return text

    def _strip_meta_preface(self, text: str) -> str:
        sentences = [item.strip() for item in re.split(r"(?<=[.!?])\s+", (text or "").strip()) if item.strip()]
        if len(sentences) <= 1:
            return text

        meta_markers = [
            "acho que",
            "acredito que",
            "vou ",
            "posso ",
            "já resolvi",
            "anteriormente",
            "vou verificar",
            "eu ",
        ]

        first_sentence = sentences[0].lower()
        if any(marker in first_sentence for marker in meta_markers):
            return " ".join(sentences[1:]).strip()
        return text

    def ask(self, prompt: str) -> str:
        """Consulta IA com contexto, memória e estilo conversacional."""
        prompt = (prompt or "").strip()
        if not prompt:
            return "Pode repetir? Não captei sua fala."

        explicit_memory = self._extract_explicit_memory(prompt)
        self._update_user_profile(prompt)

        if explicit_memory:
            self._save_memory()
            return "Certo, vou lembrar disso."

        self._add_session_memory(f"Usuário disse: {prompt}")
        full_prompt = self._build_prompt_with_context(prompt)

        output = self._ask_groq(full_prompt)
        if output:
            clean_response = self._humanize_response(self._clean_response(output))

            if self._looks_like_unavailability_reply(prompt, clean_response):
                retry_prompt = (
                    "Responda diretamente à pergunta do usuário em português do Brasil, "
                    "de forma objetiva, em no máximo duas frases, e sem metacomentários.\n\n"
                    f"Pergunta do usuário: {prompt}"
                )
                retry_output = self._ask_groq(retry_prompt)
                if retry_output:
                    clean_response = self._humanize_response(self._clean_response(retry_output))

            clean_response = self._strip_unavailability_preface(clean_response)
            clean_response = self._strip_meta_preface(clean_response)

            self._add_session_memory(f"Jarvis respondeu: {clean_response}")

            self.conversation_history.append(
                {
                    "user": prompt,
                    "assistant": clean_response,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            if len(self.conversation_history) > self.max_history:
                self.conversation_history = self.conversation_history[-self.max_history :]

            self._save_memory()
            return clean_response

        return "Desculpe, senhor, sem resposta."
