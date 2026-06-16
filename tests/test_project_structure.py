from pathlib import Path


def test_expected_project_files_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    expected_files = [
        ".env.example",
        ".gitignore",
        "README.md",
        "requirements.txt",
        "main.py",
        "config.py",
        "database.py",
        "lastfm_client.py",
        "spotify_client.py",
        "spotify_setup.py",
        "report_generator.py",
        "email_sender.py",
        "docs/M122E_Final_Documentation.docx",
        "docs/M122E_Final_Documentation.pdf",
        "docs/M122E_Test_Protocol.docx",
        "docs/M122E_Test_Protocol.pdf",
        "docs/M122E_Project_Plan_Spotify_Wrapped.xlsx",
        "docs/M122E_Project_Plan_Spotify_Wrapped.pdf",
        "docs/ProjectProposalM122E.docx",
        "docs/ProjectProposalM122E.pdf",
        "docs/assets/weekly_spotify_wrapped_cover.svg",
        "docs/assets/weekly_spotify_wrapped_cover.png",
        "docs/assets/weekly_spotify_wrapped_icon.svg",
        "docs/assets/weekly_spotify_wrapped_icon.png",
        "docs/diagrams/system_architecture_diagram.svg",
        "docs/diagrams/system_architecture_diagram.png",
        "docs/diagrams/uml_activity_diagram.svg",
        "docs/diagrams/uml_class_diagram.svg",
        "docs/diagrams/uml_component_diagram.svg",
        "docs/diagrams/uml_deployment_diagram.svg",
        "docs/diagrams/er_diagram.svg",
        "docs/diagrams/flowchart.svg",
    ]

    missing = [file_name for file_name in expected_files if not (root / file_name).exists()]

    assert missing == []


def test_every_application_module_has_a_matching_test_file() -> None:
    root = Path(__file__).resolve().parents[1]
    application_modules = [
        path
        for path in root.glob("*.py")
        if path.name not in {"__init__.py"}
    ]

    missing_tests = [
        module.name
        for module in application_modules
        if not (root / "tests" / f"test_{module.stem}.py").exists()
    ]

    assert missing_tests == []
