import math

from sandbox_common import int_arg, num, parse


def test_num_rejects_non_finite_and_clamps():
    assert num("nan", 7) == 7 and num("inf", 7) == 7 and num("-inf", 7) == 7 and num("1e999", 7) == 7
    assert num("abc", 7) == 7 and num(None, 7) == 7 and num("", 7) == 7
    assert num("5", 0, 0, 3) == 3 and num("-5", 0, 0, 3) == 0 and num("2.5", 0, 0, 3) == 2.5
    assert math.isfinite(num("1e308", 0.0, 0.0, 5.0))


def test_int_arg_always_in_range():
    for raw in ("nan", "inf", "-1", "0", "99999999999999999999", "1e12", "x", None, "٣"):
        n = int_arg(raw, 5, 1, 100)
        assert isinstance(n, int) and 1 <= n <= 100


def test_parse_supports_both_flag_styles():
    assert parse(["a", "--k", "v", "--j=w", "--flag"]) == (["a"], {"k": "v", "j": "w", "flag": True})
