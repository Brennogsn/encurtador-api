import logging
import random
import string
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from user_agents import parse as parse_user_agent

from app.database import get_db
from app.models import Link, Click, User
from app.schemas import (
    LinkCreate,
    LinkResponse,
    StatsResponse,
    UsuarioRegistrar,
    UsuarioLogin,
    UsuarioResponse,
    Token,
    DashboardResumo,
    CliquesPorDia,
    CliquesPorDispositivo,
    LinkRanking,
    EvolucaoResponse,
    PontoEvolucao,
    AlterarSenha,
)
from app.auth import hash_senha, verificar_senha, criar_access_token, get_current_user

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("encurtador")

router = APIRouter()

def gerar_codigo(tamanho=6):
    caracteres = string.ascii_letters + string.digits
    return "".join(random.choice(caracteres) for _ in range(tamanho))

def detectar_dispositivo(user_agent_str: str) -> str:
    ua = parse_user_agent(user_agent_str or "")
    if ua.is_tablet:
        return "tablet"
    if ua.is_mobile:
        return "mobile"
    return "desktop"

def limites_do_dia_utc(dia: date) -> tuple[datetime, datetime]:
    """Retorna (início, fim) do dia em UTC, para comparar direto com timestamps salvos."""
    inicio = datetime.combine(dia, time.min, tzinfo=timezone.utc)
    fim = inicio + timedelta(days=1)
    return inicio, fim

# ---------- Autenticação ----------

@router.post("/auth/registrar", response_model=UsuarioResponse)
def registrar(dados: UsuarioRegistrar, db: Session = Depends(get_db)):
    existente = db.query(User).filter(User.email == dados.email).first()
    if existente:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    novo_usuario = User(
        nome=dados.nome,
        email=dados.email,
        senha_hash=hash_senha(dados.senha),
    )
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)

    logger.info(f"Usuário registrado: {novo_usuario.email}")
    return novo_usuario

@router.post("/auth/login", response_model=Token)
def login(dados: UsuarioLogin, db: Session = Depends(get_db)):
    usuario = db.query(User).filter(User.email == dados.email).first()

    if not usuario or not verificar_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")

    token = criar_access_token({"sub": str(usuario.id)})
    logger.info(f"Login realizado: {usuario.email}")
    return Token(access_token=token)

@router.get("/auth/me", response_model=UsuarioResponse)
def me(usuario_atual: User = Depends(get_current_user)):
    return usuario_atual

# ---------- Links ----------

@router.post("/shorten", response_model=LinkResponse)
def criar_link(
    link: LinkCreate,
    db: Session = Depends(get_db),
    usuario_atual: User = Depends(get_current_user),
):
    codigo = gerar_codigo()
    novo_link = Link(
        url_original=str(link.url_original),
        codigo_curto=codigo,
        user_id=usuario_atual.id,
    )

    db.add(novo_link)
    db.commit()
    db.refresh(novo_link)

    logger.info(f"Link criado: {codigo} -> {link.url_original} (usuário {usuario_atual.id})")
    return novo_link

@router.get("/links")
def listar_links(
    db: Session = Depends(get_db),
    usuario_atual: User = Depends(get_current_user),
):
    links = (
        db.query(Link)
        .filter(Link.user_id == usuario_atual.id)
        .order_by(Link.criado_em.desc())
        .all()
    )
    resultado = []
    for link in links:
        total = db.query(func.count(Click.id)).filter(Click.link_id == link.id).scalar()
        resultado.append({
            "codigo_curto": link.codigo_curto,
            "url_original": link.url_original,
            "criado_em": link.criado_em,
            "total_clicks": total,
        })
    return resultado

# ---------- Dashboard ----------

@router.get("/dashboard/resumo", response_model=DashboardResumo)
def dashboard_resumo(
    db: Session = Depends(get_db),
    usuario_atual: User = Depends(get_current_user),
):
    link_ids = [
        link.id
        for link in db.query(Link).filter(Link.user_id == usuario_atual.id).all()
    ]
    total_links = len(link_ids)

    hoje = datetime.now(timezone.utc).date()

    # Sempre gera os 7 dias (mesmo sem nenhum link ainda), pra manter o contrato da API estável
    cliques_por_dia = []
    for i in range(6, -1, -1):
        dia = hoje - timedelta(days=i)
        if link_ids:
            inicio, fim = limites_do_dia_utc(dia)
            qtd = (
                db.query(func.count(Click.id))
                .filter(Click.link_id.in_(link_ids))
                .filter(Click.timestamp >= inicio, Click.timestamp < fim)
                .scalar()
            )
        else:
            qtd = 0
        cliques_por_dia.append(CliquesPorDia(dia=dia, cliques=qtd))

    if not link_ids:
        return DashboardResumo(
            total_links=0,
            total_cliques=0,
            cliques_hoje=0,
            taxa_cliques=0.0,
            cliques_por_dia=cliques_por_dia,
            cliques_por_dispositivo=CliquesPorDispositivo(desktop=0, mobile=0, tablet=0),
            top_links=[],
        )

    cliques_query = db.query(Click).filter(Click.link_id.in_(link_ids))
    total_cliques = cliques_query.count()

    inicio_hoje, fim_hoje = limites_do_dia_utc(hoje)
    cliques_hoje = cliques_query.filter(
        Click.timestamp >= inicio_hoje, Click.timestamp < fim_hoje
    ).count()

    taxa_cliques = round((cliques_hoje / total_cliques) * 100, 2) if total_cliques else 0.0

    contagem_dispositivo = {"desktop": 0, "mobile": 0, "tablet": 0}
    for tipo, in cliques_query.with_entities(Click.device_type).all():
        if tipo in contagem_dispositivo:
            contagem_dispositivo[tipo] += 1
    dispositivo = CliquesPorDispositivo(**contagem_dispositivo)

    top = (
        db.query(Link, func.count(Click.id).label("total"))
        .join(Click, Click.link_id == Link.id)
        .filter(Link.id.in_(link_ids))
        .group_by(Link.id)
        .order_by(func.count(Click.id).desc())
        .limit(5)
        .all()
    )
    top_links = [
        LinkRanking(codigo_curto=link.codigo_curto, url_original=link.url_original, total_clicks=total)
        for link, total in top
    ]

    return DashboardResumo(
        total_links=total_links,
        total_cliques=total_cliques,
        cliques_hoje=cliques_hoje,
        taxa_cliques=taxa_cliques,
        cliques_por_dia=cliques_por_dia,
        cliques_por_dispositivo=dispositivo,
        top_links=top_links,
    )

