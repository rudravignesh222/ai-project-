import pytest
from app.security import clean_files, safe_path

def test_clean_files_accepts_normal_files():
    assert clean_files({"src/main.py": "print('hi')"})["src/main.py"] == "print('hi')"

@pytest.mark.parametrize("path", ["../evil.txt", "/etc/passwd", ".env", "src/.env.local", "node_modules/a.js", "src/../../x"])
def test_rejects_unsafe_paths(path):
    with pytest.raises(ValueError):
        safe_path(path)
