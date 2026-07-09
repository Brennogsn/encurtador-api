import logging
import random
import string
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Link, Click
from app.schemas import LinkCreate, LinkResponse, StatsResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("encurtador")

router = APIRouter()

def gerar_codigo(tamanho=6):
    caracteres = string.ascii_letters + string.digits
    return "".join(random.choice(caracteres) for _ in range(tamanho))

@router.post("/shorten", response_model=LinkResponse)
def criar_link(link: LinkCreate, db: Session = Depends(get_db)):
    codigo = gerar_codigo()
    novo_link = Link(url_original=str(link.url_original), codigo_curto=codigo)

    db.add(novo_link)
    db.commit()
    db.refresh(novo_link)

    logger.info(f"Link criado: {codigo} -> {link.url_original}")
    return novo_link

@router.get("/links")
def listar_links(db: Session = Depends(get_db)):
    links = db.query(Link).order_by(Link.criado_em.desc()).all()
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
def redirecionar(codigo: str, db: Session = Depends(get_db)):
    link = db.query(Link).filter(Link.codigo_curto == codigo).first()

    if not link:
        logger.warning(f"Tentativa de acessar código inexistente: {codigo}")
        raise HTTPException(status_code=404, detail="Link não encontrado")

    novo_click = Click(link_id=link.id)
    db.add(novo_click)
    db.commit()

    logger.info(f"Redirecionando: {codigo} -> {link.url_original}")
    return RedirectResponse(url=link.url_original)