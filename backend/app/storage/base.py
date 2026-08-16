from pathlib import Path
from typing import Protocol


class Storage(Protocol):
    def save(self, source: Path, key: str) -> str: ...

    def read(self, key: str) -> bytes: ...

    def delete(self, key: str) -> None: ...
