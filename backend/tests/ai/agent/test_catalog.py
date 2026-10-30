from pathlib import Path

import pytest

from app.modules.ai.agent.skills.catalog import SkillCatalog, parse_skill


def test_frontmatter_parses_bom_and_deduplicates_tools():
    skill = parse_skill("\ufeff---\r\nname: inspect\r\ndescription: Inspect\r\nallowed-tools: [part_detail, part_detail]\r\n---\r\nbody")
    assert skill.name == "inspect"
    assert skill.allowed_tools == ("part_detail",)
    assert skill.content == "body"


@pytest.mark.parametrize("content", ["no frontmatter", "---\nname: ../escape\ndescription: X\n---\nx", "---\nname: good\ndescription: X\nallowed-tools: [read_file(/etc)]\n---\nx", "---\nname: good\ndescription: X\nrequired-secrets: [PASSWORD]\n---\nx"])
def test_invalid_skill_is_rejected(content):
    with pytest.raises(ValueError):
        parse_skill(content)


def test_catalog_is_same_for_listing_and_activation_and_checks_capabilities(tmp_path: Path):
    folder = tmp_path / "inspect"
    folder.mkdir()
    (folder / "SKILL.md").write_text("---\nname: inspect\ndescription: Inspect\nallowed-tools: [part_detail]\n---\nbody", encoding="utf-8")
    catalog = SkillCatalog(tmp_path)
    assert catalog.list(set()) == []
    with pytest.raises(ValueError):
        catalog.get("inspect", set())
    assert [item.name for item in catalog.list({"part_detail"})] == ["inspect"]
    assert len(catalog.activate(["inspect", "inspect"], {"part_detail"})) == 1
    with pytest.raises(ValueError):
        catalog.get("../inspect", {"part_detail"})


def test_symlink_escape_is_not_a_published_skill(tmp_path: Path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "SKILL.md").write_text("---\nname: escape\ndescription: x\n---\nbody", encoding="utf-8")
    root = tmp_path / "root"
    root.mkdir()
    try:
        (root / "escape").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation requires local Windows privileges")
    with pytest.raises(ValueError):
        SkillCatalog(root).get("escape", set())


def test_resolved_file_outside_skill_root_is_rejected_without_symlink_privileges(tmp_path: Path, monkeypatch):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside" / "SKILL.md"
    outside.parent.mkdir()
    outside.write_text("---\nname: escape\ndescription: x\n---\nbody", encoding="utf-8")
    candidate = root / "escape" / "SKILL.md"
    original_resolve = Path.resolve

    def resolve(path, *args, **kwargs):
        return outside if path == candidate else original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", resolve)
    with pytest.raises(ValueError, match="SKILL_NOT_AVAILABLE"):
        SkillCatalog(root).get("escape", set())
