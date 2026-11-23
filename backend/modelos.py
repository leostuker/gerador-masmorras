from typing import Literal
from pydantic import BaseModel, Field


Direcao = Literal["N", "S", "L", "O"]
TipoPeca = Literal["sala", "corredor", "escada"]
EscopoRerolagem = Literal["povoamento", "geometria", "tudo"]


class Celula(BaseModel):
	x: int
	y: int


class Saida(BaseModel):
	id: str
	x: int
	y: int
	direcao: Direcao
	tipo_porta: str
	descricao_porta: str
	secreta: bool = False
	trancada: bool = False
	conectada_a: str | None = None
	aberta: bool = True


class Povoamento(BaseModel):
	proposito: str = ""
	categoria_2024: str = ""
	estado_atual: str = ""
	conteudo: str = ""
	monstros_motivacao: str = ""
	perigo: str = ""
	obstaculo: str = ""
	armadilha: str = ""
	arapuca: str = ""
	tesouro: str = ""
	barulho: str = ""
	odor: str = ""
	mobilia: str = ""
	notas: str = ""


class Peca(BaseModel):
	id: str
	tipo: TipoPeca
	formato: str
	descricao_geometria: str
	celulas: list[Celula]
	saidas: list[Saida] = Field(default_factory=list)
	povoamento: Povoamento


class Masmorra(BaseModel):
	id: str
	nome: str
	tipo_masmorra: str
	peculiaridade: str
	estado_conservacao: str
	pecas: list[Peca] = Field(default_factory=list)


class NovaMasmorraRequest(BaseModel):
	nome: str = "Nova Masmorra"
	tipo_masmorra: str = "geral"


class ExpandirSaidaRequest(BaseModel):
	peca_id: str
	saida_id: str


class RerolarPecaRequest(BaseModel):
	escopo: EscopoRerolagem = "tudo"


class GerarCompletaRequest(BaseModel):
	total_salas: int = Field(default=10, ge=2, le=50)


class ConfigExportacaoPDF(BaseModel):
	tamanho_quadrado_mm: float = Field(default=25.0, ge=5.0, le=80.0)
	incluir_mapa_geral: bool = True
	incluir_guia_mestre: bool = True