# ---------- Rotas públicas (estatísticas + redirect) ----------

@router.get("/stats/{codigo}", response_model=StatsResponse)
def estatisticas(codigo: str, db: Session = Depends(get_db)):
    link = db.query(Link).filter(Link.codigo_curto == codigo).first()

    if not link:
        raise HTTPException(status_code=404, detail="Link não encontrado")

    total = db.query(func.count(Click.id)).filter(Click.link_id == link.id).scalar()

    return StatsResponse(
        codigo_curto=link.codigo_curto,
        url_original=link.url_original,
        total_clicks=total,
        criado_em=link.criado_em,
    )

@router.get("/{codigo}")
def redirecionar(codigo: str, request: Request, db: Session = Depends(get_db)):
    link = db.query(Link).filter(Link.codigo_curto == codigo).first()

    if not link:
        logger.warning(f"Tentativa de acessar código inexistente: {codigo}")
        raise HTTPException(status_code=404, detail="Link não encontrado")

    user_agent_str = request.headers.get("user-agent", "")
    dispositivo = detectar_dispositivo(user_agent_str)

    novo_click = Click(link_id=link.id, device_type=dispositivo)
    db.add(novo_click)
    db.commit()

    logger.info(f"Redirecionando: {codigo} -> {link.url_original} (dispositivo: {dispositivo})")
    return RedirectResponse(url=link.url_original)

# ---------- Estatísticas (evolução por período) ----------

@router.get("/estatisticas/evolucao", response_model=EvolucaoResponse)
def evolucao(
    periodo: str = "dia",
    db: Session = Depends(get_db),
    usuario_atual: User = Depends(get_current_user),
):
    if periodo not in ("dia", "semana", "mes"):
        raise HTTPException(status_code=400, detail="Período inválido. Use 'dia', 'semana' ou 'mes'.")

    link_ids = [
        link.id
        for link in db.query(Link).filter(Link.user_id == usuario_atual.id).all()
    ]

    agora = datetime.now(timezone.utc)
    pontos = []

    if not link_ids:
        if periodo == "dia":
            qtd_pontos, dias_por_ponto, formato = 7, 1, "%d/%m"
        elif periodo == "semana":
            qtd_pontos, dias_por_ponto, formato = 8, 7, "sem %d/%m"
        else:
            qtd_pontos, dias_por_ponto, formato = 6, 30, "%m/%Y"

        for i in range(qtd_pontos - 1, -1, -1):
            referencia = agora - timedelta(days=i * dias_por_ponto)
            pontos.append(PontoEvolucao(label=referencia.strftime(formato), cliques=0))
        return EvolucaoResponse(periodo=periodo, total_cliques=0, pontos=pontos)

    cliques_query = db.query(Click).filter(Click.link_id.in_(link_ids))
    total_cliques = cliques_query.count()

    if periodo == "dia":
        qtd_pontos, dias_por_ponto, formato = 7, 1, "%d/%m"
    elif periodo == "semana":
        qtd_pontos, dias_por_ponto, formato = 8, 7, "sem %d/%m"
    else:
        qtd_pontos, dias_por_ponto, formato = 6, 30, "%m/%Y"

    for i in range(qtd_pontos - 1, -1, -1):
        fim_ref = agora - timedelta(days=i * dias_por_ponto)
        inicio_ref = fim_ref - timedelta(days=dias_por_ponto)
        qtd = (
            cliques_query
            .filter(Click.timestamp >= inicio_ref, Click.timestamp < fim_ref)
            .count()
        )
        pontos.append(PontoEvolucao(label=fim_ref.strftime(formato), cliques=qtd))

    return EvolucaoResponse(periodo=periodo, total_cliques=total_cliques, pontos=pontos)

# ---------- Conta (senha e exclusão) ----------

@router.put("/auth/senha")
def alterar_senha(
    dados: AlterarSenha,
    db: Session = Depends(get_db),
    usuario_atual: User = Depends(get_current_user),
):
    if not verificar_senha(dados.senha_atual, usuario_atual.senha_hash):
        raise HTTPException(status_code=401, detail="Senha atual incorreta")

    usuario_atual.senha_hash = hash_senha(dados.nova_senha)
    db.commit()

    logger.info(f"Senha alterada: {usuario_atual.email}")
    return {"detail": "Senha alterada com sucesso"}

@router.delete("/auth/me")
def excluir_conta(
    db: Session = Depends(get_db),
    usuario_atual: User = Depends(get_current_user),
):
    email = usuario_atual.email
    db.delete(usuario_atual)
    db.commit()

    logger.info(f"Conta excluída: {email}")
    return {"detail": "Conta excluída com sucesso"}
