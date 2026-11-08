"""Windows-friendly desktop chat interface using only the Python standard library."""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path

from .config import Settings
from .engine import RullerAI


class UltronWindow:
    def __init__(self, root: tk.Tk, settings: Settings | None = None) -> None:
        self.root = root
        self.settings = settings or Settings()
        self.assistant = RullerAI(self.settings)
        self.results: queue.Queue[tuple[str, str]] = queue.Queue()
        self.busy = False

        root.title("ULTRON AI Assistant")
        root.geometry("900x680")
        root.minsize(640, 480)
        self._build_ui()
        self._restore_recent_chat()
        self._update_model_status()
        root.after(100, self._poll_results)
        root.protocol("WM_DELETE_WINDOW", root.destroy)

    def _build_ui(self) -> None:
        style = ttk.Style(self.root)
        if "vista" in style.theme_names():
            style.theme_use("vista")

        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)

        config = ttk.LabelFrame(outer, text="Model connection", padding=8)
        config.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        config.columnconfigure(5, weight=1)

        ttk.Label(config, text="Provider").grid(row=0, column=0, sticky="w", padx=(0, 5))
        current_provider = (self.settings.provider or "offline").casefold()
        if current_provider in {"openai-compatible", "openai_compatible", "openai-compatible-http"}:
            current_provider = "openai"
        elif current_provider in {"local-ollama", "local_ollama"}:
            current_provider = "ollama"
        self.provider_var = tk.StringVar(value=current_provider)
        self.provider_box = ttk.Combobox(
            config, textvariable=self.provider_var, values=("offline", "ollama", "openai"),
            state="readonly", width=12,
        )
        self.provider_box.grid(row=0, column=1, sticky="w", padx=(0, 12))

        ttk.Label(config, text="Model").grid(row=0, column=2, sticky="w", padx=(0, 5))
        self.model_var = tk.StringVar(value=self.settings.model or "")
        ttk.Entry(config, textvariable=self.model_var, width=19).grid(row=0, column=3, sticky="ew", padx=(0, 12))

        ttk.Label(config, text="API base").grid(row=0, column=4, sticky="w", padx=(0, 5))
        self.api_base_var = tk.StringVar(value=self.settings.api_base or "")
        ttk.Entry(config, textvariable=self.api_base_var).grid(row=0, column=5, sticky="ew", padx=(0, 12))

        ttk.Label(config, text="API key").grid(row=1, column=0, sticky="w", pady=(8, 0), padx=(0, 5))
        self.api_key_var = tk.StringVar(value=self.settings.api_key or "")
        ttk.Entry(config, textvariable=self.api_key_var, show="•", width=28).grid(
            row=1, column=1, columnspan=2, sticky="ew", pady=(8, 0), padx=(0, 12)
        )
        self.apply_button = ttk.Button(config, text="Apply model settings", command=self.apply_settings)
        self.apply_button.grid(row=1, column=3, sticky="w", pady=(8, 0))
        self.status_var = tk.StringVar()
        ttk.Label(config, textvariable=self.status_var).grid(row=1, column=4, columnspan=2, sticky="e", pady=(8, 0))

        chat = ttk.Frame(outer)
        chat.grid(row=1, column=0, sticky="nsew")
        chat.columnconfigure(0, weight=1)
        chat.rowconfigure(0, weight=1)
        self.transcript = tk.Text(chat, wrap="word", state="disabled", padx=12, pady=12, font=("Segoe UI", 10))
        scrollbar = ttk.Scrollbar(chat, orient="vertical", command=self.transcript.yview)
        self.transcript.configure(yscrollcommand=scrollbar.set)
        self.transcript.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.transcript.tag_configure("user", foreground="#155eef", spacing1=8, spacing3=8)
        self.transcript.tag_configure("assistant", foreground="#222222", spacing1=8, spacing3=8)
        self.transcript.tag_configure("system", foreground="#666666", spacing1=8, spacing3=8)

        composer = ttk.Frame(outer)
        composer.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        composer.columnconfigure(0, weight=1)
        self.input_var = tk.StringVar()
        self.input_entry = ttk.Entry(composer, textvariable=self.input_var, font=("Segoe UI", 10))
        self.input_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.input_entry.bind("<Return>", self._on_return)
        self.send_button = ttk.Button(composer, text="Send", command=self.send_message)
        self.send_button.grid(row=0, column=1)
        ttk.Button(composer, text="Clear chat", command=self.clear_chat).grid(row=0, column=2, padx=(8, 0))
        self.input_entry.focus_set()

    def _restore_recent_chat(self) -> None:
        for item in self.assistant.memory.recent(40):
            role = item.get("role")
            if role in {"user", "assistant"}:
                self._append_message("You" if role == "user" else "ULTRON", str(item.get("content", "")), role)

    def _append_message(self, speaker: str, text: str, role: str) -> None:
        self.transcript.configure(state="normal")
        self.transcript.insert("end", f"{speaker}\n{text}\n\n", role)
        self.transcript.configure(state="disabled")
        self.transcript.see("end")

    def _on_return(self, _event: tk.Event) -> str:
        self.send_message()
        return "break"

    def send_message(self) -> None:
        if self.busy:
            return
        text = self.input_var.get().strip()
        if not text:
            return
        self.input_var.set("")
        self._append_message("You", text, "user")
        self.busy = True
        self.send_button.configure(state="disabled")
        self.status_var.set("ULTRON is thinking…")

        def run_chat() -> None:
            try:
                response = self.assistant.chat(text)
            except Exception as exc:  # Present runtime/provider failures in the UI rather than crashing the window.
                response = f"Request failed: {exc}"
            self.results.put((text, response))

        threading.Thread(target=run_chat, daemon=True).start()

    def _poll_results(self) -> None:
        try:
            _prompt, response = self.results.get_nowait()
        except queue.Empty:
            pass
        else:
            self._append_message("ULTRON", response, "assistant")
            self.busy = False
            self.send_button.configure(state="normal")
            self._update_model_status()
            self.input_entry.focus_set()
        self.root.after(100, self._poll_results)

    def _update_model_status(self) -> None:
        provider = self.assistant.provider
        self.status_var.set(f"Backend: {provider.name if provider else 'offline'}")

    def apply_settings(self) -> None:
        provider = self.provider_var.get().strip()
        model = self.model_var.get().strip() or None
        api_base = self.api_base_var.get().strip() or None
        api_key = self.api_key_var.get().strip() or None
        if provider == "openai" and not api_key and not (self.settings.api_key or None):
            messagebox.showwarning(
                "API key needed",
                "Enter an API key here or set OPENAI_API_KEY in Windows environment variables.",
                parent=self.root,
            )
            return
        self.settings = Settings(
            data_dir=self.settings.data_dir,
            max_input_chars=self.settings.max_input_chars,
            max_memory_items=self.settings.max_memory_items,
            max_knowledge_items=self.settings.max_knowledge_items,
            provider=provider,
            model=model,
            api_base=api_base,
            api_key=api_key,
        )
        self.assistant = RullerAI(self.settings)
        self._update_model_status()
        messagebox.showinfo("ULTRON", "Model settings applied.", parent=self.root)

    def clear_chat(self) -> None:
        if self.busy:
            return
        if not messagebox.askyesno(
            "Clear conversation memory?",
            "This clears saved conversation memory. Your local knowledge base is kept.",
            parent=self.root,
        ):
            return
        response = self.assistant.chat("/clear")
        self.transcript.configure(state="normal")
        self.transcript.delete("1.0", "end")
        self.transcript.configure(state="disabled")
        self._append_message("ULTRON", response, "assistant")


def launch(settings: Settings | None = None) -> None:
    root = tk.Tk()
    UltronWindow(root, settings)
    root.mainloop()


def main() -> int:
    launch()
    return 0
