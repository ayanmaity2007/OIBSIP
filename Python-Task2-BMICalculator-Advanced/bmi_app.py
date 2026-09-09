"""Advanced BMI Calculator GUI.

Features include multi-user SQLite persistence, colour-coded feedback, and a
matplotlib BMI trend chart embedded in a Tkinter window.
"""

import datetime as dt
import math
import os
import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk
from typing import List, Optional, Tuple

try:
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
except ImportError:  # pragma: no cover - displayed in the GUI if not installed
    FigureCanvasTkAgg = None
    Figure = None


class DatabaseError(Exception):
    """Raised when a BMI database operation fails."""


class BMIRepository:
    """SQLite data-access layer for users and BMI records."""

    def __init__(self, database_path: str = "bmi_records.db") -> None:
        self.database_path = database_path
        try:
            self.connection = sqlite3.connect(self.database_path)
            self.connection.row_factory = sqlite3.Row
            self._create_tables()
        except sqlite3.Error as error:
            raise DatabaseError("Could not open the BMI database: {}".format(error))

    def _create_tables(self) -> None:
        try:
            with self.connection:
                self.connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                self.connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS bmi_records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        weight_kg REAL NOT NULL,
                        height_m REAL NOT NULL,
                        bmi REAL NOT NULL,
                        category TEXT NOT NULL,
                        recorded_at TEXT NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                    """
                )
        except sqlite3.Error as error:
            raise DatabaseError("Could not create database tables: {}".format(error))

    def _get_or_create_user(self, name: str) -> int:
        try:
            row = self.connection.execute("SELECT id FROM users WHERE name = ?", (name,)).fetchone()
            if row:
                return int(row["id"])
            cursor = self.connection.execute(
                "INSERT INTO users (name, created_at) VALUES (?, ?)",
                (name, dt.datetime.now().isoformat(timespec="seconds")),
            )
            self.connection.commit()
            return int(cursor.lastrowid)
        except sqlite3.Error as error:
            self.connection.rollback()
            raise DatabaseError("Could not save the user: {}".format(error))

    def add_record(self, name: str, weight: float, height: float, bmi: float, category: str) -> None:
        """Create the user if necessary and save one BMI measurement."""
        user_id = self._get_or_create_user(name)
        try:
            self.connection.execute(
                """
                INSERT INTO bmi_records
                    (user_id, weight_kg, height_m, bmi, category, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, weight, height, bmi, category, dt.datetime.now().isoformat(timespec="seconds")),
            )
            self.connection.commit()
        except sqlite3.Error as error:
            self.connection.rollback()
            raise DatabaseError("Could not save the BMI record: {}".format(error))

    def list_users(self) -> List[str]:
        """Return all saved user names in alphabetical order."""
        try:
            rows = self.connection.execute("SELECT name FROM users ORDER BY name COLLATE NOCASE").fetchall()
            return [str(row["name"]) for row in rows]
        except sqlite3.Error as error:
            raise DatabaseError("Could not read users: {}".format(error))

    def history(self, name: str) -> List[sqlite3.Row]:
        """Return a user's records in chronological order."""
        try:
            rows = self.connection.execute(
                """
                SELECT r.recorded_at, r.weight_kg, r.height_m, r.bmi, r.category
                FROM bmi_records AS r
                JOIN users AS u ON u.id = r.user_id
                WHERE u.name = ?
                ORDER BY r.recorded_at ASC, r.id ASC
                """,
                (name,),
            ).fetchall()
            return list(rows)
        except sqlite3.Error as error:
            raise DatabaseError("Could not read BMI history: {}".format(error))

    def close(self) -> None:
        """Close the SQLite connection safely."""
        try:
            self.connection.close()
        except sqlite3.Error:
            pass


def calculate_bmi(weight: float, height: float) -> float:
    """Return BMI rounded to two decimals after validating measurements."""
    if not math.isfinite(weight) or not math.isfinite(height):
        raise ValueError("Weight and height must be finite numbers.")
    if weight <= 0 or height <= 0:
        raise ValueError("Weight and height must be greater than zero.")
    result = weight / (height ** 2)
    if not math.isfinite(result) or result <= 0:
        raise ValueError("Those measurements cannot produce a usable BMI.")
    return round(result, 2)


def classify_bmi(bmi: float) -> Tuple[str, str]:
    """Return a BMI category and a colour used by the result label."""
    if bmi < 18.5:
        return "Underweight", "#d97706"
    if bmi < 25:
        return "Normal weight", "#15803d"
    if bmi < 30:
        return "Overweight", "#b45309"
    return "Obese", "#b91c1c"


