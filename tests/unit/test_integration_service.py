from unittest.mock import MagicMock, patch

import pytest

from core.integrations.base import Document
from services.integration_service import IntegrationService, SyncResult

# ── Helpers ──────────────────────────────────────────────────────────────────

def _doc(title: str, source: str = "google_drive") -> Document:
    return Document(content=f"contenido de {title}", source=source, title=title)


def _make_drive(*, healthy: bool = True, docs: list[Document] | None = None):
    mock = MagicMock()
    mock.health_check.return_value = healthy
    mock.fetch_documents.return_value = docs or []
    mock.search.return_value = docs or []
    return mock


def _make_clickup(*, authenticated: bool = True, healthy: bool = True, docs: list[Document] | None = None):
    mock = MagicMock()
    mock.is_authenticated.return_value = authenticated
    mock.health_check.return_value = healthy
    mock.fetch_documents.return_value = docs or []
    mock.search.return_value = docs or []
    return mock


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def svc_with_drive():
    """IntegrationService con Drive activo y ClickUp sin autenticar."""
    with patch("services.integration_service.GoogleDriveIntegration") as MockDrive, \
         patch("services.integration_service.ClickUpIntegration") as MockClickUp:

        MockDrive.return_value = _make_drive(healthy=True)
        MockClickUp.return_value = _make_clickup(authenticated=False)

        svc = IntegrationService(google_access_token="token-fake", clickup_user_id="u1")
        svc._drive   = MockDrive.return_value
        svc._clickup = MockClickUp.return_value
        yield svc


@pytest.fixture
def svc_full():
    """IntegrationService con Drive y ClickUp ambos activos."""
    with patch("services.integration_service.GoogleDriveIntegration") as MockDrive, \
         patch("services.integration_service.ClickUpIntegration") as MockClickUp:

        MockDrive.return_value   = _make_drive(healthy=True)
        MockClickUp.return_value = _make_clickup(authenticated=True, healthy=True)

        svc = IntegrationService(google_access_token="token-fake", clickup_user_id="u1")
        svc._drive   = MockDrive.return_value
        svc._clickup = MockClickUp.return_value
        yield svc


# ── status() ─────────────────────────────────────────────────────────────────

class TestStatus:

    def test_drive_connected_clickup_not_authenticated(self, svc_with_drive):
        status = svc_with_drive.status()
        assert status["google_drive"] is True
        assert status["clickup"] is False

    def test_both_connected(self, svc_full):
        status = svc_full.status()
        assert status["google_drive"] is True
        assert status["clickup"] is True

    def test_no_drive_token_disables_drive(self):
        with patch("services.integration_service.ClickUpIntegration") as MockClickUp:
            MockClickUp.return_value = _make_clickup(authenticated=False)
            svc = IntegrationService(google_access_token=None, clickup_user_id="u1")
            assert svc.status()["google_drive"] is False

    def test_drive_unhealthy_returns_false(self):
        with patch("services.integration_service.GoogleDriveIntegration") as MockDrive, \
             patch("services.integration_service.ClickUpIntegration") as MockClickUp:

            MockDrive.return_value   = _make_drive(healthy=False)
            MockClickUp.return_value = _make_clickup(authenticated=False)

            svc = IntegrationService(google_access_token="token", clickup_user_id="u1")
            svc._drive = MockDrive.return_value
            assert svc.status()["google_drive"] is False


# ── sync() ────────────────────────────────────────────────────────────────────

class TestSync:

    def test_drive_docs_returned(self, svc_with_drive):
        drive_docs = [_doc("Archivo A"), _doc("Archivo B")]
        svc_with_drive._drive.fetch_documents.return_value = drive_docs

        result = svc_with_drive.sync()

        assert isinstance(result, SyncResult)
        assert result.drive_docs == drive_docs
        assert result.clickup_docs == []
        assert result.total == 2

    def test_both_sources_combined(self, svc_full):
        drive_docs   = [_doc("Drive Doc", "google_drive")]
        clickup_docs = [_doc("ClickUp Task", "clickup")]
        svc_full._drive.fetch_documents.return_value   = drive_docs
        svc_full._clickup.fetch_documents.return_value = clickup_docs

        result = svc_full.sync()

        assert result.drive_docs   == drive_docs
        assert result.clickup_docs == clickup_docs
        assert result.total == 2
        assert set(d.source for d in result.all_docs) == {"google_drive", "clickup"}

    def test_drive_error_captured_not_raised(self, svc_with_drive):
        svc_with_drive._drive.fetch_documents.side_effect = RuntimeError("fallo de red")

        result = svc_with_drive.sync()

        assert result.drive_docs == []
        assert len(result.errors) == 1
        assert "Drive" in result.errors[0]

    def test_clickup_error_captured_not_raised(self, svc_full):
        svc_full._clickup.fetch_documents.side_effect = RuntimeError("timeout")

        result = svc_full.sync()

        assert result.clickup_docs == []
        assert any("ClickUp" in e for e in result.errors)

    def test_no_drive_skips_drive_fetch(self):
        with patch("services.integration_service.ClickUpIntegration") as MockClickUp:
            MockClickUp.return_value = _make_clickup(authenticated=False)
            svc = IntegrationService(google_access_token=None, clickup_user_id="u1")
            result = svc.sync()

        assert result.drive_docs == []
        assert result.errors == []

    def test_sync_result_total_property(self):
        result = SyncResult(
            drive_docs=[_doc("A"), _doc("B")],
            clickup_docs=[_doc("C", "clickup")],
        )
        assert result.total == 3
        assert len(result.all_docs) == 3


# ── search() ─────────────────────────────────────────────────────────────────

class TestSearch:

    def test_search_combines_both_sources(self, svc_full):
        drive_hits   = [_doc("Drive resultado")]
        clickup_hits = [_doc("ClickUp resultado", "clickup")]
        svc_full._drive.search.return_value   = drive_hits
        svc_full._clickup.search.return_value = clickup_hits

        results = svc_full.search("presupuesto")

        assert len(results) == 2
        svc_full._drive.search.assert_called_once_with("presupuesto")
        svc_full._clickup.search.assert_called_once_with("presupuesto")

    def test_search_drive_error_returns_partial(self, svc_full):
        svc_full._drive.search.side_effect = RuntimeError("error")
        svc_full._clickup.search.return_value = [_doc("ClickUp resultado", "clickup")]

        results = svc_full.search("algo")

        assert len(results) == 1
        assert results[0].source == "clickup"

    def test_search_without_drive(self):
        with patch("services.integration_service.ClickUpIntegration") as MockClickUp:
            mock_cu = _make_clickup(authenticated=True, docs=[_doc("Task", "clickup")])
            MockClickUp.return_value = mock_cu
            svc = IntegrationService(google_access_token=None, clickup_user_id="u1")
            svc._clickup = mock_cu

            results = svc.search("tarea")

        assert all(d.source == "clickup" for d in results)
