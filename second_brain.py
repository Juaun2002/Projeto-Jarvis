"""Second Brain para o Mike.

Mantém um repositório persistente de quatro tipos de memória:
- anotações do usuário (annotations.jsonl)
- ações/eventos do assistente (actions.jsonl)
- perfil rico do usuário (profile.json)
- índice de arquivos locais (files_index.json + files/)

A busca é por token overlap (mesmo padrão de brain.Brain) — sem dependências
novas. Os arquivos JSONL são append-only; quando passam do limite, o arquivo
é truncado para manter só as últimas N entradas.
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from datetime import datetime
from typing import Iterable

from config import (
    SECOND_BRAIN_ACTIONS,
    SECOND_BRAIN_ANNOTATIONS,
    SECOND_BRAIN_DIR,
    SECOND_BRAIN_FILES_DIR,
    SECOND_BRAIN_FILES_INDEX,
    SECOND_BRAIN_MAX_ACTIONS,
    SECOND_BRAIN_MAX_ANNOTATIONS,
    SECOND_BRAIN_MAX_FILE_CHARS,
    SECOND_BRAIN_MAX_PROFILE_FACTS,
    SECOND_BRAIN_PROFILE,
)


# Tags inferidas a partir de palavras-gatilho na fala. Mantém-se curto de
# propósito: tagging pesado vira NLP e não é o objetivo aqui.
_TAG_TRIGGERS = {
    "compras": ("comprar", "mercado", "supermercado", "lista"),
    "saude": ("remedio", "remédio", "medico", "médico", "consulta", "exame"),
    "trabalho": ("reuniao", "reunião", "cliente", "projeto", "entrega", "prazo"),
    "estudo": ("estudar", "ler", "livro", "curso", "aula"),
    "pessoal": ("mae", "mãe", "pai", "amigo", "namorada", "esposa", "filho"),
    "ideia": ("ideia", "talvez", "quem sabe", "pensei"),
    "urgente": ("urgente", "importante", "prioridade", "asap"),
    "comida": ("comida", "receita", "jantar", "almoco", "almoço", "lanche"),
}


class SecondBrain:
    """Camada unificada de memória de longo prazo do Mike."""

    def __init__(self, base_dir: str | None = None):
        self.dir = base_dir or SECOND_BRAIN_DIR
        self.annotations_path = os.path.join(self.dir, "annotations.jsonl")
        self.actions_path = os.path.join(self.dir, "actions.jsonl")
        self.profile_path = os.path.join(self.dir, "profile.json")
        self.files_index_path = os.path.join(self.dir, "files_index.json")
        self.files_dir = os.path.join(self.dir, "files")

        self._ensure_dirs()
        self._profile = self._load_profile()
        self._files_index = self._load_files_index()

    # ------------------------------------------------------------------ I/O

    def _ensure_dirs(self):
        try:
            os.makedirs(self.dir, exist_ok=True)
            os.makedirs(self.files_dir, exist_ok=True)
        except Exception as exc:
            print(f"[SecondBrain] Aviso: não consegui criar diretórios: {exc}")

    def _load_profile(self) -> dict:
        if not os.path.exists(self.profile_path):
            return {
                "name": None,
                "form_of_address": "senhor",
                "preferences": [],
                "routine": {},
                "projects": [],
                "contacts": {},
                "facts": [],
                "updated_at": None,
            }
        try:
            with open(self.profile_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            defaults = {
                "name": None,
                "form_of_address": "senhor",
                "preferences": [],
                "routine": {},
                "projects": [],
                "contacts": {},
                "facts": [],
            }
            for key, value in defaults.items():
                data.setdefault(key, value)
            return data
        except Exception as exc:
            print(f"[SecondBrain] perfil corrompido, recriando: {exc}")
            return {
                "name": None,
                "form_of_address": "senhor",
                "preferences": [],
                "routine": {},
                "projects": [],
                "contacts": {},
                "facts": [],
                "updated_at": None,
            }

    def _save_profile(self):
        try:
            self._profile["updated_at"] = datetime.now().isoformat()
            with open(self.profile_path, "w", encoding="utf-8") as f:
                json.dump(self._profile, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            print(f"[SecondBrain] não consegui salvar perfil: {exc}")

    def _load_files_index(self) -> list[dict]:
        if not os.path.exists(self.files_index_path):
            return []
        try:
            with open(self.files_index_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception as exc:
            print(f"[SecondBrain] files_index corrompido, recriando: {exc}")
            return []

    def _save_files_index(self):
        try:
            with open(self.files_index_path, "w", encoding="utf-8") as f:
                json.dump(self._files_index, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            print(f"[SecondBrain] não consegui salvar files_index: {exc}")

    def _read_jsonl(self, path: str) -> list[dict]:
        if not os.path.exists(path):
            return []
        items: list[dict] = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        items.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except Exception as exc:
            print(f"[SecondBrain] erro lendo {path}: {exc}")
        return items

    def _append_jsonl(self, path: str, entry: dict, max_entries: int):
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as exc:
            print(f"[SecondBrain] erro escrevendo {path}: {exc}")
            return

        try:
            items = self._read_jsonl(path)
            if len(items) > max_entries:
                kept = items[-max_entries:]
                tmp_path = path + ".tmp"
                with open(tmp_path, "w", encoding="utf-8") as f:
                    for item in kept:
                        f.write(json.dumps(item, ensure_ascii=False) + "\n")
                os.replace(tmp_path, path)
        except Exception as exc:
            print(f"[SecondBrain] erro rotacionando {path}: {exc}")

    # -------------------------------------------------------------- anotações

    def _infer_tags(self, text: str) -> list[str]:
        text_lower = (text or "").lower()
        tags: list[str] = []
        for tag, triggers in _TAG_TRIGGERS.items():
            if any(trigger in text_lower for trigger in triggers):
                tags.append(tag)
        return tags

    def add_annotation(self, text: str, tags: list[str] | None = None, source: str = "voice") -> dict:
        """Adiciona uma anotação. Retorna o registro criado."""
        clean = (text or "").strip(" .,!?")
        if not clean:
            raise ValueError("texto da anotação vazio")

        inferred = self._infer_tags(clean)
        merged_tags: list[str] = []
        for tag in (tags or []) + inferred:
            if tag and tag not in merged_tags:
                merged_tags.append(tag)

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        entry = {
            "id": f"ann_{stamp}_{uuid.uuid4().hex[:6]}",
            "text": clean,
            "tags": merged_tags,
            "source": source,
            "created_at": datetime.now().isoformat(),
        }
        self._append_jsonl(self.annotations_path, entry, SECOND_BRAIN_MAX_ANNOTATIONS)
        return entry

    def list_annotations(self, limit: int = 10, tag: str | None = None) -> list[dict]:
        items = self._read_jsonl(self.annotations_path)
        if tag:
            tag_lower = tag.lower()
            items = [it for it in items if tag_lower in [t.lower() for t in it.get("tags", [])]]
        return items[-limit:][::-1]  # mais recentes primeiro

    def forget_annotation(self, query: str) -> dict | None:
        """Remove uma anotação que casa aproximadamente com `query`."""
        items = self._read_jsonl(self.annotations_path)
        if not items:
            return None
        scored = []
        q_tokens = self._tokenize(query)
        for item in items:
            text = item.get("text", "")
            overlap = len(q_tokens & self._tokenize(text))
            if text.lower() in (query or "").lower() or query.lower() in text.lower():
                overlap += 5
            scored.append((overlap, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        if not scored or scored[0][0] == 0:
            return None
        target = scored[0][1]
        remaining = [it for it in items if it.get("id") != target.get("id")]
        try:
            with open(self.annotations_path, "w", encoding="utf-8") as f:
                for it in remaining:
                    f.write(json.dumps(it, ensure_ascii=False) + "\n")
        except Exception as exc:
            print(f"[SecondBrain] erro ao remover anotação: {exc}")
            return None
        return target

    # ----------------------------------------------------------------- ações

    def log_action(self, kind: str, detail: str, result: str = "ok") -> dict:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        entry = {
            "id": f"act_{stamp}_{uuid.uuid4().hex[:6]}",
            "kind": kind,
            "detail": detail,
            "result": result,
            "created_at": datetime.now().isoformat(),
        }
        self._append_jsonl(self.actions_path, entry, SECOND_BRAIN_MAX_ACTIONS)
        return entry

    def recent_actions(self, limit: int = 20, kind: str | None = None) -> list[dict]:
        items = self._read_jsonl(self.actions_path)
        if kind:
            items = [it for it in items if it.get("kind") == kind]
        return items[-limit:][::-1]

    # --------------------------------------------------------------- perfil

    def update_profile(self, key: str, value) -> None:
        if not key:
            return
        self._profile[key] = value
        self._save_profile()

    def add_fact(self, text: str) -> None:
        clean = (text or "").strip(" .,!?")
        if not clean:
            return
        facts = self._profile.setdefault("facts", [])
        if clean.lower() not in {f.lower() for f in facts}:
            facts.append(clean)
            if len(facts) > SECOND_BRAIN_MAX_PROFILE_FACTS:
                facts = facts[-SECOND_BRAIN_MAX_PROFILE_FACTS:]
            self._profile["facts"] = facts
        self._save_profile()

    def remove_fact(self, query: str) -> str | None:
        facts = self._profile.get("facts", [])
        q_lower = (query or "").lower()
        for fact in list(facts):
            if q_lower in fact.lower() or fact.lower() in q_lower:
                facts.remove(fact)
                self._profile["facts"] = facts
                self._save_profile()
                return fact
        return None

    def add_preference(self, text: str) -> None:
        clean = (text or "").strip(" .,!?")
        if not clean:
            return
        prefs = self._profile.setdefault("preferences", [])
        if clean.lower() not in {p.lower() for p in prefs}:
            prefs.append(clean)
            self._profile["facts"] = self._profile.get("facts", [])
            self._save_profile()

    def add_project(self, text: str) -> None:
        clean = (text or "").strip(" .,!?")
        if not clean:
            return
        projects = self._profile.setdefault("projects", [])
        if clean.lower() not in {p.lower() for p in projects}:
            projects.append(clean)
            self._save_profile()

    def set_name(self, name: str) -> None:
        clean = (name or "").strip().title()
        if not clean:
            return
        self._profile["name"] = clean
        self._save_profile()

    def set_form_of_address(self, form: str) -> None:
        clean = (form or "").strip().lower()
        if clean in {"senhor", "chefe", "voce", "você"}:
            self._profile["form_of_address"] = clean
            self._save_profile()

    @property
    def profile(self) -> dict:
        return dict(self._profile)

    # --------------------------------------------------------------- arquivos

    def index_local_files(self, directory: str | None = None) -> int:
        """Indexa arquivos .md/.txt em `directory` (ou files_dir padrão).

        Apenas metadados + preview são guardados; o conteúdo é lido do disco
        no momento da busca.
        """
        target = directory or self.files_dir
        if not os.path.isdir(target):
            return 0

        index: list[dict] = []
        try:
            for root, _dirs, files in os.walk(target):
                for name in files:
                    if not name.lower().endswith((".md", ".txt", ".markdown")):
                        continue
                    full = os.path.join(root, name)
                    try:
                        with open(full, "r", encoding="utf-8") as f:
                            content = f.read(SECOND_BRAIN_MAX_FILE_CHARS)
                        size = os.path.getsize(full)
                        rel = os.path.relpath(full, target).replace("\\", "/")
                        index.append(
                            {
                                "rel_path": rel,
                                "abs_path": full,
                                "size": size,
                                "preview": content[:200],
                                "indexed_at": datetime.now().isoformat(),
                            }
                        )
                    except Exception as exc:
                        print(f"[SecondBrain] erro indexando {full}: {exc}")
        except Exception as exc:
            print(f"[SecondBrain] erro varrendo {target}: {exc}")
            return 0

        self._files_index = index
        self._save_files_index()
        return len(index)

    def search_files(self, prompt: str, k: int = 3) -> list[dict]:
        if not self._files_index:
            return []
        q_tokens = self._tokenize(prompt)
        scored: list[tuple[float, dict, str]] = []
        for entry in self._files_index:
            try:
                with open(entry["abs_path"], "r", encoding="utf-8") as f:
                    content = f.read(SECOND_BRAIN_MAX_FILE_CHARS)
            except Exception:
                continue
            tokens = self._tokenize(content)
            overlap = len(q_tokens & tokens)
            if overlap == 0:
                continue
            score = overlap * 0.7
            scored.append((score, entry, content))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, entry, content in scored[:k]:
            snippet = content[:300].replace("\n", " ").strip()
            results.append(
                {
                    "rel_path": entry["rel_path"],
                    "score": score,
                    "snippet": snippet,
                }
            )
        return results

    # ----------------------------------------------------------------- busca

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-zA-ZÀ-ÿ0-9]+", (text or "").lower())
            if len(token) >= 3
        }

    def _score(
        self,
        text: str,
        q_tokens: set[str],
        weight: float,
        timestamp: str | None,
    ) -> float:
        if not text or not q_tokens:
            return 0.0
        overlap = len(q_tokens & self._tokenize(text))
        if overlap == 0:
            return 0.0
        recency = 0.0
        if timestamp:
            try:
                age = max(1.0, (datetime.now() - datetime.fromisoformat(timestamp)).total_seconds())
                recency = min(1.0, 86400.0 / age)
            except Exception:
                recency = 0.0
        return overlap * weight + recency * 0.2

    def query(self, prompt: str, k: int = 5) -> dict:
        """Busca em todas as fontes da Second Brain. Retorna top-k por fonte."""
        q_tokens = self._tokenize(prompt)

        annotations_scored: list[tuple[float, dict]] = []
        for item in self._read_jsonl(self.annotations_path):
            score = self._score(item.get("text", ""), q_tokens, 1.0, item.get("created_at"))
            if score > 0:
                annotations_scored.append((score, item))
        annotations_scored.sort(key=lambda x: x[0], reverse=True)
        top_annotations = [it for _, it in annotations_scored[:k]]

        actions_scored: list[tuple[float, dict]] = []
        for item in self._read_jsonl(self.actions_path):
            text = f"{item.get('kind', '')} {item.get('detail', '')}"
            score = self._score(text, q_tokens, 0.6, item.get("created_at"))
            if score > 0:
                actions_scored.append((score, item))
        actions_scored.sort(key=lambda x: x[0], reverse=True)
        top_actions = [it for _, it in actions_scored[:k]]

        profile_facts: list[tuple[float, str]] = []
        for fact in self._profile.get("facts", []):
            score = self._score(fact, q_tokens, 0.9, self._profile.get("updated_at"))
            if score > 0:
                profile_facts.append((score, fact))
        for pref in self._profile.get("preferences", []):
            score = self._score(pref, q_tokens, 0.9, self._profile.get("updated_at"))
            if score > 0:
                profile_facts.append((score, pref))
        profile_facts.sort(key=lambda x: x[0], reverse=True)
        top_profile = [f for _, f in profile_facts[:k]]

        top_files = self.search_files(prompt, k=3)

        return {
            "annotations": top_annotations,
            "actions": top_actions,
            "profile_facts": top_profile,
            "files": top_files,
        }

    # ------------------------------------------------------ helpers p/ Brain

    def context_for_prompt(self, prompt: str, k: int = 4) -> dict | None:
        """Retorna um subconjunto pronto para virar seção de prompt LLM."""
        result = self.query(prompt, k=k)
        has_anything = (
            result["annotations"] or result["actions"] or result["profile_facts"] or result["files"]
        )
        if not has_anything:
            return None
        return result
