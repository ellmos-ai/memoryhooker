import json
import re
from pathlib import Path

import pytest

tomllib = pytest.importorskip("tomllib", reason="stdlib erst ab Python 3.11")

import memoryhooker

ROOT = Path(__file__).resolve().parent.parent


def test_version_parity():
    pyproject_path = ROOT / "pyproject.toml"
    module_v2_path = ROOT / "ellmos-module.v2.json"
    changelog_path = ROOT / "CHANGELOG.md"
    security_path = ROOT / "SECURITY.md"
    llms_path = ROOT / "llms.txt"

    with pyproject_path.open("rb") as f:
        pyproject_data = tomllib.load(f)
    pyproject_version = pyproject_data["project"]["version"]

    with module_v2_path.open("r", encoding="utf-8") as f:
        module_v2_data = json.load(f)
    module_v2_version = module_v2_data["version"]

    assert memoryhooker.__version__ == "0.3.3"
    assert pyproject_version == "0.3.3"
    assert module_v2_version == "0.3.3"

    changelog_text = changelog_path.read_text(encoding="utf-8")
    assert "## [0.3.3] - 2026-09-14" in changelog_text

    security_text = security_path.read_text(encoding="utf-8")
    assert "`0.3.x`" in security_text

    llms_text = llms_path.read_text(encoding="utf-8")
    assert "Version: 0.3.3" in llms_text


def test_module_v2_contract():
    module_v2_path = ROOT / "ellmos-module.v2.json"
    with module_v2_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["schema"] == "ellmos.module.v2"
    assert data["id"] == "memoryhooker"
    assert "provides" in data
    assert "surfaces" in data
    assert "boundaries" in data


def test_package_exports():
    expected_exports = ["Hit", "MemoryBackend", "Config", "load_config", "__version__"]
    for export_name in expected_exports:
        assert hasattr(memoryhooker, export_name)
        assert export_name in memoryhooker.__all__


def test_pep621_extended_urls():
    pyproject_path = ROOT / "pyproject.toml"
    with pyproject_path.open("rb") as f:
        pyproject_data = tomllib.load(f)
    urls = pyproject_data["project"]["urls"]

    expected_keys = [
        "Homepage",
        "Repository",
        "Documentation",
        "Issues",
        "Changelog",
        "Security",
        "Parent Organization",
        "Umbrella Ecosystem",
        "Third-Party Licenses",
        "Marketing Log",
        "LLM Ready",
    ]
    for key in expected_keys:
        assert key in urls, f"Missing URL entry in pyproject.toml: {key}"
        assert urls[key].startswith("https://github.com/")


def _extract_nav_anchors(content: str) -> list[str]:
    nav_match = re.search(
        r"## (?:Quick Navigation|Schnellnavigation)\s*\n\n(.*?)\n\n---",
        content,
        re.DOTALL,
    )
    assert nav_match is not None, "Quick Navigation section not found"
    return re.findall(r"\[.*?\]\((#[^\)]+)\)", nav_match.group(1))


def _gh_slug(heading: str) -> str:
    return "#" + re.sub(r"[^\w\s-]", "", heading.lower()).replace(" ", "-")


