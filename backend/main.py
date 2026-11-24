import json
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from backend.exportador_pdf import gerar_pdf_masmorra
from backend.gerador import (
	criar_masmorra,
	expandir_saida,
	gerar_masmorra_completa,
	listar_tipos_masmorra,
	remover_peca,
	rerolar_peca,
)
from backend.modelos import (
	ConfigExportacaoPDF,
	ExpandirSaidaRequest,
	GerarCompletaRequest,
	Masmorra,
	NovaMasmorraRequest,
	RerolarPecaRequest,
)


BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
MASMORRAS_DIR = BASE_DIR / "masmorras"
MASMORRAS_DIR.mkdir(parents=True, exist_ok=True)

PADRAO_ID_SEGURO = re.compile(r"^[a-zA-Z0-9_-]+$")

app = FastAPI(title="Gerador de Masmorras")
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR / "static")), name="static")


@app.middleware("http")
async def adicionar_cabecalhos_seguranca(request: Request, call_next):
	resposta = await call_next(request)
	resposta.headers["X-Content-Type-Options"] = "nosniff"
	resposta.headers["X-Frame-Options"] = "DENY"
	resposta.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
	return resposta


def caminho_masmorra(masmorra_id: str) -> Path:
	if not PADRAO_ID_SEGURO.match(masmorra_id):
		raise HTTPException(status_code=400, detail="Identificador de masmorra inválido.")
	return MASMORRAS_DIR / f"{masmorra_id}.json"


def salvar_masmorra_disco(masmorra: Masmorra) -> None:
	caminho = caminho_masmorra(masmorra.id)
	conteudo = json.dumps(masmorra.model_dump(), indent="\t", ensure_ascii=False)
	caminho.write_text(conteudo, encoding="utf-8")


def carregar_masmorra_disco(masmorra_id: str) -> Masmorra:
	caminho = caminho_masmorra(masmorra_id)
	if not caminho.exists():
		raise HTTPException(status_code=404, detail="Masmorra não encontrada.")
	return Masmorra.model_validate_json(caminho.read_text(encoding="utf-8"))


@app.get("/health")
def verificar_saude() -> dict:
	return {"status": "ok"}


@app.get("/")
def pagina_inicial() -> FileResponse:
	return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/api/tabelas/opcoes")
def obter_opcoes_tabelas() -> dict:
	return {"tipos_masmorra": listar_tipos_masmorra()}


@app.get("/api/masmorras")
def listar_masmorras() -> list[dict]:
	itens = []
	for arquivo in sorted(MASMORRAS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
		dados = Masmorra.model_validate_json(arquivo.read_text(encoding="utf-8"))
		itens.append({
			"id": dados.id,
			"nome": dados.nome,
			"tipo_masmorra": dados.tipo_masmorra,
			"seed": dados.seed,
			"qtd_pecas": len(dados.pecas),
		})
	return itens


@app.post("/api/masmorras/nova")
def criar_nova_masmorra(req: NovaMasmorraRequest) -> Masmorra:
	masmorra = criar_masmorra(req.nome, req.tipo_masmorra, req.seed)
	salvar_masmorra_disco(masmorra)
	return masmorra


@app.get("/api/masmorras/{masmorra_id}")
def buscar_masmorra(masmorra_id: str) -> Masmorra:
	return carregar_masmorra_disco(masmorra_id)


@app.put("/api/masmorras/{masmorra_id}")
def atualizar_masmorra(masmorra_id: str, masmorra: Masmorra) -> Masmorra:
	if masmorra.id != masmorra_id:
		raise HTTPException(status_code=400, detail="ID da masmorra não corresponde à rota.")
	salvar_masmorra_disco(masmorra)
	return masmorra


@app.delete("/api/masmorras/{masmorra_id}")
def excluir_masmorra(masmorra_id: str) -> dict:
	caminho = caminho_masmorra(masmorra_id)
	if not caminho.exists():
		raise HTTPException(status_code=404, detail="Masmorra não encontrada.")
	caminho.unlink()
	return {"removida": masmorra_id}


@app.post("/api/masmorras/{masmorra_id}/expandir")
def expandir_proxima_sala(masmorra_id: str, req: ExpandirSaidaRequest) -> dict:
	masmorra = carregar_masmorra_disco(masmorra_id)
	masmorra_atualizada, nova_peca = expandir_saida(masmorra, req.peca_id, req.saida_id)
	salvar_masmorra_disco(masmorra_atualizada)
	return {
		"masmorra": masmorra_atualizada,
		"nova_peca_id": nova_peca.id if nova_peca else None,
	}


@app.post("/api/masmorras/{masmorra_id}/rerolar/{peca_id}")
def rerolar_peca_endpoint(masmorra_id: str, peca_id: str, req: RerolarPecaRequest) -> Masmorra:
	masmorra = carregar_masmorra_disco(masmorra_id)
	masmorra_atualizada = rerolar_peca(masmorra, peca_id, req.escopo)
	salvar_masmorra_disco(masmorra_atualizada)
	return masmorra_atualizada


@app.delete("/api/masmorras/{masmorra_id}/pecas/{peca_id}")
def remover_peca_endpoint(masmorra_id: str, peca_id: str) -> Masmorra:
	masmorra = carregar_masmorra_disco(masmorra_id)
	masmorra_atualizada = remover_peca(masmorra, peca_id)
	salvar_masmorra_disco(masmorra_atualizada)
	return masmorra_atualizada


@app.post("/api/masmorras/{masmorra_id}/gerar-completa")
def gerar_completa_endpoint(masmorra_id: str, req: GerarCompletaRequest) -> Masmorra:
	masmorra = carregar_masmorra_disco(masmorra_id)
	masmorra_atualizada = gerar_masmorra_completa(masmorra, req.total_salas)
	salvar_masmorra_disco(masmorra_atualizada)
	return masmorra_atualizada


@app.post("/api/masmorras/{masmorra_id}/exportar-pdf")
def exportar_pdf_endpoint(masmorra_id: str, config: ConfigExportacaoPDF) -> Response:
	masmorra = carregar_masmorra_disco(masmorra_id)
	pdf_bytes = gerar_pdf_masmorra(masmorra, config)
	slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", masmorra.nome).strip("_") or "masmorra"
	return Response(
		content=pdf_bytes,
		media_type="application/pdf",
		headers={"Content-Disposition": f'attachment; filename="{slug}.pdf"'},
	)
