import uuid

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def criar_usuario_e_logar():
    """Cria um usuário com e-mail único e retorna o header de autorização pronto pra usar."""
    email = f"usuario_{uuid.uuid4().hex[:10]}@teste.com"
    senha = "senha12345"

    resposta_registro = client.post(
        "/auth/registrar",
        json={"nome": "Usuário Teste", "email": email, "senha": senha},
    )
    assert resposta_registro.status_code == 200

    resposta_login = client.post("/auth/login", json={"email": email, "senha": senha})
    assert resposta_login.status_code == 200
    token = resposta_login.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}, email


# ---------- Autenticação ----------

def test_registrar_usuario():
    email = f"usuario_{uuid.uuid4().hex[:10]}@teste.com"
    response = client.post(
        "/auth/registrar",
        json={"nome": "Fulano", "email": email, "senha": "senha12345"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == email
    assert data["nome"] == "Fulano"
    assert "senha" not in data
    assert "senha_hash" not in data


def test_registrar_email_duplicado():
    email = f"usuario_{uuid.uuid4().hex[:10]}@teste.com"
    payload = {"nome": "Fulano", "email": email, "senha": "senha12345"}

    primeira = client.post("/auth/registrar", json=payload)
    assert primeira.status_code == 200

    segunda = client.post("/auth/registrar", json=payload)
    assert segunda.status_code == 400


def test_login_com_credenciais_corretas():
    _, email = criar_usuario_e_logar()
    assert email is not None


def test_login_com_senha_errada():
    email = f"usuario_{uuid.uuid4().hex[:10]}@teste.com"
    client.post(
        "/auth/registrar",
        json={"nome": "Fulano", "email": email, "senha": "senha12345"},
    )

    response = client.post("/auth/login", json={"email": email, "senha": "senha-errada"})
    assert response.status_code == 401


def test_auth_me_com_token_valido():
    headers, email = criar_usuario_e_logar()
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == email


def test_auth_me_sem_token():
    response = client.get("/auth/me")
    assert response.status_code == 401


# ---------- Links (exigem autenticação) ----------

def test_criar_link_sem_token_e_rejeitado():
    response = client.post("/shorten", json={"url_original": "https://exemplo.com"})
    assert response.status_code == 401


def test_criar_link_valido():
    headers, _ = criar_usuario_e_logar()
    response = client.post(
        "/shorten",
        json={"url_original": "https://exemplo.com"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "codigo_curto" in data
    assert data["url_original"] == "https://exemplo.com/"


def test_criar_link_url_invalida():
    headers, _ = criar_usuario_e_logar()
    response = client.post(
        "/shorten",
        json={"url_original": "isso-nao-e-uma-url"},
        headers=headers,
    )
    assert response.status_code == 422


def test_listar_links_mostra_apenas_os_do_usuario_logado():
    headers_a, _ = criar_usuario_e_logar()
    headers_b, _ = criar_usuario_e_logar()

    client.post(
        "/shorten", json={"url_original": "https://do-usuario-a.com"}, headers=headers_a
    )

    resposta_a = client.get("/links", headers=headers_a)
    resposta_b = client.get("/links", headers=headers_b)

    urls_a = [item["url_original"] for item in resposta_a.json()]
    urls_b = [item["url_original"] for item in resposta_b.json()]

    assert "https://do-usuario-a.com/" in urls_a
    assert "https://do-usuario-a.com/" not in urls_b


def test_redirecionar_link_existente():
    headers, _ = criar_usuario_e_logar()
    criar = client.post(
        "/shorten", json={"url_original": "https://google.com"}, headers=headers
    )
    codigo = criar.json()["codigo_curto"]

    response = client.get(f"/{codigo}", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "https://google.com/"


def test_redirecionar_codigo_inexistente():
    response = client.get("/codigo-que-nao-existe")
    assert response.status_code == 404
    assert response.json()["detail"] == "Link não encontrado"


def test_estatisticas_link_existente():
    headers, _ = criar_usuario_e_logar()
    criar = client.post(
        "/shorten", json={"url_original": "https://github.com"}, headers=headers
    )
    codigo = criar.json()["codigo_curto"]

    client.get(f"/{codigo}", follow_redirects=False)
    client.get(f"/{codigo}", follow_redirects=False)

    response = client.get(f"/stats/{codigo}")
    assert response.status_code == 200
    assert response.json()["total_clicks"] == 2


def test_estatisticas_codigo_inexistente():
    response = client.get("/stats/nao-existe-esse")
    assert response.status_code == 404


# ---------- Dashboard / resumo ----------

def test_resumo_sem_token_e_rejeitado():
    response = client.get("/dashboard/resumo")
    assert response.status_code == 401


def test_resumo_sem_links_retorna_zerado():
    headers, _ = criar_usuario_e_logar()
    response = client.get("/dashboard/resumo", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_links"] == 0
    assert data["total_cliques"] == 0
    assert data["cliques_hoje"] == 0
    assert data["taxa_cliques"] == 0.0
    assert len(data["cliques_por_dia"]) == 7
    assert data["top_links"] == []


def test_resumo_reflete_links_e_cliques_criados():
    headers, _ = criar_usuario_e_logar()
    criar = client.post(
        "/shorten", json={"url_original": "https://exemplo.com"}, headers=headers
    )
    codigo = criar.json()["codigo_curto"]

    client.get(f"/{codigo}", follow_redirects=False)
    client.get(f"/{codigo}", follow_redirects=False)

    response = client.get("/dashboard/resumo", headers=headers)
    data = response.json()

    assert data["total_links"] == 1
    assert data["total_cliques"] == 2
    assert data["cliques_hoje"] == 2
    assert data["taxa_cliques"] == 100.0
    assert data["cliques_por_dispositivo"]["desktop"] == 2
    assert len(data["top_links"]) == 1
    assert data["top_links"][0]["codigo_curto"] == codigo
    assert data["top_links"][0]["total_clicks"] == 2


def test_resumo_isola_dados_entre_usuarios():
    headers_a, _ = criar_usuario_e_logar()
    headers_b, _ = criar_usuario_e_logar()

    client.post(
        "/shorten", json={"url_original": "https://so-do-a.com"}, headers=headers_a
    )

    resumo_b = client.get("/dashboard/resumo", headers=headers_b)
    assert resumo_b.json()["total_links"] == 0