class BMIApp:
    """Tkinter application for calculating and tracking BMI."""

    def __init__(self, root: tk.Tk, repository: BMIRepository) -> None:
        self.root = root
        self.repository = repository
        self.root.title("Advanced BMI Calculator")
        self.root.geometry("1050x760")
        self.root.minsize(900, 650)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.name_var = tk.StringVar()
        self.weight_var = tk.StringVar()
        self.height_var = tk.StringVar()
        self.result_var = tk.StringVar(value="Enter your measurements and click Calculate.")
        self.category_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Records are stored locally in SQLite.")
        self.last_result: Optional[Tuple[float, float, float, str]] = None

        self._build_widgets()
        self.refresh_users()

    def _build_widgets(self) -> None:
        """Create the labelled inputs, buttons, history table, and chart."""
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Title.TLabel", font=("Arial", 20, "bold"))
        style.configure("Heading.TLabel", font=("Arial", 12, "bold"))
        style.configure("Action.TButton", font=("Arial", 10, "bold"))

        container = ttk.Frame(self.root, padding=18)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=0)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(2, weight=1)

        ttk.Label(container, text="BMI Calculator", style="Title.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 4)
        )
        ttk.Label(
            container,
            text="Calculate, save, and visualise BMI records for multiple users.",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 14))

        input_frame = ttk.LabelFrame(container, text="New measurement", padding=14)
        input_frame.grid(row=2, column=0, sticky="nsew", padx=(0, 14))
        input_frame.columnconfigure(1, weight=1)

        ttk.Label(input_frame, text="User name:").grid(row=0, column=0, sticky="w", pady=6)
        self.user_combo = ttk.Combobox(input_frame, textvariable=self.name_var, width=24)
        self.user_combo.grid(row=0, column=1, sticky="ew", pady=6)
        self.user_combo.bind("<<ComboboxSelected>>", lambda _event: self.load_history())

        ttk.Label(input_frame, text="Weight (kg):").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(input_frame, textvariable=self.weight_var, width=25).grid(
            row=1, column=1, sticky="ew", pady=6
        )

        ttk.Label(input_frame, text="Height (m):").grid(row=2, column=0, sticky="w", pady=6)
        ttk.Entry(input_frame, textvariable=self.height_var, width=25).grid(
            row=2, column=1, sticky="ew", pady=6
        )

        ttk.Button(input_frame, text="Calculate", style="Action.TButton", command=self.calculate).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(14, 6)
        )
        ttk.Button(input_frame, text="Save Record", command=self.save_record).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=6
        )
        ttk.Button(input_frame, text="Load Selected User", command=self.load_history).grid(
            row=5, column=0, columnspan=2, sticky="ew", pady=6
        )

        result_frame = tk.LabelFrame(
            input_frame,
            text="Result",
            font=("Arial", 11, "bold"),
            padx=10,
            pady=10,
            bg="#f8fafc",
        )
        result_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(18, 0))
        result_frame.columnconfigure(0, weight=1)
        tk.Label(
            result_frame,
            textvariable=self.result_var,
            font=("Arial", 16, "bold"),
            bg="#f8fafc",
            wraplength=270,
        ).grid(row=0, column=0, sticky="ew")
        self.category_label = tk.Label(
            result_frame,
            textvariable=self.category_var,
            font=("Arial", 13, "bold"),
            fg="#334155",
            bg="#f8fafc",
        )
        self.category_label.grid(row=1, column=0, pady=(8, 0))

        right = ttk.Frame(container)
        right.grid(row=2, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        right.rowconfigure(3, weight=2)

        ttk.Label(right, text="Saved history", style="Heading.TLabel").grid(row=0, column=0, sticky="w")
        table_frame = ttk.Frame(right)
        table_frame.grid(row=1, column=0, sticky="nsew", pady=(6, 16))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        columns = ("date", "weight", "height", "bmi", "category")
        self.history_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=8)
        headings = {
            "date": "Recorded",
            "weight": "Weight (kg)",
            "height": "Height (m)",
            "bmi": "BMI",
            "category": "Category",
        }
        widths = {"date": 150, "weight": 90, "height": 90, "bmi": 70, "category": 130}
        for column in columns:
            self.history_tree.heading(column, text=headings[column])
            self.history_tree.column(column, width=widths[column], anchor="center")
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        self.history_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        ttk.Label(right, text="BMI trend", style="Heading.TLabel").grid(row=2, column=0, sticky="w")
        self.chart_frame = ttk.Frame(right, relief="groove", borderwidth=1)
        self.chart_frame.grid(row=3, column=0, sticky="nsew", pady=(6, 0))
        self.chart_message = ttk.Label(
            self.chart_frame,
            text="Select a user with saved records to view a trend chart.",
            anchor="center",
        )
        self.chart_message.pack(fill="both", expand=True, padx=20, pady=20)

        ttk.Label(container, textvariable=self.status_var, foreground="#475569").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(12, 0)
        )

    def _read_measurements(self) -> Tuple[float, float]:
        """Parse and validate the two GUI input fields."""
        try:
            weight = float(self.weight_var.get().strip())
            height = float(self.height_var.get().strip())
        except ValueError:
            raise ValueError("Enter numeric values for both weight and height.")
        if not math.isfinite(weight) or not math.isfinite(height):
            raise ValueError("Weight and height must be finite numbers.")
        if weight <= 0 or height <= 0:
            raise ValueError("Weight and height must be greater than zero.")
        return weight, height

    def calculate(self) -> bool:
        """Calculate a BMI and update the colour-coded result panel."""
        try:
            weight, height = self._read_measurements()
            bmi = calculate_bmi(weight, height)
            category, colour = classify_bmi(bmi)
        except ValueError as error:
            self.result_var.set("Invalid input")
            self.category_var.set("")
            self.category_label.configure(fg="#b91c1c")
            self.status_var.set(str(error))
            return False

        self.last_result = (weight, height, bmi, category)
        self.result_var.set("BMI: {:.2f}".format(bmi))
        self.category_var.set("Category: {}".format(category))
        self.category_label.configure(fg=colour)
        self.status_var.set("Calculation complete. Click Save Record to store it for this user.")
        return True

    def save_record(self) -> None:
        """Save the current calculation and refresh history/chart safely."""
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Missing user", "Enter a name before saving a BMI record.")
            return
        # Recalculate on every save so edited fields can never save stale data.
        if not self.calculate():
            return
        assert self.last_result is not None
        weight, height, bmi, category = self.last_result
        try:
            self.repository.add_record(name, weight, height, bmi, category)
            self.refresh_users()
            self.load_history()
            self.status_var.set("Saved BMI {:.2f} for {}.".format(bmi, name))
        except DatabaseError as error:
            messagebox.showerror("Database error", str(error))
            self.status_var.set("The record could not be saved.")

    def refresh_users(self) -> None:
        """Refresh the multi-user combobox without losing the current name."""
        current = self.name_var.get()
        try:
            self.user_combo["values"] = self.repository.list_users()
        except DatabaseError as error:
            messagebox.showerror("Database error", str(error))
            self.status_var.set("Could not read saved users.")
            return
        self.name_var.set(current)

    def load_history(self) -> None:
        """Load the selected user's table and trend chart."""
        name = self.name_var.get().strip()
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        if not name:
            self.status_var.set("Enter or select a user name to view history.")
            self._draw_chart([] , "")
            return
        try:
            records = self.repository.history(name)
        except DatabaseError as error:
            messagebox.showerror("Database error", str(error))
            self.status_var.set("Could not read BMI history.")
            return
        for row in records:
            self.history_tree.insert(
                "",
                "end",
                values=(
                    row["recorded_at"].replace("T", " "),
                    "{:.1f}".format(row["weight_kg"]),
                    "{:.2f}".format(row["height_m"]),
                    "{:.2f}".format(row["bmi"]),
                    row["category"],
                ),
            )
        self._draw_chart(records, name)
        self.status_var.set("Loaded {} record(s) for {}.".format(len(records), name))

    def _draw_chart(self, records: List[sqlite3.Row], name: str) -> None:
        """Render the selected user's BMI trend using an embedded matplotlib figure."""
        for child in self.chart_frame.winfo_children():
            child.destroy()
        if Figure is None or FigureCanvasTkAgg is None:
            ttk.Label(
                self.chart_frame,
                text="Install matplotlib to display the trend chart.",
                anchor="center",
            ).pack(fill="both", expand=True, padx=20, pady=20)
            return
        if not records:
            ttk.Label(
                self.chart_frame,
                text="No saved records for this user yet.",
                anchor="center",
            ).pack(fill="both", expand=True, padx=20, pady=20)
            return

        figure = Figure(figsize=(6.2, 3.1), dpi=100)
        axes = figure.add_subplot(111)
        x_values = list(range(1, len(records) + 1))
        y_values = [float(row["bmi"]) for row in records]
        axes.plot(x_values, y_values, marker="o", color="#2563eb", linewidth=2)
        axes.set_title("BMI trend for {}".format(name))
        axes.set_xlabel("Measurement number")
        axes.set_ylabel("BMI")
        axes.grid(True, alpha=0.3)
        figure.tight_layout()
        canvas = FigureCanvasTkAgg(figure, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def close(self) -> None:
        """Close the database and the GUI."""
        self.repository.close()
        self.root.destroy()


def main() -> None:
    """Start the advanced BMI GUI; there is no command-line interaction."""
    database_path = os.getenv("BMI_DATABASE", "bmi_records.db")
    try:
        repository = BMIRepository(database_path)
    except DatabaseError as error:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Database error", str(error))
        root.destroy()
        return
    root = tk.Tk()
    BMIApp(root, repository)
    root.mainloop()


if __name__ == "__main__":
    main()
