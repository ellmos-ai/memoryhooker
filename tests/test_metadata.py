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

    assert len(anchors_en) == 18, f"Expected 18 anchors in README.md, got {len(anchors_en)}"
    assert len(anchors_de) == 18, f"Expected 18 anchors in README_de.md, got {len(anchors_de)}"
    assert len(headings_en) == 18, f"Expected 18 headings in README.md, got {len(headings_en)}"
    assert len(headings_de) == 18, f"Expected 18 headings in README_de.md, got {len(headings_de)}"

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
    assert "Last-checked: 2026-10-01" in content or "Last-checked: 2026-09-29" in content
    assert "NOTICE" in content
    assert "THIRD_PARTY_LICENSES.md" in content
    assert "THIRD_PARTY_LICENSES.txt" in content
    assert "MARKETING-LOG.txt" in content


def test_ci_workflows_extended_governance():
    workflows_dir = ROOT / ".github" / "workflows"

    # auto-assign.yml
    auto_assign = (workflows_dir / "auto-assign.yml").read_text(encoding="utf-8")
    assert "timeout-minutes: 5" in auto_assign
    assert "cancel-in-progress: true" in auto_assign
    assert "pull-requests: write" in auto_assign

    # label-sync.yml
    label_sync = (workflows_dir / "label-sync.yml").read_text(encoding="utf-8")
    assert "timeout-minutes: 5" in label_sync
    assert "cancel-in-progress: true" in label_sync
    assert "issues: write" in label_sync

    # labels.yml
    labels_file = (ROOT / ".github" / "labels.yml").read_text(encoding="utf-8")
    assert "name: bug" in labels_file
    assert "name: enhancement" in labels_file
    assert "name: documentation" in labels_file
    assert "name: stale" in labels_file

    # stale.yml
    stale = (workflows_dir / "stale.yml").read_text(encoding="utf-8")
    assert "timeout-minutes: 10" in stale
    assert "cancel-in-progress: true" in stale
    assert "30 1 * * *" in stale

    # welcome.yml
    welcome = (workflows_dir / "welcome.yml").read_text(encoding="utf-8")
    assert "timeout-minutes: 5" in welcome
    assert "cancel-in-progress: true" in welcome


def test_canonical_notice_file():
    notice_path = ROOT / "NOTICE"
    assert notice_path.exists()
    content = notice_path.read_text(encoding="utf-8")

    assert "MemoryHooker" in content
    assert "Lukas Geiger" in content
    assert "ellmos-ai" in content
    assert "open-bricks" in content
    assert "THIRD_PARTY_LICENSES.md" in content
    assert "THIRD_PARTY_LICENSES.txt" in content


def test_third_party_licenses_plain_text_companion():
    txt_path = ROOT / "THIRD_PARTY_LICENSES.txt"
    assert txt_path.exists()
    content = txt_path.read_text(encoding="utf-8")

    assert "hook-master" in content
    assert "Python Standard Library" in content
    assert "INV-LOCAL-01" in content
    assert "INV-SLA-10" in content
    assert "RunAsInvoker" in content
    assert "Audit Date: 2026-10-01" in content or "Audit Date: 2026-09-29" in content


def test_pep621_license_files_and_pytest_config():
    pyproject_path = ROOT / "pyproject.toml"
    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)

    project = data["project"]
    license_files = project["license-files"]
    assert "LICENSE" in license_files
    assert "NOTICE" in license_files
    assert "THIRD_PARTY_LICENSES.md" in license_files
    assert "THIRD_PARTY_LICENSES.txt" in license_files

    keywords = project["keywords"]
    assert len(keywords) == 20
    assert "memory" in keywords
    assert "local-first" in keywords
    assert "zero-egress" in keywords

    urls = project["urls"]
    assert "Notice" in urls
    assert "Level 1 SBOM" in urls
    assert "Third-Party Licenses (Text)" in urls
    assert "Plain-Text Licenses" in urls

    pytest_opts = data["tool"]["pytest"]["ini_options"]
    assert pytest_opts["minversion"] == "7.0"
    assert "--basetemp=.pytest_temp" in pytest_opts["addopts"]
    assert ".pytest_temp" in pytest_opts["norecursedirs"]


def test_gitignore_multihost_lock_defense():
    gitignore_path = ROOT / ".gitignore"
    assert gitignore_path.exists()
    content = gitignore_path.read_text(encoding="utf-8")

    assert "*-ASUS*" in content
    assert "*-IDEAPAD*" in content
    assert "*_WORKSTATION*" in content
    assert "*-WORKSTATION-LG.*" in content
    assert "LOCK.user.*" in content
    assert "LOCK.condition.*" in content
    assert ".pytest_temp/" in content
    assert "Desktop.ini" in content
    assert "desktop.ini" in content


def test_changelog_and_marketing_log_recency():
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [Unreleased]" in changelog
    assert "Pfad B" in changelog or "Pfad A" in changelog

    marketing_log = (ROOT / "MARKETING-LOG.txt").read_text(encoding="utf-8")
    assert "## 2026-10-01" in marketing_log or "## 2026-09-29" in marketing_log
    assert "Pfad B" in marketing_log or "Pfad A" in marketing_log


def test_bilingual_18_point_dual_anchors():
    readme_en = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (ROOT / "README_de.md").read_text(encoding="utf-8")

    for i in range(1, 19):
        sec_tag = f'<a id="sec-{i:02d}"></a>'
        assert sec_tag in readme_en, f"{sec_tag} missing in README.md"
        assert sec_tag in readme_de, f"{sec_tag} missing in README_de.md"


def test_ascii_four_view_architectural_topology_parity():
    readme_en = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (ROOT / "README_de.md").read_text(encoding="utf-8")

    expected_views_en = [
        "VIEW 1: CALLER RUNTIMES, LIFECYCLE HOOKS & AGENT CLIENTS",
        "VIEW 2: MEMORYHOOKER SOVEREIGN CORE ENGINE & PIPELINE ORCHESTRATOR",
        "VIEW 3: RUNTIME PERSISTENCE, SHARED MEMORY SCHEMAS & AUDIT LEDGER",
        "VIEW 4: AIR-GAP DEFENSE PERIMETER, RUNASINVOKER & ZERO-EGRESS GOVERNANCE",
    ]
    for view in expected_views_en:
        assert view in readme_en, f"English topology missing: {view}"

    expected_sichten_de = [
        "SICHT 1: AUFRUFER-LAUFZEITEN, LIFECYCLE-HOOKS & AGENTEN-CLIENTS",
        "SICHT 2: MEMORYHOOKER SOUVERÄNE CORE-ENGINE & PIPELINE-ORCHESTRIERUNG",
        "SICHT 3: LAUFZEIT-PERSISTENZ, GETEILTE SPEICHER-SCHEMATA & AUDIT-LEDGER",
        "SICHT 4: AIR-GAP DEFENSE PERIMETER, RUNASINVOKER & ZERO-EGRESS-GOVERNANCE",
    ]
    for sicht in expected_sichten_de:
        assert sicht in readme_de, f"German topology missing: {sicht}"


def test_statutory_disclaimer_521_bgb():
    readme_en = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_de = (ROOT / "README_de.md").read_text(encoding="utf-8")

    assert "521 BGB" in readme_en
    assert "521 BGB" in readme_de
