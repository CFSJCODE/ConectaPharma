import os
import tempfile

os.environ.setdefault("CONNECTAPHARMA_ALLOW_LEGACY_JWT", "true")
os.environ.setdefault("CONNECTAPHARMA_DATA_FILE", os.path.join(tempfile.gettempdir(), "conectapharma_test_db.json"))

from fastapi.testclient import TestClient

from Backend.backend_python import app


client = TestClient(app)


def get_auth_headers() -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@conectapharma.com", "password": "admin123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_healthz_returns_ok():
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_returns_jwt_and_user():
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@conectapharma.com", "password": "admin123"},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "admin@conectapharma.com"


def test_me_requires_valid_token():
    response = client.get("/api/v1/auth/me")

    assert response.status_code in (401, 403)


def test_me_returns_current_user_with_token():
    response = client.get("/api/v1/auth/me", headers=get_auth_headers())

    assert response.status_code == 200
    assert response.json()["email"] == "admin@conectapharma.com"


def test_alertas_contract():
    response = client.get("/api/v1/alertas", headers=get_auth_headers())

    body = response.json()
    assert response.status_code == 200
    assert len(body) >= 1
    assert {"id", "medicamento_id", "nome", "dias_restantes", "status", "recomendacao"} <= set(body[0])


def test_farmacias_mapa_contract():
    response = client.get("/api/v1/farmacias/mapa", headers=get_auth_headers())

    body = response.json()
    assert response.status_code == 200
    assert len(body) >= 1
    assert {
        "id",
        "nome",
        "distancia_km",
        "disponibilidade_farmaco",
        "horario_funcionamento",
        "endereco",
        "avaliacao",
    } <= set(body[0])

def test_farmacias_proximas_processa_no_backend_com_fallback_mock():
    response = client.get(
        "/api/v1/farmacias/proximas",
        params={
            "lat": -19.9191,
            "lng": -43.9386,
            "radius_km": 10,
            "open_now": True,
            "limit": 10,
            "source": "mock",
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["source"] == "local_mock"
    assert body["count"] >= 1
    assert {
        "id",
        "name",
        "address",
        "latitude",
        "longitude",
        "distance_km",
        "is_open",
        "status_label",
        "opening_hours_label",
        "maps_url",
    } <= set(body["items"][0])


def test_rnds_status_defaults_to_dry_run():
    response = client.get("/api/v1/integracoes/rnds/status", headers=get_auth_headers())

    body = response.json()
    assert response.status_code == 200
    assert body["enabled"] is False
    assert body["configured"] is False
    assert body["mode"] == "dry-run"


def test_rnds_dispensacao_builds_fhir_bundle_in_dry_run():
    response = client.post(
        "/api/v1/integracoes/rnds/dispensacao",
        headers=get_auth_headers(),
        json={
            "cidadao_cns": "123456789012345",
            "paciente_nome": "Maria Silva",
            "medicamento_nome": "Losartana 50mg",
            "quantidade": 30,
            "unidade": "comprimidos",
            "estabelecimento_cnes": "1234567",
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["mode"] == "dry-run"
    assert body["sent"] is False
    assert body["request_preview"]["resourceType"] == "Bundle"
    assert body["request_preview"]["type"] == "document"


def test_farmacias_search_filters_by_query():
    response = client.get("/api/v1/farmacias", params={"q": "central", "limit": 10})

    body = response.json()
    assert response.status_code == 200
    assert len(body) >= 1
    assert any("Central" in item["nome"] for item in body)
    assert {"id", "nome", "endereco", "maps_url", "status_label"} <= set(body[0])


def test_medicamentos_catalogo_search():
    response = client.get("/api/v1/saude/medicamentos", params={"q": "losartana", "limit": 10})

    body = response.json()
    assert response.status_code == 200
    assert len(body) >= 1
    assert body[0]["nome"] == "Losartana 50mg"


def test_obter_medicamento_por_id():
    response = client.get("/api/v1/saude/medicamentos/1")

    assert response.status_code == 200
    assert response.json()["id"] == 1
