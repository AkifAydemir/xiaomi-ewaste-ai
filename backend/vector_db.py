"""Lexical retrieval; historical class name retained for API compatibility.

No embedding model downloads or vector-database dependency at startup.
"""
import re
from pathlib import Path
from backend.config import Config


def tokens(text):
    return set(re.findall(r'\w+', text.casefold().replace('ı', 'i')))


class VectorDatabase:
    def __init__(self):
        self.entries = self._parse_dataset(Path(Config.DATASET_PATH).read_text(encoding='utf-8'))
        if not self.entries:
            raise ValueError('Recycling dataset has no valid records')

    def _parse_dataset(self, content):
        entries = []
        for block in re.split(r'(?=^COMPONENT:)', content, flags=re.MULTILINE):
            fields = re.findall(r'^(COMPONENT|CATEGORY|ACTION|PERSPECTIVE|OUTPUT):\s*(.*?)(?=^(?:COMPONENT|CATEGORY|ACTION|PERSPECTIVE|OUTPUT):|\Z)', block, re.MULTILINE | re.DOTALL)
            entry = {key.lower(): value.strip() for key, value in fields}
            if all(entry.get(key) for key in ('component', 'category', 'action', 'perspective', 'output')):
                entries.append(entry)
        return entries

    def search(self, query, perspective=None, n_results=5):
        ranked = []
        for entry in self.entries:
            if perspective and entry['perspective'].casefold() != perspective.casefold():
                continue
            score = sum(weight * len(tokens(query) & tokens(entry[key])) for key, weight in (('component', 3), ('category', 2), ('action', 1)))
            if score:
                ranked.append((score, entry))
        ranked.sort(key=lambda item: item[0], reverse=True)
        selected = [entry for _, entry in ranked[:max(0, n_results)]]
        return {'documents': [[entry['output'] for entry in selected]], 'metadatas': [selected]}
