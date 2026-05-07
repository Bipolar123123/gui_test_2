import math

def add(a, b):
    """Сложение двух чисел."""
    return a + b

def divide(a, b):
    """Деление. При b=0 выбрасывает ValueError."""
    if b == 0:
        raise ValueError("Division by zero")
    return a / b

def parse_string_to_int(s):
    """Преобразует строку в целое число, игнорируя пробелы.
    Если строка не является числом, возвращает None."""
    s = s.strip()
    try:
        return int(s)
    except ValueError:
        return None

def calculate_circle_area(radius):
    """Площадь круга. radius > 0."""
    if radius <= 0:
        raise ValueError("Radius must be positive")
    return math.pi * radius ** 2