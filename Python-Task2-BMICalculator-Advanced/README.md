# Advanced BMI Calculator GUI

Advanced implementation of **Task 2 – BMI Calculator** for the Oasis Infobyte
Python Programming track.

This version is a desktop Tkinter application rather than a command-line
program. It calculates BMI, gives colour-coded feedback, stores named-user
records in SQLite, and embeds a matplotlib line chart for BMI history.

## Advanced Features

- Tkinter GUI with labelled weight, height, and user-name fields.
- Calculate button with BMI rounded to two decimal places.
- Colour-coded category feedback:
  - Underweight – amber
  - Normal weight – green
  - Overweight – orange
  - Obese – red
- Multiple named users through a searchable editable combobox.
- Historical measurements stored locally in `bmi_records.db` using SQLite.
- Scrollable history table showing date, weight, height, BMI, and category.
- Embedded matplotlib line chart for the selected user's BMI trend.
- Validation for blank, non-numeric, zero, negative, infinite, and NaN values.
- Database read/write failures shown with GUI error dialogs instead of a
  traceback.
- No command-line interaction after launching the GUI.

## Install

Python 3.8 or later is recommended. Tkinter is included with most Python
installations. Install matplotlib in a virtual environment:

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Ubuntu/Debian, install Tkinter if needed:

```bash
sudo apt install python3-tk
```

## Run

```bash
python bmi_app.py
```

The application creates `bmi_records.db` in the project directory on first
launch. You can choose a different database path with `BMI_DATABASE`:

```bash
BMI_DATABASE=/path/to/bmi_records.db python bmi_app.py
```

On Windows PowerShell:

```powershell
$env:BMI_DATABASE = "C:\\path\\to\\bmi_records.db"
python bmi_app.py
```

## How to Use

1. Enter a user name, weight in kilograms, and height in metres.
2. Select **Calculate** to view the BMI and category.
3. Select **Save Record** to store the measurement for that named user.
4. Choose another user or type a new name to support multiple users.
5. Select **Load Selected User** to refresh the table and trend chart.
6. Repeat measurements over time to build a line chart.

## BMI Categories

| Category | Range |
| --- | ---: |
| Underweight | Less than 18.5 |
| Normal weight | 18.5 to less than 25.0 |
| Overweight | 25.0 to less than 30.0 |
| Obese | 30.0 or higher |

The formula is:

```text
BMI = weight in kilograms / (height in metres ** 2)
```

## Data and Privacy

Records are stored in a local SQLite database and are not uploaded by this
application. The database contains the user name, measurements, BMI category,
and timestamp. The database is not encrypted; protect the file if it contains
sensitive health information. This BMI result is an educational screening
calculation, not medical advice.

## Project Structure

```text
Python-Task2-BMICalculator-Advanced/
├── bmi_app.py       # Tkinter GUI, SQLite repository, and chart
├── requirements.txt # matplotlib dependency
└── README.md
```
