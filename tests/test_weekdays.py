from app.weekdays import validate_weekday_int, weekday_int_to_name, weekday_name_to_int


def test_weekday_int_to_name_ok():
    assert weekday_int_to_name(1) == "Segunda-feira"
    assert weekday_int_to_name(7) == "Domingo"


def test_weekday_int_to_name_invalid():
    try:
        weekday_int_to_name(0)
        raise AssertionError("Era esperado ValueError")
    except ValueError:
        pass


def test_weekday_name_to_int_ok():
    assert weekday_name_to_int("segunda") == 1
    assert weekday_name_to_int("Segunda-feira") == 1
    assert weekday_name_to_int("terça") == 2
    assert weekday_name_to_int("TERCA") == 2
    assert weekday_name_to_int("sábado") == 6
    assert weekday_name_to_int("domingo") == 7


def test_validate_weekday_int():
    assert validate_weekday_int(1) == 1
    assert validate_weekday_int(7) == 7

    for invalid in (0, 8):
        try:
            validate_weekday_int(invalid)
            raise AssertionError("Era esperado ValueError")
        except ValueError:
            pass
