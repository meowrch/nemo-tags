import os
import json
import secrets
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional

from header import DB_DIR
from header import DB_PATH


class TagDatabase:
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = DB_PATH
        
        self.db_path = db_path
        self.tags: List[Dict] = []
        self.index: Dict[str, List[str]] = {}
        self._load()

    def _load(self):
        if not self.db_path.exists():
            self._save()
        
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
        
        self.tags = data.get("tags", [])
        raw_index = data.get("index", {})

        # Разворачиваем алиасы при загрузке
        self.index = {}
        for tag_id, paths in raw_index.items():
            self.index[tag_id] = [self._expand_path(p) for p in paths]

    def _save(self):
        DB_DIR.mkdir(parents=True, exist_ok=True)
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump({"tags": self.tags, "index": self.index}, f, indent=2)

    def _generate_id(self) -> str:
        """Генерирует случайный уникальный идентификатор тега"""
        existing_ids = {t["id"] for t in self.tags}

        while True: # Генерируем 8-символьный hex ID
            tag_id = secrets.token_hex(4)
            if tag_id not in existing_ids:
                return tag_id

    def add_tag(self, name: str, color: str) -> str:
        tag_id = self._generate_id()
        self.tags.append({"id": tag_id, "name": name, "color": color})
        self._save()
        return tag_id

    def get_tags(self) -> List[Dict]:
        return list(self.tags)

    def get_tag_by_id(self, tag_id: str) -> Optional[Dict]:
        for tag in self.tags:
            if tag["id"] == tag_id:
                return tag
        
        return None

    def remove_tag(self, tag_id: str) -> bool:
        before = len(self.tags)
        self.tags = [tag for tag in self.tags if tag["id"] != tag_id]
        self.index.pop(tag_id, None)
        self._save()
        return len(self.tags) != before

    def update_tag(self, tag_id: str, name: str, color: str) -> bool:
        """Обновляет имя и/или цвет тега"""
        for tag in self.tags:
            if tag["id"] == tag_id:
                tag["name"] = name
                tag["color"] = color
                self._save()
                return True

        return False

    def reorder_tags(self, tag_ids: List[str]) -> bool:
        """Изменяет порядок тегов согласно переданному списку ID"""
        if len(tag_ids) != len(self.tags):
            return False

        # Создаём словарь для быстрого поиска
        tag_dict = {tag["id"]: tag for tag in self.tags}

        # Проверяем что все ID существуют
        if not all(tag_id in tag_dict for tag_id in tag_ids):
            return False

        # Переупорядочиваем теги
        self.tags = [tag_dict[tag_id] for tag_id in tag_ids]
        self._save()
        return True

    def assign_tag(self, tag_id: str, file_path: str):
        file_path = str(file_path)
        self.index.setdefault(tag_id, [])

        if file_path not in self.index[tag_id]:
            self.index[tag_id].append(file_path)
            self._save()

    def unassign_tag(self, tag_id: str, file_path: str):
        file_path = str(file_path)
        items = self.index.get(tag_id, [])

        if file_path in items:
            items.remove(file_path)
            self._save()

    def files_by_tag(self, tag_id: str) -> List[str]:
        return list(self.index.get(tag_id, []))

    def tags_for_file(self, file_path: str) -> List[Dict]:
        file_path = str(file_path)
        result = []

        for tag in self.tags:
            if file_path in self.index.get(tag["id"], []):
                result.append(tag)

        return result

    def is_tagged(self, tag_id: str, file_path: str) -> bool:
        file_path = str(file_path)
        return file_path in self.index.get(tag_id, [])

    def flush(self):
        self._save()

    def _expand_path(self, path: str) -> str:
        """Преобразует $HOME и ~ в абсолютный путь"""
        return os.path.expanduser(path.replace("$HOME", "~"))