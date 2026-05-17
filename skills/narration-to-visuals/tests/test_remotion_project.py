import json
from pathlib import Path

ROOT = Path(__file__).parents[1] / "remotion"


def test_remotion_project_files_exist():
    for rel in ["package.json", "tsconfig.json", "src/index.ts",
                "src/Root.tsx", "src/Main.tsx"]:
        assert (ROOT / rel).exists(), rel


def test_package_json_has_remotion_and_render_script():
    pkg = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    assert "remotion" in deps
    assert "@remotion/cli" in deps
    assert "render" in pkg.get("scripts", {})


def test_main_consumes_props_contract():
    main = (ROOT / "src" / "Main.tsx").read_text(encoding="utf-8")
    for key in ["blocks", "pip", "audioSrc", "imageSrc", "slideLines",
                "diagramSpec", "fromFrame", "durationFrames"]:
        assert key in main, key
    root = (ROOT / "src" / "Root.tsx").read_text(encoding="utf-8")
    assert 'id="Main"' in root or "'Main'" in root or '"Main"' in root
