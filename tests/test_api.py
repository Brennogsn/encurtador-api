from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_criar_link_valido():
    """Testa se um link válido é criado com sucesso"""
    response = client.post("/shorten", json={"url_original": "https://exemplo.com"})
    assert response.status_code == 200
    data = response.json()
    assert "codigo_curto" in data
    assert data["url_original"] == "https://exemplo.com/"


def test_criar_link_url_invalida():
    """Testa se uma URL inválida é rejeitada pela validação"""
    response = client.post("/shorten", json={"url_original": "isso-nao-e-uma-url"})
    assert response.status_code == 422  # erro de validação do Pydantic


def test_redirecionar_link_existente():
    """Cria um link e testa se o redirecionamento funciona"""
    criar = client.post("/shorten", json={"url_original": "https://google.com"})
    codigo = criar.json()["codigo_curto"]

    response = client.get(f"/{codigo}", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "https://google.com/"


def test_redirecionar_codigo_inexistente():
    """Testa se um código que não existe retorna 404"""
    response = client.get("/codigo-que-nao-existe")
    assert response.status_code == 404
    assert response.json()["detail"] == "Link não encontrado"


def test_estatisticas_link_existente():
    """Cria um link, acessa ele, e verifica se o contador de cliques bate"""
    criar = client.post("/shorten", json={"url_original": "https://github.com"})
    codigo = criar.json()["codigo_curto"]

    client.get(f"/{codigo}", follow_redirects=False)
    client.get(f"/{codigo}", follow_redirects=False)

    response = client.get(f"/stats/{codigo}")
    assert response.status_code == 200
    data = response.json()
    assert data["total_clicks"] == 2


def test_estatisticas_codigo_inexistente():
    """Testa se estatísticas de um código inexistente retornam 404"""
    response = client.get("/stats/nao-existe-esse")
    assert response.status_code == 404
