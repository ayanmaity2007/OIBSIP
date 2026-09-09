# BMI Calculator

A beginner-friendly command-line Body Mass Index (BMI) calculator created for
**Oasis Infobyte Internship – Python Programming Track, Task 2**.

The program asks for a person's weight in kilograms and height in metres,
calculates BMI using the standard formula, and displays the matching category.

## Tech Stack

- Python 3.6 or later
- Python standard library only (`math`)
- Command-line interface (no GUI)
- No external packages required

## BMI Formula

```text
BMI = weight (kg) / height (m)²
```

The displayed BMI is rounded to two decimal places.

## BMI Categories

| Category | BMI range |
| --- | ---: |
| Underweight | Less than 18.5 |
| Normal weight | 18.5 to less than 25.0 |
| Overweight | 25.0 to less than 30.0 |
| Obese | 30.0 or higher |

These boundaries correspond to the requested two-decimal ranges of
under 18.5, 18.5–24.9, 25–29.9, and 30 or above.

## Features

- Accepts weight in kilograms and height in metres.
- Calculates BMI with the formula `weight / (height ** 2)`.
- Displays BMI rounded to two decimal places.
- Classifies BMI as Underweight, Normal weight, Overweight, or Obese.
- Rejects non-numeric input with a helpful message.
- Rejects zero, negative, infinite, and NaN values.
- Allows the user to retry after invalid input.
- Uses functions, docstrings, type hints, and clear comments/documentation.

## Project Structure

```text
Python-Task2-BMICalculator/
├── main.py          # Main Python application
├── README.md        # Project documentation
└── screenshot.png   # Screenshot of a sample run
```

## Requirements

Install Python 3.6 or later. No additional libraries are needed.

To check your Python version:

```bash
python --version
```

On some systems, use:

```bash
python3 --version
```

## How to Run

1. Open a terminal or command prompt.
2. Move into the project directory:

   ```bash
   cd OIBsIP/Python-Task2-BMICalculator
   ```

3. Run the program:

   **Windows:**

   ```bash
   py main.py
   ```

   **macOS/Linux:**

   ```bash
   python3 main.py
   ```

   You can also use `python main.py` if `python` is mapped to Python 3.

4. Enter the weight in kilograms when prompted.
5. Enter the height in metres when prompted.
6. Read the BMI value and category displayed by the program.

## Sample Input and Output

```text
========================================
           BMI CALCULATOR
========================================
Enter your weight (kg): 70
Enter your height (m): 1.75

========================================
                RESULTS
========================================
BMI: 22.86
Category: Normal weight
========================================

Thank you for using the BMI Calculator!
```

## Invalid Input Example

```text
Enter your weight (kg): abc
Error: Please enter a valid number, such as 70 or 1.75.
Enter your weight (kg): 0
Error: The value must be greater than zero. Please try again.
Enter your weight (kg): 70
Enter your height (m): -5
Error: The value must be greater than zero. Please try again.
Enter your height (m): 1.75
```

The program keeps asking for the value until a valid positive number is
provided.

## Validation Test Cases

| Weight (kg) | Height (m) | Expected BMI | Expected category |
| ---: | ---: | ---: | --- |
| 70 | 1.75 | 22.86 | Normal weight |
| 50 | 1.60 | 19.53 | Normal weight |
| 85 | 1.70 | 29.41 | Overweight |
| 100 | 1.65 | 36.73 | Obese |
| 45 | 1.70 | 15.57 | Underweight |

## Taking a Screenshot

Run the program with one of the sample inputs, then capture the terminal window
using your operating system's screenshot tool. Save the image in this folder as
`screenshot.png` before submitting the project.

## Author

**Your Name**  
Oasis Infobyte Internship – Python Programming Track  
Task 2: BMI Calculator

Replace **Your Name** with your name before publishing the repository.
