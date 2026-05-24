import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _dependency_names(values: list[str]) -> set[str]:
    names: set[str] = set()
    for value in values:
        normalized = value.split(";", 1)[0].strip()
        for separator in ("[", " ", "<", ">", "=", "!", "~", "@"):
            normalized = normalized.split(separator, 1)[0].strip()
        names.add(normalized.lower())
    return names


def test_project_metadata_is_real_package_identity() -> None:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = metadata["project"]

    assert project["name"] == "ancient-high-tech-compression"
    assert "Add your description here" not in project["description"]
    assert project["readme"] == "README.md"


def test_core_runtime_dependencies_stay_compression_scoped() -> None:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    runtime = _dependency_names(metadata["project"]["dependencies"])

    assert {"brotli", "nltk"} <= runtime
    assert len(runtime) <= 4

    unrelated_runtime = {
        "anthropic",
        "fastapi",
        "flask",
        "openai",
        "playwright",
        "psycopg2-binary",
        "selenium",
        "uvicorn",
        "webdriver-manager",
    }
    assert runtime.isdisjoint(unrelated_runtime)


def test_heavy_tooling_is_optional_not_core_runtime() -> None:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    optional = metadata["project"]["optional-dependencies"]

    assert "extraction" in optional
    assert {"flask", "selenium", "requests"} <= _dependency_names(optional["extraction"])
    assert {"openai", "anthropic"}.isdisjoint(_dependency_names(optional["extraction"]))
    assert {"openai"} <= _dependency_names(optional["providers"])
    assert {"pytest"} <= _dependency_names(optional["dev"])