def test_bilingual_navigation_anchor_parity():
    readme_en = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (ROOT / "README_de.md").read_text(encoding="utf-8")

    anchors_en = _extract_nav_anchors(readme_en)
    anchors_de = _extract_nav_anchors(readme_de)

    headings_en = [h.lstrip("#").strip() for h in re.findall(r"^##\s+(?!Quick|Schnell)(.*)$", readme_en, re.MULTILINE)]
    headings_de = [h.lstrip("#").strip() for h in re.findall(r"^##\s+(?!Quick|Schnell)(.*)$", readme_de, re.MULTILINE)]

    assert len(anchors_en) == 16, f"Expected 16 anchors in README.md, got {len(anchors_en)}"
    assert len(anchors_de) == 16, f"Expected 16 anchors in README_de.md, got {len(anchors_de)}"
    assert len(headings_en) == 16, f"Expected 16 headings in README.md, got {len(headings_en)}"
    assert len(headings_de) == 16, f"Expected 16 headings in README_de.md, got {len(headings_de)}"

    for anchor, heading in zip(anchors_en, headings_en, strict=True):
        expected_slug = _gh_slug(heading)
        assert anchor == expected_slug, f"README.md anchor mismatch: {anchor} != {expected_slug} for heading {heading}"

    for anchor, heading in zip(anchors_de, headings_de, strict=True):
        expected_slug = _gh_slug(heading)
        assert anchor == expected_slug, f"README_de.md anchor mismatch: {anchor} != {expected_slug} for heading {heading}"


def test_target_personas_sections():
    readme_en = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (ROOT / "README_de.md").read_text(encoding="utf-8")

    for doc in (readme_en, readme_de):
        assert "Autonomous AI Coding Agents" in doc or "Autonome Coding-Agenten" in doc
        assert "Local-First" in doc
        assert "Multi-Agent Swarm" in doc or "Multi-Agent" in doc
        assert "Compliance" in doc

    assert "High-Intent Discovery Keywords" in readme_en
    assert "High-Intent Suchbegriffe" in readme_de


def test_comparative_matrix_sections():
    readme_en = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (ROOT / "README_de.md").read_text(encoding="utf-8")

    for doc in (readme_en, readme_de):
        assert "Cloud Vector DB RAG" in doc
        assert "Chat History Buffer" in doc
        assert "MemGPT" in doc
        assert "100% Zero-Egress" in doc
        assert "RunAsInvoker" in doc


def test_governance_invariants_sections():
    readme_en = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (ROOT / "README_de.md").read_text(encoding="utf-8")
    marketing_log = (ROOT / "MARKETING-LOG.txt").read_text(encoding="utf-8")

    expected_invariants = [
        "INV-LOCAL-01",
        "INV-READONLY-02",
        "INV-UNPRIV-03",
        "INV-REDACT-04",
        "INV-BOUND-05",
        "INV-GATE-06",
        "INV-SPAM-07",
        "INV-FAILOPEN-08",
        "INV-LLM-09",
        "INV-SLA-10",
    ]

    for inv in expected_invariants:
        assert inv in readme_en, f"{inv} missing in README.md"
        assert inv in readme_de, f"{inv} missing in README_de.md"
        assert inv in marketing_log, f"{inv} missing in MARKETING-LOG.txt"


def test_third_party_licenses_file():
    tpl_path = ROOT / "THIRD_PARTY_LICENSES.md"
    assert tpl_path.exists()
    content = tpl_path.read_text(encoding="utf-8")

    assert "PSFL-2.0" in content
    assert "MIT" in content
    assert "Apache-2.0" in content
    assert "RunAsInvoker" in content
    assert "Zero-Egress" in content


def test_marketing_log_audit():
    mlog_path = ROOT / "MARKETING-LOG.txt"
    assert mlog_path.exists()
    content = mlog_path.read_text(encoding="utf-8")

    assert "v0.3.3" in content
    assert "2026-09-14" in content
    assert "Ziel-Personas" in content or "Target Personas" in content


def test_ci_timeout_minutes_guardrail():
    ci_path = ROOT / ".github" / "workflows" / "ci.yml"
    assert ci_path.exists()
    content = ci_path.read_text(encoding="utf-8")

    assert "timeout-minutes: 15" in content


def test_llms_txt_content():
    llms_path = ROOT / "llms.txt"
    assert llms_path.exists()
    content = llms_path.read_text(encoding="utf-8")

    assert "Version: 0.3.3" in content
    assert "Last-checked: 2026-09-14" in content
    assert "THIRD_PARTY_LICENSES.md" in content
    assert "MARKETING-LOG.txt" in content
