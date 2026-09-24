"""Community-edition notice and repository-content safeguards."""

from pathlib import Path

import docformat_gui as gui


PROJECT_ROOT = Path(__file__).parent.parent

# Assembled at runtime so this guard file never contains the literals it forbids;
# a plain substring search over the repository therefore stays meaningful.
_FORBIDDEN_PROMOTION_MARKERS = (
    "Pro" + " 版",
    "闲" + "鱼",
    "xian" + "yu",
    "goo" + "fish",
    "19" + ".9",
    "购买" + "渠道",
    "购买" + "激活码",
    "ProInfo" + "Dialog",
    "EMBEDDED_PRO" + "_INFO_TEXT",
)

_SCANNED_FILES = (
    "docformat_gui.py",
    "README.md",
    "README_EN.md",
    "build.py",
    ".github/workflows/build.yml",
)


def test_notice_schedule_uses_the_declared_community_edition_launches():
    for start_count in (1, 3, 7, 10, 20):
        assert gui.should_show_community_notice(start_count)

    for start_count in (2, 4, 6, 8, 11, 21):
        assert not gui.should_show_community_notice(start_count)


def test_notice_only_contains_the_free_software_disclosure():
    assert gui.COMMUNITY_NOTICE_TEXT == (
        "本工具完全免费开源，不收取任何费用；如从网络付费购买，请举报商家并要求退款。"
    )


def test_repository_does_not_ship_promotional_or_paid_upgrade_surfaces():
    assert not (PROJECT_ROOT / ("PRO" + ".md")).exists()
    assert not (PROJECT_ROOT / "assets" / ("xian" + "yu_qr.png")).exists()

    for relative_path in _SCANNED_FILES:
        source = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        for marker in _FORBIDDEN_PROMOTION_MARKERS:
            assert marker not in source, f"{relative_path} still mentions {marker}"


def test_build_outputs_do_not_bundle_a_promotional_image():
    build_script = (PROJECT_ROOT / "build.py").read_text(encoding="utf-8")
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8")

    assert "--add-data=scripts" in build_script
    assert '--add-data "scripts:scripts"' in workflow
    assert (PROJECT_ROOT / "assets" / "icon.ico").is_file()


def test_ui_keeps_the_community_notice_and_about_dialog():
    source = (PROJECT_ROOT / "docformat_gui.py").read_text(encoding="utf-8")
    for text in (
        "继续使用开源社区版",
        "此版本为开源社区版",
        "CommunityNoticeTicker",
        "CommunityEditionDialog",
        "AboutDialog",
    ):
        assert text in source


def test_about_dialog_keeps_the_mit_attribution():
    """MIT requires the copyright notice to travel with the software."""
    source = (PROJECT_ROOT / "docformat_gui.py").read_text(encoding="utf-8")

    assert "开发者：KaguraNanaga" in source
    assert "许可证：MIT License" in source

    license_text = (PROJECT_ROOT / "LICENSE").read_text(encoding="utf-8")
    assert license_text.startswith("MIT License")
    assert "Copyright (c) 2025 KaguraNanaga" in license_text
