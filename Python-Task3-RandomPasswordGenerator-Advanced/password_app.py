"""Advanced cryptographically secure password generator GUI."""

import secrets
import string
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Dict, Iterable, List, Sequence, Tuple

try:
    import pyperclip
except ImportError:  # Clipboard fallback is provided by Tkinter.
    pyperclip = None


CHARACTER_SETS: Dict[str, str] = {
    "uppercase": string.ascii_uppercase,
    "lowercase": string.ascii_lowercase,
    "numbers": string.digits,
    "symbols": "!@#$%^&*()-_=+[]{};:,.?/|~",
}
DISPLAY_NAMES = {
    "uppercase": "Uppercase letters",
    "lowercase": "Lowercase letters",
    "numbers": "Numbers",
    "symbols": "Symbols",
}
AMBIGUOUS_CHARACTERS = set("0O1lI|")


def _available_characters(character_type: str, exclude_ambiguous: bool) -> str:
    """Return a selected character set after applying the exclusion rule."""
    if character_type not in CHARACTER_SETS:
        raise ValueError("Unknown character type: {}".format(character_type))
    characters = CHARACTER_SETS[character_type]
    if exclude_ambiguous:
        characters = "".join(char for char in characters if char not in AMBIGUOUS_CHARACTERS)
    if not characters:
        raise ValueError("The selected character type has no characters left after exclusions.")
    return characters


def generate_password(length: int, selected_types: Sequence[str], exclude_ambiguous: bool = False) -> str:
    """Generate a secure password satisfying every selected character rule.

    At least one character is deliberately chosen from each selected category,
    then the remaining positions are filled from the combined pool and the
    result is shuffled using ``secrets.SystemRandom``.
    """
    if length < 8:
        raise ValueError("Password length must be at least 8 characters.")
    unique_types = list(dict.fromkeys(selected_types))
    if len(unique_types) < 2:
        raise ValueError("Select at least two character types.")
    if length < len(unique_types):
        raise ValueError("Password length is too short for all selected character types.")

    pools = [_available_characters(kind, exclude_ambiguous) for kind in unique_types]
    combined_pool = "".join(pools)
    password_characters = [secrets.choice(pool) for pool in pools]
    password_characters.extend(secrets.choice(combined_pool) for _ in range(length - len(pools)))
    secrets.SystemRandom().shuffle(password_characters)
    return "".join(password_characters)


def password_strength(password: str, selected_count: int) -> Tuple[str, int, str]:
    """Return a strength label, progress value, and explanation."""
    length = len(password)
    score = 0
    score += 25 if length >= 8 else 10
    score += 20 if length >= 12 else 0
    score += 20 if length >= 16 else 0
    score += 15 if selected_count >= 2 else 0
    score += 15 if selected_count >= 3 else 0
    score += 5 if selected_count >= 4 else 0
    if score >= 80:
        return "Strong", min(score, 100), "Good length and character diversity."
    if score >= 50:
        return "Medium", min(score, 100), "Increase length or add more character types."
    return "Weak", min(score, 100), "Use at least 12 characters and multiple character types."


