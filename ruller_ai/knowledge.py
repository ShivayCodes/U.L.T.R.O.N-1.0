"""Simple offline document store and transparent lexical retrieval."""
import csv
import re
import threading
from pathlib import Path
from typing import Any

from .storage import read_json, write_json

TOKEN_RE = re.compile(r"[a-zA-Z0-9_'-]+")


def tokens(text: str) -> set[str]:
    return {token.casefold() for token in TOKEN_RE.findall(text) if len(token) > 1}


class KnowledgeBase:
    SUPPORTED = {".txt", ".md", ".rst", ".py", ".json", ".csv", ".html", ".xml", ".pdf", ".xlsx", ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp"}
    MAX_FILE_BYTES = 1_000_000
    MAX_DOCUMENT_BYTES = 20 * 1024 * 1024
    MAX_CSV_BYTES = 200 * 1024 * 1024
    MAX_ITEM_CHARS = 20_000
    MAX_CSV_FIELD_CHARS = MAX_ITEM_CHARS
    MAX_EXTRACTED_CHARS = 1_000_000
    MAX_SPREADSHEET_ROWS = 10_000
    _csv_limit_lock = threading.Lock()

    def __init__(self, path: Path, max_items: int = 5_000) -> None:
        self.path = path
        self.max_items = max(1, max_items)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._items: list[dict[str, Any]] = read_json(path, [])
        if not isinstance(self._items, list):
            raise RuntimeError(f"Invalid knowledge format in {path}; expected a JSON list.")
        self._reset_index()
        for item in self._items:
            self._index_item(item)

    def _reset_index(self) -> None:
        self._next_id = 0
        self._order: list[int] = []
        self._entries: dict[int, tuple[dict[str, Any], set[str]]] = {}
        self._postings: dict[str, set[int]] = {}
        self._fingerprint_counts: dict[tuple[Any, Any], int] = {}

    @property
    def count(self) -> int:
        return len(self._items)

    def _index_item(self, item: dict[str, Any]) -> int:
        item_id = self._next_id
        self._next_id += 1
        item_tokens = tokens(str(item.get("text", "")))
        self._order.append(item_id)
        self._entries[item_id] = (item, item_tokens)
        for token in item_tokens:
            self._postings.setdefault(token, set()).add(item_id)
        fingerprint = (item.get("source"), item.get("text"))
        self._fingerprint_counts[fingerprint] = self._fingerprint_counts.get(fingerprint, 0) + 1
        return item_id

    def _remove_oldest(self) -> None:
        item_id = self._order.pop(0)
        item, item_tokens = self._entries.pop(item_id)
        for token in item_tokens:
            posting = self._postings[token]
            posting.remove(item_id)
            if not posting:
                del self._postings[token]
        fingerprint = (item.get("source"), item.get("text"))
        remaining = self._fingerprint_counts[fingerprint] - 1
        if remaining:
            self._fingerprint_counts[fingerprint] = remaining
        else:
            del self._fingerprint_counts[fingerprint]

    def _add_text(self, text: str, source: str) -> bool:
        cleaned = text.strip()
        if not cleaned:
            return False
        record = {"text": cleaned[:self.MAX_ITEM_CHARS], "source": source[:500]}
        fingerprint = (record["source"], record["text"])
        if self._fingerprint_counts.get(fingerprint, 0):
            return False
        self._items.append(record)
        self._index_item(record)
        if len(self._items) > self.max_items:
            self._items = self._items[-self.max_items:]
            self._remove_oldest()
        return True

    def add_text(self, text: str, source: str = "manual") -> bool:
        added = self._add_text(text, source)
        if added:
            write_json(self.path, self._items)
        return added

    def _add_sections(self, sections: list[str], source: str) -> int:
        original_items = self._items.copy()
        added = 0
        try:
            for section in sections:
                added += self._add_text(section, source)
            if added:
                write_json(self.path, self._items)
            return added
        except Exception:
            self._restore_items(original_items)
            raise

    def ingest_file(self, path: Path) -> int:
        suffix = path.suffix.casefold()
        if suffix == ".csv":
            return self.ingest_csv(path)
        if suffix not in self.SUPPORTED:
            raise ValueError(f"Unsupported file type: {path.suffix or '(no extension)'}")
        if not path.is_file():
            raise FileNotFoundError(f"Not a file: {path}")
        if suffix in {".pdf", ".xlsx"} or suffix in {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp"}:
            if path.stat().st_size > self.MAX_DOCUMENT_BYTES:
                raise ValueError("PDF, spreadsheet, or image files larger than 20 MB are not accepted.")
            if suffix == ".pdf":
                return self._ingest_pdf(path)
            if suffix == ".xlsx":
                return self._ingest_xlsx(path)
            return self._ingest_image(path)
        if path.stat().st_size > self.MAX_FILE_BYTES:
            raise ValueError("Files larger than 1 MB are not accepted.")
        content = path.read_text(encoding="utf-8", errors="replace")
        chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n", content) if chunk.strip()]
        return self._add_sections(chunks, str(path))

    def _ingest_pdf(self, path: Path) -> int:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("PDF import requires the optional 'pypdf' package. Install it with: pip install 'ultron-1-0[pdf]'") from exc
        try:
            reader = PdfReader(str(path))
            sections: list[str] = []
            extracted = 0
            for number, page in enumerate(reader.pages, 1):
                text = (page.extract_text() or "").strip()
                if text:
                    section = f"Page {number}\n{text}"
                    extracted += len(section)
                    if extracted > self.MAX_EXTRACTED_CHARS:
                        raise ValueError("Extracted document text exceeds the 1 MB limit.")
                    sections.append(section)
            return self._add_sections(sections, str(path))
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"Could not read PDF: {exc}") from exc

    def _ingest_xlsx(self, path: Path) -> int:
        try:
            from openpyxl import load_workbook
        except ImportError as exc:
            raise RuntimeError("Spreadsheet import requires the optional 'openpyxl' package. Install it with: pip install 'ultron-1-0[spreadsheets]'") from exc
        sections: list[str] = []
        extracted = 0
        workbook = None
        try:
            workbook = load_workbook(path, read_only=True, data_only=True)
            for sheet in workbook.worksheets:
                rows = sheet.iter_rows(values_only=True)
                headers = next(rows, None)
                if headers is None:
                    continue
                labels = [str(value).strip() if value is not None else f"Column {i + 1}" for i, value in enumerate(headers)]
                for row_number, row in enumerate(rows, 2):
                    if row_number > self.MAX_SPREADSHEET_ROWS + 1:
                        raise ValueError(f"Spreadsheet exceeds {self.MAX_SPREADSHEET_ROWS} data rows per sheet.")
                    cells = ["" if value is None else str(value) for value in row]
                    text = self._format_csv_row(labels, cells)
                    if text:
                        passage = f"Sheet: {sheet.title} | Row {row_number}\n{text}"
                        extracted += len(passage)
                        if extracted > self.MAX_EXTRACTED_CHARS:
                            raise ValueError("Extracted spreadsheet text exceeds the 1 MB limit.")
                        sections.append(passage)
            return self._add_sections(sections, str(path))
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"Could not read spreadsheet: {exc}") from exc
        finally:
            if workbook is not None:
                workbook.close()

    def _ingest_image(self, path: Path) -> int:
        from .vision import extract_text_from_image
        summary = extract_text_from_image(path)
        if not summary.raw_text.strip():
            return 0
        return self._add_sections(["Text recognized in image:\n" + summary.raw_text[:self.MAX_EXTRACTED_CHARS]], str(path))

    @staticmethod
    def _format_csv_row(headers: list[str], row: list[str]) -> str:
        parts: list[str] = []
        remaining = KnowledgeBase.MAX_ITEM_CHARS
        for index, value in enumerate(row):
            if not value.strip() or remaining <= 0:
                continue
            label = headers[index] if index < len(headers) else f"Column {index + 1}"
            fragment = f"{label}: {value.strip()}"
            if parts:
                fragment = " | " + fragment
            parts.append(fragment[:remaining])
            remaining -= min(len(fragment), remaining)
        return "".join(parts)

    def _restore_items(self, items: list[dict[str, Any]]) -> None:
        self._items = items
        self._reset_index()
        for item in self._items:
            self._index_item(item)

    def ingest_csv(self, path: Path) -> int:
        """Stream UTF-8 CSV rows into local retrieval; enforce explicit field limits."""
        if path.suffix.casefold() != ".csv":
            raise ValueError("Dataset files must use the .csv extension.")
        if not path.is_file():
            raise FileNotFoundError(f"Not a file: {path}")
        if path.stat().st_size > self.MAX_CSV_BYTES:
            raise ValueError("CSV datasets larger than 200 MB are not accepted.")

        original_items = self._items.copy()
        added = 0
        with self._csv_limit_lock:
            previous_limit = csv.field_size_limit()
            try:
                csv.field_size_limit(self.MAX_CSV_FIELD_CHARS)
                with path.open("r", encoding="utf-8-sig", newline="") as stream:
                    reader = csv.reader(stream, strict=True)
                    headers = next(reader, None)
                    if headers is not None:
                        headers = [header.strip() or f"Column {i + 1}" for i, header in enumerate(headers)]
                        for row in reader:
                            text = self._format_csv_row(headers, row)
                            if text:
                                added += self._add_text(text, str(path))
                if added:
                    write_json(self.path, self._items)
                return added
            except UnicodeError as exc:
                self._restore_items(original_items)
                raise ValueError("CSV is not valid UTF-8.") from exc
            except csv.Error as exc:
                self._restore_items(original_items)
                if "field larger than field limit" in str(exc).casefold():
                    raise ValueError(f"CSV field exceeds the {self.MAX_CSV_FIELD_CHARS}-character limit.") from exc
                raise ValueError(f"Malformed CSV dataset: {exc}") from exc
            except Exception:
                self._restore_items(original_items)
                raise
            finally:
                csv.field_size_limit(previous_limit)

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        query_tokens = tokens(query)
        if not query_tokens or limit <= 0:
            return []
        scores: dict[int, int] = {}
        for token in query_tokens:
            for item_id in self._postings.get(token, ()):
                scores[item_id] = scores.get(item_id, 0) + 1
        if not scores:
            return []
        ranked_ids = sorted(scores, key=lambda item_id: (-scores[item_id], item_id))[:limit]
        query_size = len(query_tokens)
        return [
            {
                "score": round(scores[item_id] / query_size, 3),
                "text": self._entries[item_id][0]["text"],
                "source": self._entries[item_id][0].get("source", "unknown"),
            }
            for item_id in ranked_ids
        ]
