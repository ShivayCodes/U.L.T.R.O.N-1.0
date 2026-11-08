"""Windows-friendly desktop chat UI built with Tkinter."""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from .config import Settings
from .engine import RullerAI


class UltronWindow:
    """Desktop chat window with a permanently visible composer and model sidebar."""

    LIGHT = {
        "window": "#f4f6fa", "surface": "#ffffff", "text": "#172033",
        "muted": "#697386", "border": "#e2e7ef", "user_bubble": "#dceafe",
        "assistant_bubble": "#ffffff", "accent": "#3267d6", "input": "#ffffff",
    }
    DARK = {
        "window": "#111827", "surface": "#1b2433", "text": "#e8edf5",
        "muted": "#9aa8bb", "border": "#2c394b", "user_bubble": "#24436c",
        "assistant_bubble": "#202c3b", "accent": "#77a7ff", "input": "#202c3b",
    }

    def __init__(self, root: tk.Tk, settings: Settings | None = None) -> None:
        self.root = root
        self.settings = settings or Settings()
        self.assistant = RullerAI(self.settings)
        self.results: queue.Queue[tuple[str, str]] = queue.Queue()
        self.busy = False
        self._closing = False
        self._worker: threading.Thread | None = None
        self.dark_mode = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Ready")

        root.title("ULTRON AI Assistant")
        root.geometry("1120x760")
        root.minsize(760, 520)
        self._build_ui()
        self._apply_theme()
        self._restore_recent_chat()
        self._update_model_status()
        root.after(100, self._poll_results)
        root.protocol("WM_DELETE_WINDOW", self._request_close)

    def _build_ui(self) -> None:
        self.style = ttk.Style(self.root)
        if "vista" in self.style.theme_names():
            self.style.theme_use("vista")

        self.main = tk.Frame(self.root, padx=14, pady=14)
        self.main.pack(fill="both", expand=True)
        self.main.columnconfigure(1, weight=1)
        self.main.rowconfigure(0, weight=1)

        self.sidebar = tk.Frame(self.main, width=270, padx=14, pady=14)
        self.sidebar.grid(row=0, column=0, sticky="ns", padx=(0, 12))
        self.sidebar.grid_propagate(False)
        self._tk_label(self.sidebar, "ULTRON", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        self._tk_label(self.sidebar, "AI assistant").pack(anchor="w", pady=(0, 18))
        self._section_label(self.sidebar, "MODEL SETTINGS")

        self.provider_var = tk.StringVar(value=self._normalize_provider(self.settings.provider))
        self._label(self.sidebar, "Provider").pack(anchor="w", pady=(10, 4))
        self.provider_box = ttk.Combobox(
            self.sidebar, textvariable=self.provider_var,
            values=("offline", "ollama", "openai"), state="readonly",
        )
        self.provider_box.pack(fill="x")
        self._label(self.sidebar, "Model name").pack(anchor="w", pady=(12, 4))
        self.model_var = tk.StringVar(value=self.settings.model or "")
        ttk.Entry(self.sidebar, textvariable=self.model_var).pack(fill="x")
        self._label(self.sidebar, "API base URL").pack(anchor="w", pady=(12, 4))
        self.api_base_var = tk.StringVar(value=self.settings.api_base or "")
        ttk.Entry(self.sidebar, textvariable=self.api_base_var).pack(fill="x")
        self._label(self.sidebar, "API key (session only)").pack(anchor="w", pady=(12, 4))
        self.api_key_var = tk.StringVar(value=self.settings.api_key or "")
        ttk.Entry(self.sidebar, textvariable=self.api_key_var, show="*").pack(fill="x")
        ttk.Button(self.sidebar, text="Apply settings", command=self.apply_settings).pack(fill="x", pady=(12, 4))
        self.backend_label = self._tk_label(self.sidebar, "Backend: offline", wraplength=230, justify="left")
        self.backend_label.pack(fill="x", pady=(4, 16))

        self._section_label(self.sidebar, "PREFERENCES")
        ttk.Checkbutton(self.sidebar, text="Dark mode", variable=self.dark_mode, command=self._apply_theme).pack(anchor="w", pady=(10, 6))
        ttk.Button(self.sidebar, text="Clear conversation", command=self.clear_chat).pack(fill="x", pady=(8, 4))
        self._section_label(self.sidebar, "LOCAL DATA")
        self.data_label = self._tk_label(self.sidebar, f"Stored locally in:\n{self.settings.data_dir}", justify="left", wraplength=230)
        self.data_label.pack(fill="x", pady=(10, 0))

        self.chat_area = tk.Frame(self.main)
        self.chat_area.grid(row=0, column=1, sticky="nsew")
        self.chat_area.columnconfigure(0, weight=1)
        # Pack makes the composer a fixed bottom bar; only the transcript expands.
        self.chat_header = tk.Frame(self.chat_area, padx=16, pady=12)
        self.chat_header.pack(side="top", fill="x", pady=(0, 8))
        self.chat_title = self._tk_label(self.chat_header, "Chat", font=("Segoe UI", 15, "bold"))
        self.chat_title.pack(anchor="w")
        self.chat_subtitle = self._tk_label(
            self.chat_header,
            "Type below and press Enter or click Send. Hosted models receive your prompts.",
        )
        self.chat_subtitle.pack(anchor="w", pady=(3, 0))

        self.composer = tk.Frame(self.chat_area, padx=12, pady=10)
        self.composer.pack(side="bottom", fill="x", pady=(8, 0))
        self.composer.columnconfigure(0, weight=1)
        self.input_entry = ttk.Entry(self.composer, font=("Segoe UI", 11))
        self.input_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8), ipady=8)
        self.input_entry.insert(0, "Type your message here…")
        self._input_placeholder = True
        self.input_entry.bind("<FocusIn>", self._clear_placeholder)
        self.input_entry.bind("<FocusOut>", self._restore_placeholder)
        self.input_entry.bind("<Return>", self._on_return)
        self.send_button = ttk.Button(self.composer, text="Send", command=self.send_message)
        self.send_button.grid(row=0, column=1, padx=(0, 10), ipady=4)
        self.spinner = ttk.Progressbar(self.composer, mode="indeterminate", length=82)
        self.spinner.grid(row=0, column=2, padx=(0, 8))
        self.spinner.grid_remove()
        self.status_label = self._tk_label(self.composer, "Ready", anchor="e", width=16)
        self.status_label.grid(row=0, column=3, sticky="e")

        self.chat_frame = tk.Frame(self.chat_area)
        self.chat_frame.pack(side="top", fill="both", expand=True)
        self.chat_frame.columnconfigure(0, weight=1)
        self.chat_frame.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self.chat_frame, highlightthickness=0, borderwidth=0)
        self.scrollbar = ttk.Scrollbar(self.chat_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.messages = tk.Frame(self.canvas, padx=12, pady=12)
        self.messages_window = self.canvas.create_window((0, 0), window=self.messages, anchor="nw")
        self.messages.bind("<Configure>", self._update_scroll_region)
        self.canvas.bind("<Configure>", self._resize_message_area)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.input_entry.focus_set()

    def _clear_placeholder(self, _event: tk.Event) -> None:
        if self._input_placeholder:
            self.input_entry.delete(0, "end")
            self._input_placeholder = False

    def _restore_placeholder(self, _event: tk.Event) -> None:
        if not self.input_entry.get().strip() and not self._input_placeholder:
            self.input_entry.insert(0, "Type your message here…")
            self._input_placeholder = True

    @staticmethod
    def _normalize_provider(provider: str | None) -> str:
        name = (provider or "offline").casefold()
        if name in {"openai-compatible", "openai_compatible", "openai-compatible-http"}:
            return "openai"
        if name in {"local-ollama", "local_ollama"}:
            return "ollama"
        return name if name in {"offline", "ollama", "openai"} else "offline"

    def _tk_label(self, parent: tk.Widget, text: str, **kwargs: object) -> tk.Label:
        return tk.Label(parent, text=text, **kwargs)

    def _section_label(self, parent: tk.Widget, text: str) -> tk.Label:
        label = self._tk_label(parent, text, font=("Segoe UI", 8, "bold"), anchor="w")
        label.pack(fill="x", pady=(8, 0))
        return label

    def _label(self, parent: tk.Widget, text: str) -> tk.Label:
        return self._tk_label(parent, text, anchor="w")

    def _apply_theme(self) -> None:
        colors = self.DARK if self.dark_mode.get() else self.LIGHT
        self.colors = colors
        self.root.configure(bg=colors["window"])
        for frame in (self.main, self.chat_area, self.chat_frame, self.messages):
            frame.configure(bg=colors["window"])
        for frame in (self.sidebar, self.chat_header, self.composer):
            frame.configure(bg=colors["surface"])
        for widget in self.sidebar.winfo_children():
            if isinstance(widget, tk.Label):
                is_section = str(widget.cget("text")).isupper() and len(str(widget.cget("text"))) < 24
                widget.configure(bg=colors["surface"], fg=colors["muted"] if is_section else colors["text"])
        self.chat_title.configure(bg=colors["surface"], fg=colors["text"])
        self.chat_subtitle.configure(bg=colors["surface"], fg=colors["muted"])
        self.backend_label.configure(bg=colors["surface"], fg=colors["muted"])
        self.data_label.configure(bg=colors["surface"], fg=colors["muted"])
        self.status_label.configure(bg=colors["surface"], fg=colors["muted"])
        self.canvas.configure(bg=colors["window"])
        self.style.configure("TFrame", background=colors["window"])
        self.style.configure("TLabel", background=colors["surface"], foreground=colors["text"])
        self.style.configure("TCheckbutton", background=colors["surface"], foreground=colors["text"])
        self.style.map("TCheckbutton", background=[("active", colors["surface"])])
        self.style.configure("TEntry", fieldbackground=colors["input"], foreground=colors["text"])
        self.style.configure("TCombobox", fieldbackground=colors["input"], foreground=colors["text"])
        self.style.configure("Horizontal.TProgressbar", background=colors["accent"])
        self._recolor_messages()

    def _recolor_messages(self) -> None:
        if not hasattr(self, "messages"):
            return
        for row in self.messages.winfo_children():
            role = getattr(row, "message_role", "assistant")
            bubble_color = self.colors["user_bubble"] if role == "user" else self.colors["assistant_bubble"]
            for bubble in row.winfo_children():
                if isinstance(bubble, tk.Frame):
                    bubble.configure(bg=bubble_color, highlightbackground=self.colors["border"])
                    for child in bubble.winfo_children():
                        child.configure(bg=bubble_color, fg=self.colors["muted"] if getattr(child, "is_timestamp", False) else self.colors["text"])

    def _restore_recent_chat(self) -> None:
        for item in self.assistant.memory.recent(40):
            role = item.get("role")
            if role in {"user", "assistant"}:
                self._append_message("You" if role == "user" else "ULTRON", str(item.get("content", "")), role, item.get("timestamp"))

    def _append_message(self, speaker: str, text: str, role: str, timestamp: str | None = None) -> None:
        role = role if role in {"user", "assistant"} else "assistant"
        colors = self.colors
        row = tk.Frame(self.messages, bg=colors["window"])
        row.message_role = role
        row.pack(fill="x", pady=5)
        bubble_color = colors["user_bubble"] if role == "user" else colors["assistant_bubble"]
        bubble = tk.Frame(row, bg=bubble_color, padx=12, pady=8, highlightthickness=1, highlightbackground=colors["border"])
        bubble.pack(side="right" if role == "user" else "left", padx=(60, 4) if role == "user" else (4, 60))
        stamp = self._format_timestamp(timestamp)
        heading = tk.Label(bubble, text=f"{speaker}  ·  {stamp}", bg=bubble_color, fg=colors["muted"], font=("Segoe UI", 8, "bold"), anchor="w")
        heading.is_timestamp = True
        heading.pack(anchor="w", pady=(0, 4))
        tk.Label(bubble, text=text, bg=bubble_color, fg=colors["text"], font=("Segoe UI", 10), justify="left", anchor="w", wraplength=620).pack(anchor="w")
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)

    @staticmethod
    def _format_timestamp(value: str | None = None) -> str:
        try:
            if value:
                return datetime.fromisoformat(value).astimezone().strftime("%b %d, %I:%M %p")
        except (ValueError, TypeError):
            pass
        return datetime.now().astimezone().strftime("%b %d, %I:%M %p")

    def _update_scroll_region(self, _event: tk.Event | None = None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_message_area(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self.messages_window, width=event.width)

    def _on_mousewheel(self, event: tk.Event) -> None:
        if not self._closing and self.canvas.winfo_exists():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_return(self, _event: tk.Event) -> str:
        self.send_message()
        return "break"

    def send_message(self) -> None:
        if self.busy or self._closing:
            return
        text = "" if self._input_placeholder else self.input_entry.get().strip()
        if not text:
            return
        self.input_entry.delete(0, "end")
        self._input_placeholder = False
        self._append_message("You", text, "user")
        self.busy = True
        self.send_button.configure(state="disabled")
        self.status_var.set("Thinking…")
        self.status_label.configure(textvariable=self.status_var)
        self.spinner.grid()
        self.spinner.start(12)

        def run_chat() -> None:
            try:
                response = self.assistant.chat(text)
            except Exception:
                # Avoid showing arbitrary exception text that may contain submitted content or secrets.
                response = "Request failed unexpectedly. Check the provider settings and local application logs."
            self.results.put((text, response))

        self._worker = threading.Thread(target=run_chat, name="ultron-chat-worker", daemon=False)
        self._worker.start()

    def _poll_results(self) -> None:
        if self._closing:
            if self._worker is not None and self._worker.is_alive():
                self.root.after(100, self._poll_results)
            else:
                self.root.destroy()
            return
        try:
            _prompt, response = self.results.get_nowait()
        except queue.Empty:
            pass
        else:
            self.spinner.stop()
            self.spinner.grid_remove()
            self._append_message("ULTRON", response, "assistant")
            self.busy = False
            self._worker = None
            self.send_button.configure(state="normal")
            self._update_model_status()
            self.input_entry.focus_set()
        self.root.after(100, self._poll_results)

    def _update_model_status(self) -> None:
        provider = self.assistant.provider
        name = provider.name if provider else "offline"
        self.backend_label.configure(text=f"Backend: {name}")
        self.status_var.set(f"Ready · {name}")

    def apply_settings(self) -> None:
        if self.busy or self._closing:
            return
        provider = self.provider_var.get().strip()
        model = self.model_var.get().strip() or None
        api_base = self.api_base_var.get().strip() or None
        api_key = self.api_key_var.get().strip() or None
        if provider == "openai" and not api_key:
            messagebox.showwarning("API key needed", "Enter an API key here or set OPENAI_API_KEY in Windows environment variables.", parent=self.root)
            return
        try:
            settings = Settings(
                data_dir=self.settings.data_dir, max_input_chars=self.settings.max_input_chars,
                max_memory_items=self.settings.max_memory_items, max_knowledge_items=self.settings.max_knowledge_items,
                provider=provider, model=model, api_base=api_base, api_key=api_key,
            )
            assistant = RullerAI(settings)
        except Exception as exc:
            # Provider validation errors intentionally contain no credential values.
            messagebox.showerror("Settings could not be applied", str(exc), parent=self.root)
            return
        self.settings, self.assistant = settings, assistant
        self._update_model_status()
        messagebox.showinfo("ULTRON", "Model settings applied.", parent=self.root)

    def clear_chat(self) -> None:
        if self.busy or self._closing:
            return
        if not messagebox.askyesno("Clear conversation memory?", "This clears saved conversation memory. Your local knowledge base is kept.", parent=self.root):
            return
        self.assistant.memory.clear()
        for child in self.messages.winfo_children():
            child.destroy()
        self._append_message("ULTRON", "Conversation memory cleared. Your local knowledge was kept.", "assistant")

    def _request_close(self) -> None:
        if self._closing:
            return
        self._closing = True
        self.input_entry.configure(state="disabled")
        self.send_button.configure(state="disabled")
        self.status_var.set("Finishing current request before closing…")
        self.spinner.stop()
        self.spinner.grid_remove()
        self.root.after(50, self._poll_results)


def launch(settings: Settings | None = None) -> None:
    root = tk.Tk()
    UltronWindow(root, settings)
    root.mainloop()


def main() -> int:
    launch()
    return 0