class PasswordApp:
    """Tkinter interface for secure password generation and session history."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Advanced Secure Password Generator")
        self.root.geometry("780x560")
        self.root.minsize(700, 500)

        self.length_var = tk.IntVar(value=16)
        self.exclude_var = tk.BooleanVar(value=False)
        self.type_vars = {kind: tk.BooleanVar(value=(kind in ("uppercase", "lowercase", "numbers"))) for kind in CHARACTER_SETS}
        self.password_var = tk.StringVar()
        self.strength_var = tk.StringVar(value="Strength: —")
        self.status_var = tk.StringVar(value="Choose at least two character types.")
        self.current_password = ""
        self.history: List[str] = []

        self._build_widgets()

    def _build_widgets(self) -> None:
        """Build controls, strength feedback, and in-memory history."""
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Title.TLabel", font=("Arial", 20, "bold"))
        style.configure("Heading.TLabel", font=("Arial", 12, "bold"))
        style.configure("Generate.TButton", font=("Arial", 11, "bold"))
        style.configure("Strength.Horizontal.TProgressbar", troughcolor="#e2e8f0", background="#16a34a")

        outer = ttk.Frame(self.root, padding=20)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(2, weight=1)

        ttk.Label(outer, text="Secure Password Generator", style="Title.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w"
        )
        ttk.Label(
            outer,
            text="Uses Python's secrets module. Generated passwords are never saved to disk.",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 18))

        controls = ttk.LabelFrame(outer, text="Password rules", padding=14)
        controls.grid(row=2, column=0, sticky="nsw", padx=(0, 18))

        ttk.Label(controls, text="Length (8–128):").grid(row=0, column=0, sticky="w", pady=5)
        self.length_spinbox = tk.Spinbox(
            controls,
            from_=8,
            to=128,
            textvariable=self.length_var,
            width=8,
            validate="key",
        )
        self.length_spinbox.grid(row=0, column=1, sticky="e", pady=5)

        ttk.Label(controls, text="Character types:").grid(row=1, column=0, columnspan=2, sticky="w", pady=(14, 4))
        for row, kind in enumerate(CHARACTER_SETS, start=2):
            ttk.Checkbutton(
                controls,
                text=DISPLAY_NAMES[kind],
                variable=self.type_vars[kind],
            ).grid(row=row, column=0, columnspan=2, sticky="w", pady=3)

        ttk.Checkbutton(
            controls,
            text="Exclude ambiguous characters",
            variable=self.exclude_var,
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(14, 8))
        ttk.Label(controls, text="Excludes: 0, O, 1, l, I, |").grid(row=7, column=0, columnspan=2, sticky="w")
        ttk.Button(
            controls,
            text="Generate Password",
            style="Generate.TButton",
            command=self.generate,
        ).grid(row=8, column=0, columnspan=2, sticky="ew", pady=(18, 5))

        output = ttk.Frame(outer)
        output.grid(row=2, column=1, sticky="nsew")
        output.columnconfigure(0, weight=1)
        output.rowconfigure(5, weight=1)
        ttk.Label(output, text="Generated password", style="Heading.TLabel").grid(row=0, column=0, sticky="w")
        password_entry = ttk.Entry(output, textvariable=self.password_var, font=("Courier New", 14), state="readonly")
        password_entry.grid(row=1, column=0, sticky="ew", pady=(8, 6))
        ttk.Button(output, text="Copy to Clipboard", command=self.copy_to_clipboard).grid(
            row=2, column=0, sticky="w", pady=(0, 12)
        )

        strength_frame = ttk.LabelFrame(output, text="Password strength", padding=10)
        strength_frame.grid(row=3, column=0, sticky="ew", pady=(0, 14))
        strength_frame.columnconfigure(0, weight=1)
        ttk.Label(strength_frame, textvariable=self.strength_var, font=("Arial", 11, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        self.strength_bar = ttk.Progressbar(
            strength_frame,
            style="Strength.Horizontal.TProgressbar",
            orient="horizontal",
            mode="determinate",
            maximum=100,
        )
        self.strength_bar.grid(row=1, column=0, sticky="ew", pady=6)
        ttk.Label(strength_frame, text="Strength uses length and selected character diversity.").grid(
            row=2, column=0, sticky="w"
        )

        ttk.Label(output, text="Last 5 passwords in this session", style="Heading.TLabel").grid(
            row=4, column=0, sticky="w"
        )
        history_frame = ttk.Frame(output)
        history_frame.grid(row=5, column=0, sticky="nsew", pady=(6, 0))
        history_frame.columnconfigure(0, weight=1)
        history_frame.rowconfigure(0, weight=1)
        self.history_list = tk.Listbox(history_frame, font=("Courier New", 11), height=8, activestyle="none")
        self.history_list.grid(row=0, column=0, sticky="nsew")
        history_scroll = ttk.Scrollbar(history_frame, orient="vertical", command=self.history_list.yview)
        history_scroll.grid(row=0, column=1, sticky="ns")
        self.history_list.configure(yscrollcommand=history_scroll.set)

        ttk.Label(outer, textvariable=self.status_var, foreground="#475569").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(14, 0)
        )

    def _selected_types(self) -> List[str]:
        """Return the currently checked character categories."""
        return [kind for kind, variable in self.type_vars.items() if variable.get()]

    def generate(self) -> None:
        """Generate, display, copy, and add a password to session history."""
        try:
            length = int(self.length_var.get())
            selected = self._selected_types()
            password = generate_password(length, selected, self.exclude_var.get())
        except (TypeError, ValueError) as error:
            messagebox.showerror("Invalid password settings", str(error))
            self.status_var.set(str(error))
            return

        self.current_password = password
        self.password_var.set(password)
        label, score, explanation = password_strength(password, len(selected))
        self.strength_var.set("Strength: {} ({}%)".format(label, score))
        self.strength_bar["value"] = score
        self._set_strength_colour(label)

        self.history.insert(0, password)
        self.history = self.history[:5]
        self.history_list.delete(0, tk.END)
        for item in self.history:
            self.history_list.insert(tk.END, item)
        self.copy_to_clipboard(auto=True)
        self.status_var.set("{} {} Password copied automatically.".format(label, explanation))

    def _set_strength_colour(self, label: str) -> None:
        """Change the progress bar colour according to strength."""
        colour = {"Weak": "#dc2626", "Medium": "#d97706", "Strong": "#16a34a"}[label]
        style = ttk.Style()
        style.configure("Strength.Horizontal.TProgressbar", background=colour)

    def copy_to_clipboard(self, auto: bool = False) -> None:
        """Copy the current password using pyperclip, with a Tk fallback."""
        if not self.current_password:
            self.status_var.set("Generate a password before copying.")
            return
        try:
            if pyperclip is not None:
                pyperclip.copy(self.current_password)
            else:
                self.root.clipboard_clear()
                self.root.clipboard_append(self.current_password)
                self.root.update()
            if not auto:
                self.status_var.set("Password copied to the clipboard.")
        except Exception as error:
            self.status_var.set("Clipboard is unavailable: {}".format(error))


def main() -> None:
    """Start the desktop application."""
    root = tk.Tk()
    PasswordApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
