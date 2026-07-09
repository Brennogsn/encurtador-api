from pydantic import BaseModel, HttpUrl, ConfigDict
from datetime import datetime

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