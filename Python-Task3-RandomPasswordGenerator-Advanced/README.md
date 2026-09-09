# Advanced Secure Random Password Generator

Advanced implementation of **Task 3 – Random Password Generator** for the
Oasis Infobyte Python Programming track.

The application is a Tkinter GUI that uses Python's `secrets` module rather
than `random`, enforces the selected character rules, copies each generated
password to the clipboard, and keeps a five-item in-memory session history.

## Features

### Beginner features included

- Minimum password length of 8 characters.
- Uppercase, lowercase, number, and symbol checkboxes.
- At least two character categories required.
- Invalid settings are rejected with a clear GUI error.
- Generate another password without restarting.

### Advanced features included

- GUI length spinbox from 8 to 128 characters.
- Cryptographically secure generation with `secrets.choice` and
  `secrets.SystemRandom().shuffle`.
- Password strength label and visual progress bar: Weak, Medium, or Strong.
- At least one character from every selected type is guaranteed.
- Automatic clipboard copy after generation and a manual Copy button using
  `pyperclip`.
- Checkbox to exclude ambiguous characters `0`, `O`, `1`, `l`, `I`, and `|`.
- Last five generated passwords shown only for the current session; no history
  is written to a file or database.

## Install

Python 3.8 or later is recommended. Tkinter is included with most Python
installations. Install the clipboard dependency:

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
```

If Tkinter is missing on Ubuntu/Debian:

```bash
sudo apt install python3-tk
```

`pyperclip` may require an operating-system clipboard utility. The app falls
back to Tkinter's clipboard methods when the package is unavailable.

## Run

```bash
python password_app.py
```

## How to Use

1. Choose a length of at least 8.
2. Select at least two character types.
3. Optionally enable **Exclude ambiguous characters**.
4. Click **Generate Password**.
5. The password is displayed, copied automatically, scored, and added to the
   five-item session history.
6. Use **Copy to Clipboard** whenever you need to copy the current password.

## Strength Rules

The indicator uses a transparent heuristic based on length and character
diversity. A longer password with three or four selected categories is rated
Strong. The indicator is guidance only; never reuse passwords and use a
password manager for important accounts.

## Security Notes

- `secrets` is appropriate for security-sensitive random values; `random` is
  intentionally not used.
- Passwords remain in GUI memory and the visible session history until the app
  closes. They are not persisted by this project.
- Clipboard contents can be read by other applications. Clear the clipboard if
  your operating system or threat model requires it.
- Do not take screenshots containing real passwords.

## Project Structure

```text
Python-Task3-RandomPasswordGenerator-Advanced/
├── password_app.py  # GUI and secure generator
├── requirements.txt  # pyperclip dependency
└── README.md
```
