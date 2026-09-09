"""
BMI Calculator
Oasis Infobyte Internship - Python Programming Track
Task 2: Beginner Tier

This command-line program accepts a user's weight and height, calculates
Body Mass Index (BMI), and displays the corresponding BMI category.
"""

import math


def calculate_bmi(weight: float, height: float) -> float:
    """Calculate BMI and return the result rounded to two decimal places.

    Args:
        weight: Weight in kilograms. Must be greater than zero.
        height: Height in metres. Must be greater than zero.

    Returns:
        The calculated BMI rounded to two decimal places.

    Raises:
        ValueError: If either input is not a finite, positive number.
    """
    if not math.isfinite(weight) or not math.isfinite(height):
        raise ValueError("Weight and height must be finite numbers.")

    if weight <= 0 or height <= 0:
        raise ValueError("Weight and height must be greater than zero.")

    bmi = weight / (height ** 2)
    return round(bmi, 2)


def classify_bmi(bmi: float) -> str:
    """Return the health category for a BMI value.

    The boundaries use 18.5, 25.0, and 30.0 so that every valid BMI is
    assigned to exactly one category.

    Args:
        bmi: BMI value to classify.

    Returns:
        One of: Underweight, Normal weight, Overweight, or Obese.

    Raises:
        ValueError: If the BMI is not a finite, positive number.
    """
    if not math.isfinite(bmi) or bmi <= 0:
        raise ValueError("BMI must be a finite number greater than zero.")

    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Normal weight"
    if bmi < 30:
        return "Overweight"
    return "Obese"


def get_positive_float(prompt: str) -> float:
    """Ask for a positive, finite floating-point number until valid.

    Args:
        prompt: Text displayed before reading the user's input.

    Returns:
        A valid positive floating-point number.

    Note:
        Invalid input is handled inside this function, so the user can retry
        without restarting the program.
    """
    while True:
        try:
            value = float(input(prompt).strip())
        except ValueError:
            print("Error: Please enter a valid number, such as 70 or 1.75.")
            continue

        if not math.isfinite(value):
            print("Error: Please enter a finite number.")
            continue

        if value <= 0:
            print("Error: The value must be greater than zero. Please try again.")
            continue

        return value


def display_header() -> None:
    """Display the title of the application."""
    line = "=" * 40
    print("\n" + line)
    print("BMI CALCULATOR".center(40))
    print(line)


def display_results(bmi: float, category: str) -> None:
    """Display the calculated BMI and its category."""
    line = "=" * 40
    print("\n" + line)
    print("RESULTS".center(40))
    print(line)
    print(f"BMI: {bmi:.2f}")
    print(f"Category: {category}")
    print(line)


def main() -> None:
    """Run the BMI Calculator command-line application."""
    display_header()

    try:
        # Ask for both measurements. Invalid values are retried automatically.
        weight = get_positive_float("Enter your weight (kg): ")
        height = get_positive_float("Enter your height (m): ")

        # Calculate the BMI and map it to a category.
        bmi = calculate_bmi(weight, height)
        category = classify_bmi(bmi)

    except (EOFError, KeyboardInterrupt):
        print("\n\nInput cancelled. Goodbye!")
        return

    display_results(bmi, category)
    print("\nThank you for using the BMI Calculator!\n")


if __name__ == "__main__":
    main()
