from pathlib import Path

import yaml

from backend.store import app_version

ROOT = Path(__file__).resolve().parents[2]


def test_compose_files_use_the_image_of_this_version():
    """docker-compose.yml and the HTTPS example build `lineage:<version>`: bump them with the version."""
    for f in (ROOT / "docker-compose.yml", ROOT / "docs" / "examples" / "docker-compose.https.yml"):
        image = yaml.safe_load(f.read_text())["services"]["lineage"]["image"]
        assert image == f"lineage:{app_version()}", f"{f.relative_to(ROOT)}: image is {image}, lineage is {app_version()}"
