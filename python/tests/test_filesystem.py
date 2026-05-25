from pathlib import Path

from redtonomous.tools.filesystem import (
    append_file,
    create_directory,
    delete_file,
    list_directory,
    move_file,
    read_file,
    search_files,
    write_file,
)


def test_write_read_roundtrip(tmp_path: Path):
    p = tmp_path / "a.txt"
    assert write_file(str(p), "hello").startswith("OK")
    assert read_file(str(p)) == "hello"


def test_read_missing(tmp_path: Path):
    assert read_file(str(tmp_path / "nope")).startswith("ERROR")


def test_append(tmp_path: Path):
    p = tmp_path / "b.txt"
    write_file(str(p), "one\n")
    append_file(str(p), "two\n")
    assert read_file(str(p)) == "one\ntwo\n"


def test_list_directory(tmp_path: Path):
    write_file(str(tmp_path / "x.py"), "")
    create_directory(str(tmp_path / "sub"))
    listed = list_directory(str(tmp_path))
    assert "x.py" in listed
    assert "sub/" in listed


def test_move_and_delete(tmp_path: Path):
    src = tmp_path / "src.txt"
    dst = tmp_path / "dst.txt"
    write_file(str(src), "x")
    assert move_file(str(src), str(dst)).startswith("OK")
    assert dst.exists() and not src.exists()
    assert delete_file(str(dst)).startswith("OK")
    assert not dst.exists()


def test_search_files_match(tmp_path: Path):
    write_file(str(tmp_path / "a.py"), "def needle():\n    pass\n")
    write_file(str(tmp_path / "b.py"), "no match\n")
    out = search_files("needle", str(tmp_path), "*.py")
    assert "needle" in out and "a.py" in out


def test_search_files_invalid_regex(tmp_path: Path):
    # Previously this was silently re-escaped — now it surfaces the error.
    out = search_files("(", str(tmp_path))
    assert out.startswith("ERROR:")
