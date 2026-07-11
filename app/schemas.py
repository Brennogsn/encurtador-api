from pydantic import BaseModel, HttpUrl, EmailStr, ConfigDict, Field
from datetime import date, datetime

class LinkCreate(BaseModel):
    url_original: HttpUrl

class LinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    codigo_curto: str
    url_original: str

class StatsResponse(BaseModel):
    codigo_curto: str
    url_original: str
    total_clicks: int
    criado_em: datetime

class UsuarioRegistrar(BaseModel):
    nome: str = Field(min_length=1)
    email: EmailStr
    senha: str = Field(min_length=8)

class UsuarioLogin(BaseModel):
    email: EmailStr
    senha: str

class UsuarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    email: str
    criado_em: datetime

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class CliquesPorDia(BaseModel):
    dia: date
    cliques: int

class CliquesPorDispositivo(BaseModel):
    desktop: int
    mobile: int
    tablet: int

class LinkRanking(BaseModel):
    codigo_curto: str
    url_original: str
    total_clicks: int

class DashboardResumo(BaseModel):
    total_links: int
    total_cliques: int
    cliques_hoje: int
    taxa_cliques: float
    cliques_por_dia: list[CliquesPorDia]
    cliques_por_dispositivo: CliquesPorDispositivo
    top_links: list[LinkRanking]
