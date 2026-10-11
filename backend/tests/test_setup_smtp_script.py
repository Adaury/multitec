import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "setup_smtp.py"
spec = importlib.util.spec_from_file_location("setup_smtp", SCRIPT)
setup_smtp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup_smtp)


def test_set_env_values_replaces_and_appends_keeping_the_rest_and_newlines():
    original = "A=1\r\nSMTP_HOST=\r\nSMTP_PASSWORD=\r\n# comentario\r\nB=2\r\n"

    result = setup_smtp.set_env_values(original, {"SMTP_HOST": "smtp.gmail.com", "SMTP_PASSWORD": "abc", "NUEVA": "x"})

    assert "SMTP_HOST=smtp.gmail.com" in result
    assert "SMTP_PASSWORD=abc" in result
    assert result.count("SMTP_HOST") == 1
    assert "A=1" in result and "B=2" in result and "# comentario" in result
    assert result.endswith("NUEVA=x\r\n")
    assert "\n" not in result.replace("\r\n", "")  # sin saltos mezclados


def test_set_env_values_handles_special_characters_in_values():
    result = setup_smtp.set_env_values("SMTP_PASSWORD=\n", {"SMTP_PASSWORD": r"ab\1$x"})

    # Una barra invertida seguida de dígito es un backreference en re.sub: el valor debe quedar literal.
    assert result == r"SMTP_PASSWORD=ab\1$x" + "\n"


def test_read_env_ignores_comments_and_blank_lines():
    values = setup_smtp.read_env("# hola\n\nA=1\nB = dos \n")

    assert values == {"A": "1", "B": "dos"}
