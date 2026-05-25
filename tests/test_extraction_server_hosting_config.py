from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVER = (ROOT / "real-extraction-server.py").read_text(encoding="utf-8")
STEPPED_SERVER = (ROOT / "stepped-pipeline-server.py").read_text(encoding="utf-8")


def test_extraction_server_has_no_hardcoded_preview_domain() -> None:
    assert "9136ea47-1260-4a5e-8d7b-17ebaf01c724" not in SERVER
    assert "worf.replit.dev" not in SERVER
    assert "https://*.replit.app" not in SERVER
    assert "https://*.replit.dev" not in SERVER


def test_extraction_server_uses_operator_configured_urls() -> None:
    assert "HIVE_CONTENT_BASE_URL" in SERVER
    assert "HIVE_EXPLORER_BASE_URL" in SERVER
    assert "FRONTEND_BASE_URL" in SERVER
    assert "EXTRACTION_CORS_ORIGINS" in SERVER
    assert "origins=get_cors_origins()" in SERVER


def test_extraction_user_agent_matches_repo_identity() -> None:
    assert "ArcHive-ContentExtractor/1.0" not in SERVER
    assert "AncientHighTechCompression-Extractor/1.0" in SERVER


def test_visible_verification_surfaces_match_repo_identity() -> None:
    assert "<title>ArcHive" not in SERVER
    assert "<h1>ArcHive" not in SERVER
    assert "Powered by <strong>ArcHive" not in SERVER
    assert "Using proven ArcHive extraction pipeline" not in SERVER
    assert "Ancient High-Tech Compression - Blockchain Verification" in SERVER
    assert "AncientHighTech_Token_Storage_v1.0" in SERVER
    assert "AncientHighTech_Data_Export_" in SERVER
    assert "serves the ArcHive UI" not in STEPPED_SERVER
    assert "serves the Ancient High-Tech UI" in STEPPED_SERVER
