import pytest
from my_project.utils import add, divide, parse_string_to_int, calculate_circle_area
from unittest.mock import patch
import math

# Параметризованные тесты для add
@pytest.mark.parametrize("a,b,expected", [
    (1, 2, 3),
    (-1, 1, 0),
    (0, 0, 0),
    (2.5, 3.5, 6.0)
])
def test_add(a, b, expected):
    assert add(a, b) == expected

# Параметризованные тесты для divide
@pytest.mark.parametrize("a,b,expected", [
    (10, 2, 5),
    (9, 3, 3),
    (7, 2, 3.5)
])
def test_divide_ok(a, b, expected):
    assert divide(a, b) == expected

def test_divide_by_zero():
    with pytest.raises(ValueError, match="Division by zero"):
        divide(5, 0)

# Параметризованные тесты для parse_string_to_int
@pytest.mark.parametrize("input_str,expected", [
    ("42", 42),
    ("  123  ", 123),
    ("abc", None),
    ("12.34", None),
    ("-5", -5),
    ("0", 0)
])
def test_parse_string_to_int(input_str, expected):
    assert parse_string_to_int(input_str) == expected

# Тест с фикстурой
def test_calculate_circle_area(sample_numbers):
    radius = sample_numbers[0]  # 10
    expected = math.pi * 100
    assert calculate_circle_area(radius) == expected

# Тест с моком (замена math.pi на фиксированное значение)
def test_calculate_circle_area_with_mock():
    with patch('my_project.utils.math.pi', 3.14):
        assert calculate_circle_area(2) == 3.14 * 4

def test_calculate_circle_area_invalid(invalid_radius):
    with pytest.raises(ValueError, match="Radius must be positive"):
        calculate_circle_area(invalid_radius)