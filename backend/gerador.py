import hashlib
import json
import random
import secrets
import uuid
from pathlib import Path

from backend.modelos import Celula, Masmorra, Peca, Povoamento, Saida


BASE_DIR = Path(__file__).resolve().parent.parent
DADOS_DIR = BASE_DIR / "dados"

VETORES_DIRECAO = {
	"N": (0, -1),
	"S": (0, 1),
	"L": (1, 0),
	"O": (-1, 0),
}

DIRECAO_OPOSTA = {
	"N": "S",
	"S": "N",
	"L": "O",
	"O": "L",
}

VIRAR_ESQUERDA = {
	"N": "O",
	"O": "S",
	"S": "L",
	"L": "N",
}

VIRAR_DIREITA = {
	"N": "L",
	"L": "S",
	"S": "O",
	"O": "N",
}


def carregar_json(nome_arquivo: str) -> dict:
	caminho = DADOS_DIR / nome_arquivo
	return json.loads(caminho.read_text(encoding="utf-8"))


TABELAS_GEOMETRIA = carregar_json("tabelas_geometria.json")
TABELAS_PROPOSITO = carregar_json("tabelas_proposito.json")
TABELAS_POVOAMENTO = carregar_json("tabelas_povoamento.json")
TABELAS_AMBIENTACAO = carregar_json("tabelas_ambientacao.json")


def gerar_seed_aleatoria() -> str:
	return secrets.token_hex(4).upper()


def normalizar_seed(seed: str | None) -> str:
	if seed is not None:
		limpa = seed.strip()
		if limpa:
			return limpa
	return gerar_seed_aleatoria()


def criar_rng(seed: str, contexto: str) -> random.Random:
	digest = hashlib.sha256(f"{seed}|{contexto}".encode("utf-8")).digest()
	return random.Random(int.from_bytes(digest, "big"))


def obter_seed_efetiva(masmorra: Masmorra) -> str:
	if not masmorra.seed:
		masmorra.seed = masmorra.id.upper()
	return masmorra.seed


def rolar_tabela(entradas: list[dict], lados: int, rng: random.Random) -> dict:
	valor = rng.randint(1, lados)
	for entrada in entradas:
		if entrada["min"] <= valor <= entrada["max"]:
			return entrada
	return entradas[-1]


def listar_tipos_masmorra() -> list[dict]:
	tipos = []
	for chave, dados in TABELAS_PROPOSITO["tipos_masmorra"].items():
		tipos.append({"id": chave, "nome": dados["nome"]})
	return tipos


def conjunto_celulas_ocupadas(masmorra: Masmorra, ignorar_peca_id: str | None = None) -> dict[tuple[int, int], str]:
	ocupadas: dict[tuple[int, int], str] = {}
	for peca in masmorra.pecas:
		if peca.id == ignorar_peca_id:
			continue
		for cel in peca.celulas:
			ocupadas[(cel.x, cel.y)] = peca.id
	return ocupadas


def proximo_id_peca(masmorra: Masmorra, tipo: str) -> str:
	prefixos = {"sala": "S", "corredor": "C", "escada": "E"}
	prefixo = prefixos.get(tipo, "S")
	maior = 0
	for peca in masmorra.pecas:
		if peca.id.startswith(prefixo) and peca.id[1:].isdigit():
			numero = int(peca.id[1:])
			if numero > maior:
				maior = numero
	return f"{prefixo}{maior + 1}"


def gerar_id_saida(peca_id: str, saidas_existentes: list[Saida]) -> str:
	usados = {s.id for s in saidas_existentes}
	indice = len(saidas_existentes) + 1
	while f"{peca_id}_O{indice}" in usados:
		indice += 1
	return f"{peca_id}_O{indice}"


def obter_peca(masmorra: Masmorra, peca_id: str) -> Peca | None:
	for peca in masmorra.pecas:
		if peca.id == peca_id:
			return peca
	return None


def gerar_celulas_forma(formato: str, largura: int, altura: int, origem_x: int, origem_y: int) -> list[Celula]:
	celulas: list[Celula] = []
	cx = (largura - 1) / 2.0
	cy = (altura - 1) / 2.0
	raio_x = largura / 2.0
	raio_y = altura / 2.0
	chanfro = max(1, min(largura, altura) // 4)

	for dy in range(altura):
		for dx in range(largura):
			incluir = True
			if formato == "circular":
				nx = (dx - cx) / max(raio_x, 0.5)
				ny = (dy - cy) / max(raio_y, 0.5)
				incluir = (nx * nx + ny * ny) <= 1.08
			elif formato == "octogonal":
				canto_no = dx + dy < chanfro
				canto_ne = (largura - 1 - dx) + dy < chanfro
				canto_so = dx + (altura - 1 - dy) < chanfro
				canto_se = (largura - 1 - dx) + (altura - 1 - dy) < chanfro
				incluir = not (canto_no or canto_ne or canto_so or canto_se)
			elif formato == "trapezoide":
				recuo = 1 if dy < altura // 3 else 0
				if largura >= 6 and dy < altura // 4:
					recuo = max(1, largura // 6)
				incluir = recuo <= dx < (largura - recuo)

			if incluir:
				celulas.append(Celula(x=origem_x + dx, y=origem_y + dy))

	if not celulas:
		for dy in range(altura):
			for dx in range(largura):
				celulas.append(Celula(x=origem_x + dx, y=origem_y + dy))
	return celulas


def associar_categoria_2024(proposito: str) -> str:
	texto = proposito.lower()
	if any(p in texto for p in ["cripta", "tumba", "embalsamamento", "funer"]):
		return "Criptas"
	if any(p in texto for p in ["cofre", "caixa-forte", "tesouro"]):
		return "Cofres"
	if any(p in texto for p in ["templo", "santuário", "capela", "altar", "oração"]):
		return "Santuários"
	if any(p in texto for p in ["guarda", "quartel", "quarteis", "armorial", "vigia", "prisão", "cela", "baia"]):
		return "Postos de Guarda"
	if any(p in texto for p in ["laboratório", "oficina", "biblioteca", "ferraria", "estudo", "adivinhação", "conjuração", "escritório"]):
		return "Áreas de Trabalho"
	if any(p in texto for p in ["cisterna", "poço", "veio", "mina", "caverna"]):
		return "Áreas Subterrâneas Naturais"
	return "Alojamentos"


def sortear_detalhes_porta(rng: random.Random, forcada_secreta: bool = False, forcada_normal: bool = False) -> dict:
	if forcada_secreta:
		return {
			"tipo_porta": "secreta",
			"descricao_porta": "Porta secreta",
			"secreta": True,
			"trancada": False,
		}
	if forcada_normal:
		entrada = rolar_tabela(TABELAS_GEOMETRIA["porta"], 18, rng)
	else:
		entrada = rolar_tabela(TABELAS_GEOMETRIA["porta"], 20, rng)
	return {
		"tipo_porta": entrada["tipo"],
		"descricao_porta": entrada["descricao"],
		"secreta": entrada["secreta"],
		"trancada": entrada["trancada"],
	}


def povoar_peca(tipo_masmorra: str, tipo_peca: str, rng: random.Random, proposito_forcado: str | None = None, notas_existentes: str = "") -> Povoamento:
	if tipo_peca == "corredor":
		estado = rolar_tabela(TABELAS_PROPOSITO["estado_atual_camara"], 20, rng)["descricao"]
		barulho = rolar_tabela(TABELAS_AMBIENTACAO["barulhos"], 100, rng)["descricao"]
		odor = rolar_tabela(TABELAS_AMBIENTACAO["odores"], 100, rng)["descricao"]
		caract = rolar_tabela(TABELAS_AMBIENTACAO["caracteristicas_gerais"], 100, rng)["descricao"]
		tem_algo = rng.random() < 0.3
		conteudo = "Passagem livre"
		perigo = ""
		armadilha = ""
		monstros_motivacao = ""
		if tem_algo:
			rolagem = rng.randint(1, 3)
			if rolagem == 1:
				conteudo = "Armadilha no corredor"
				gatilho = rolar_tabela(TABELAS_POVOAMENTO["armadilha_gatilho"], 6, rng)["descricao"]
				gravidade = rolar_tabela(TABELAS_POVOAMENTO["armadilha_gravidade"], 6, rng)["descricao"]
				efeito = rolar_tabela(TABELAS_POVOAMENTO["armadilha_efeito"], 100, rng)["descricao"]
				armadilha = f"{gravidade} — Gatilho: {gatilho}. Efeito: {efeito}"
			elif rolagem == 2:
				conteudo = "Perigo na passagem"
				perigo = rolar_tabela(TABELAS_POVOAMENTO["perigos"], 20, rng)["descricao"]
			else:
				conteudo = "Patrulha ou criatura errante"
				monstros_motivacao = rolar_tabela(TABELAS_POVOAMENTO["motivacao_monstro"], 20, rng)["descricao"]

		return Povoamento(
			proposito=proposito_forcado or "Corredor de ligação",
			categoria_2024="Passagem",
			estado_atual=estado,
			conteudo=conteudo,
			monstros_motivacao=monstros_motivacao,
			perigo=perigo,
			armadilha=armadilha,
			barulho=barulho,
			odor=odor,
			mobilia=caract,
			notas=notas_existentes,
		)

	tabela_tipo = TABELAS_PROPOSITO["tipos_masmorra"].get(
		tipo_masmorra,
		TABELAS_PROPOSITO["tipos_masmorra"]["geral"],
	)
	proposito = proposito_forcado or rolar_tabela(tabela_tipo["propositos"], tabela_tipo["dado"], rng)["descricao"]
	categoria_2024 = associar_categoria_2024(proposito)

	estado_entrada = rolar_tabela(TABELAS_PROPOSITO["estado_atual_camara"], 20, rng)
	estado_atual = estado_entrada["descricao"]
	if estado_entrada["min"] == 17:
		tabela_geral = TABELAS_PROPOSITO["tipos_masmorra"]["geral"]
		novo_uso = rolar_tabela(tabela_geral["propositos"], tabela_geral["dado"], rng)["descricao"]
		estado_atual = f"Convertida para outro uso: {novo_uso}"

	cont = rolar_tabela(TABELAS_POVOAMENTO["conteudo_camara"], 100, rng)
	monstros_motivacao = ""
	perigo = ""
	obstaculo = ""
	armadilha = ""
	arapuca = ""
	tesouro = ""

	if cont["tem_monstro"]:
		monstros_motivacao = rolar_tabela(TABELAS_POVOAMENTO["motivacao_monstro"], 20, rng)["descricao"]
	if cont["tem_perigo"]:
		perigo = rolar_tabela(TABELAS_POVOAMENTO["perigos"], 20, rng)["descricao"]
	if cont["tem_obstaculo"]:
		obstaculo = rolar_tabela(TABELAS_POVOAMENTO["obstaculos"], 20, rng)["descricao"]
	if cont["tem_armadilha"]:
		gatilho = rolar_tabela(TABELAS_POVOAMENTO["armadilha_gatilho"], 6, rng)["descricao"]
		gravidade = rolar_tabela(TABELAS_POVOAMENTO["armadilha_gravidade"], 6, rng)["descricao"]
		efeito = rolar_tabela(TABELAS_POVOAMENTO["armadilha_efeito"], 100, rng)["descricao"]
		armadilha = f"{gravidade} — Gatilho: {gatilho}. Efeito: {efeito}"
	if cont["tem_arapuca"]:
		obj = rolar_tabela(TABELAS_POVOAMENTO["arapuca_objeto"], 20, rng)["descricao"]
		ef = rolar_tabela(TABELAS_POVOAMENTO["arapuca_efeito"], 100, rng)["descricao"]
		arapuca = f"{obj}: {ef}"
	if cont["tem_tesouro"]:
		tesouro = rolar_tabela(TABELAS_POVOAMENTO["tesouros_sugestao"], 100, rng)["descricao"]

	barulho = rolar_tabela(TABELAS_AMBIENTACAO["barulhos"], 100, rng)["descricao"]
	odor = rolar_tabela(TABELAS_AMBIENTACAO["odores"], 100, rng)["descricao"]
	ar = rolar_tabela(TABELAS_AMBIENTACAO["ar"], 100, rng)["descricao"]

	itens_mobilia = [rolar_tabela(TABELAS_AMBIENTACAO["caracteristicas_gerais"], 100, rng)["descricao"]]
	if categoria_2024 == "Santuários":
		itens_mobilia.append(rolar_tabela(TABELAS_AMBIENTACAO["mobilias_religiosas"], 100, rng)["descricao"])
	elif categoria_2024 == "Áreas de Trabalho":
		itens_mobilia.append(rolar_tabela(TABELAS_AMBIENTACAO["mobilias_arcanas"], 100, rng)["descricao"])
		itens_mobilia.append(rolar_tabela(TABELAS_AMBIENTACAO["livros_pergaminhos"], 100, rng)["descricao"])
	else:
		itens_mobilia.append(rolar_tabela(TABELAS_AMBIENTACAO["mobilias_gerais"], 100, rng)["descricao"])
		itens_mobilia.append(rolar_tabela(TABELAS_AMBIENTACAO["utensilios"], 100, rng)["descricao"])

	return Povoamento(
		proposito=proposito,
		categoria_2024=categoria_2024,
		estado_atual=estado_atual,
		conteudo=cont["descricao"],
		monstros_motivacao=monstros_motivacao,
		perigo=perigo,
		obstaculo=obstaculo,
		armadilha=armadilha,
		arapuca=arapuca,
		tesouro=tesouro,
		barulho=f"{barulho} (Ar: {ar})",
		odor=odor,
		mobilia=", ".join(itens_mobilia),
		notas=notas_existentes,
	)


def escolher_celula_borda(celulas: list[Celula], direcao: str, saidas_existentes: list[Saida], ocupadas: dict[tuple[int, int], str]) -> tuple[int, int] | None:
	conjunto = {(c.x, c.y) for c in celulas}
	dx, dy = VETORES_DIRECAO[direcao]
	candidatas: list[tuple[int, int]] = []

	for cx, cy in conjunto:
		vx, vy = cx + dx, cy + dy
		if (vx, vy) not in conjunto:
			candidatas.append((cx, cy))

	if not candidatas:
		return None

	if direcao in ("N", "S"):
		candidatas.sort(key=lambda p: (p[0], p[1]))
	else:
		candidatas.sort(key=lambda p: (p[1], p[0]))

	usadas = {(s.x, s.y, s.direcao) for s in saidas_existentes}
	livres = [
		(cx, cy) for cx, cy in candidatas
		if (cx, cy, direcao) not in usadas and (cx + dx, cy + dy) not in ocupadas
	]
	pool = livres if livres else [c for c in candidatas if (c[0], c[1], direcao) not in usadas]
	if not pool:
		return None

	meio = len(pool) // 2
	return pool[meio]


def criar_saida_em_borda(peca_id: str, saidas_existentes: list[Saida], x: int, y: int, direcao: str, tipo_especifico: str, rng: random.Random) -> Saida:
	saida_id = gerar_id_saida(peca_id, saidas_existentes)
	if tipo_especifico == "corredor":
		return Saida(
			id=saida_id,
			x=x,
			y=y,
			direcao=direcao,
			tipo_porta="corredor",
			descricao_porta="Passagem aberta",
			secreta=False,
			trancada=False,
			aberta=True,
		)
	if tipo_especifico == "porta_secreta":
		detalhes = sortear_detalhes_porta(rng, forcada_secreta=True)
	else:
		detalhes = sortear_detalhes_porta(rng)
	return Saida(
		id=saida_id,
		x=x,
		y=y,
		direcao=direcao,
		tipo_porta=detalhes["tipo_porta"],
		descricao_porta=detalhes["descricao_porta"],
		secreta=detalhes["secreta"],
		trancada=detalhes["trancada"],
		aberta=True,
	)


def construir_area_inicial(peca_id: str, tipo_masmorra: str, rng: random.Random) -> Peca:
	area = rolar_tabela(TABELAS_GEOMETRIA["area_inicial"], 10, rng)
	larg = area["largura_quads"]
	alt = area["altura_quads"]
	formato = area["formato"]
	tipo_peca = area["tipo_peca"]

	if formato == "intersecao_t":
		celulas = [Celula(x=x, y=0) for x in range(-2, 4)] + [Celula(x=x, y=1) for x in range(-2, 4)]
		celulas += [Celula(x=0, y=y) for y in range(2, 4)] + [Celula(x=1, y=y) for y in range(2, 4)]
	elif formato == "cruzamento":
		cel_set: set[tuple[int, int]] = set()
		for x in range(0, 6):
			for y in (2, 3):
				cel_set.add((x, y))
		for y in range(0, 6):
			for x in (2, 3):
				cel_set.add((x, y))
		celulas = [Celula(x=x, y=y) for x, y in sorted(cel_set)]
	else:
		celulas = gerar_celulas_forma(formato, larg, alt, 0, 0)

	direcoes_base = ["N", "L", "O", "S"]
	saidas: list[Saida] = []
	for indice, tipo_saida in enumerate(area["saidas"]):
		direcao = direcoes_base[indice % 4]
		pos = escolher_celula_borda(celulas, direcao, saidas, {})
		if pos is not None:
			saidas.append(criar_saida_em_borda(peca_id, saidas, pos[0], pos[1], direcao, tipo_saida, rng))

	povoamento = povoar_peca(tipo_masmorra, tipo_peca, rng, proposito_forcado="Área Inicial da Masmorra")
	return Peca(
		id=peca_id,
		tipo=tipo_peca,
		formato=formato,
		descricao_geometria=area["descricao"],
		celulas=celulas,
		saidas=saidas,
		povoamento=povoamento,
	)


def criar_masmorra(nome: str, tipo_masmorra: str, seed: str | None = None) -> Masmorra:
	seed_final = normalizar_seed(seed)
	rng = criar_rng(seed_final, f"inicio:{tipo_masmorra}")
	peculiaridade = rolar_tabela(TABELAS_PROPOSITO["peculiaridades_masmorra"], 100, rng)["descricao"]
	conservacao = rolar_tabela(TABELAS_PROPOSITO["estado_conservacao"], 6, rng)["descricao"]
	masmorra_id = uuid.uuid4().hex[:10]
	peca_inicial = construir_area_inicial("S1", tipo_masmorra, rng)
	if peca_inicial.tipo == "corredor":
		peca_inicial.id = "C1"
		for s in peca_inicial.saidas:
			s.id = s.id.replace("S1_", "C1_")

	return Masmorra(
		id=masmorra_id,
		nome=nome.strip() or "Masmorra Sem Nome",
		tipo_masmorra=tipo_masmorra,
		seed=seed_final,
		passo_rng=0,
		peculiaridade=peculiaridade,
		estado_conservacao=conservacao,
		pecas=[peca_inicial],
	)


def encaixar_camara_no_grid(
	ocupadas: dict[tuple[int, int], str],
	entrada_x: int,
	entrada_y: int,
	dir_avanco: str,
	formato: str,
	larg: int,
	alt: int,
) -> list[Celula] | None:
	tamanhos_tentativa = [(larg, alt)]
	if larg != alt:
		tamanhos_tentativa.append((alt, larg))
	if max(larg, alt) > 4:
		tamanhos_tentativa.append((max(3, larg // 2), max(3, alt // 2)))
	tamanhos_tentativa.extend([(4, 4), (3, 3), (2, 2)])

	for w, h in tamanhos_tentativa:
		deslocamentos = [0, -1, 1, -2, 2, -3, 3]
		for desl in deslocamentos:
			if dir_avanco == "L":
				ox = entrada_x
				oy = entrada_y - (h // 2) + desl
			elif dir_avanco == "O":
				ox = entrada_x - w + 1
				oy = entrada_y - (h // 2) + desl
			elif dir_avanco == "S":
				ox = entrada_x - (w // 2) + desl
				oy = entrada_y
			else:
				ox = entrada_x - (w // 2) + desl
				oy = entrada_y - h + 1

			celulas = gerar_celulas_forma(formato, w, h, ox, oy)
			coords = {(c.x, c.y) for c in celulas}
			if (entrada_x, entrada_y) not in coords:
				continue
			if not any(coord in ocupadas for coord in coords):
				return celulas

	return None


def construir_camara_conectada(
	masmorra: Masmorra,
	peca_origem: Peca,
	saida_origem: Saida,
	entrada_x: int,
	entrada_y: int,
	ocupadas: dict[tuple[int, int], str],
	rng: random.Random,
	peca_id_forcado: str | None = None,
	notas_existentes: str = "",
) -> Peca | None:
	camara_def = rolar_tabela(TABELAS_GEOMETRIA["camara"], 20, rng)
	larg = camara_def["largura_quads"]
	alt = camara_def["altura_quads"]
	if saida_origem.direcao in ("L", "O") and rng.random() < 0.5:
		larg, alt = alt, larg

	celulas = encaixar_camara_no_grid(
		ocupadas,
		entrada_x,
		entrada_y,
		saida_origem.direcao,
		camara_def["formato"],
		larg,
		alt,
	)
	if celulas is None:
		return None

	nova_id = peca_id_forcado or proximo_id_peca(masmorra, "sala")
	dir_retorno = DIRECAO_OPOSTA[saida_origem.direcao]
	saida_retorno = Saida(
		id=f"{nova_id}_O1",
		x=entrada_x,
		y=entrada_y,
		direcao=dir_retorno,
		tipo_porta=saida_origem.tipo_porta,
		descricao_porta=saida_origem.descricao_porta,
		secreta=saida_origem.secreta,
		trancada=saida_origem.trancada,
		conectada_a=peca_origem.id,
		aberta=False,
	)
	saidas = [saida_retorno]

	qtd_def = rolar_tabela(TABELAS_GEOMETRIA["saidas_camara"], 20, rng)
	qtd_saidas = qtd_def["qtd_grande"] if camara_def["tamanho"] == "grande" else qtd_def["qtd_normal"]
	ocupadas_pos = dict(ocupadas)
	for c in celulas:
		ocupadas_pos[(c.x, c.y)] = nova_id

	mapa_lados = {
		"oposta": saida_origem.direcao,
		"esquerda": VIRAR_ESQUERDA[saida_origem.direcao],
		"direita": VIRAR_DIREITA[saida_origem.direcao],
		"mesma": dir_retorno,
	}

	for _ in range(qtd_saidas):
		loc = rolar_tabela(TABELAS_GEOMETRIA["localizacao_saida"], 20, rng)["lado"]
		dir_saida = mapa_lados[loc]
		pos = escolher_celula_borda(celulas, dir_saida, saidas, ocupadas_pos)
		if pos is None:
			continue
		tipo_s = rolar_tabela(TABELAS_GEOMETRIA["tipo_saida"], 20, rng)["tipo"]
		saidas.append(criar_saida_em_borda(nova_id, saidas, pos[0], pos[1], dir_saida, tipo_s, rng))

	povoamento = povoar_peca(masmorra.tipo_masmorra, "sala", rng, notas_existentes=notas_existentes)
	return Peca(
		id=nova_id,
		tipo="sala",
		formato=camara_def["formato"],
		descricao_geometria=camara_def["descricao"],
		celulas=celulas,
		saidas=saidas,
		povoamento=povoamento,
	)


def avancar_corredor_linha(
	entrada_x: int,
	entrada_y: int,
	direcao: str,
	comprimento: int,
	largura: int,
	ocupadas: dict[tuple[int, int], str],
) -> tuple[list[Celula], tuple[int, int] | None, str | None]:
	dx, dy = VETORES_DIRECAO[direcao]
	lx, ly = VETORES_DIRECAO[VIRAR_DIREITA[direcao]]
	celulas: list[Celula] = []
	ultima_ponta = (entrada_x, entrada_y)
	peca_encontrada: str | None = None

	for passo in range(comprimento):
		faixa: list[Celula] = []
		bloqueado = False
		for w in range(largura):
			px = entrada_x + dx * passo + lx * w
			py = entrada_y + dy * passo + ly * w
			if (px, py) in ocupadas:
				bloqueado = True
				peca_encontrada = ocupadas[(px, py)]
				break
			faixa.append(Celula(x=px, y=py))
		if bloqueado:
			break
		celulas.extend(faixa)
		ultima_ponta = (entrada_x + dx * passo, entrada_y + dy * passo)

	return celulas, ultima_ponta if celulas else None, peca_encontrada


def construir_corredor_conectado(
	masmorra: Masmorra,
	peca_origem: Peca,
	saida_origem: Saida,
	entrada_x: int,
	entrada_y: int,
	ocupadas: dict[tuple[int, int], str],
	rng: random.Random,
	detalhe_forcado: dict | None = None,
	peca_id_forcado: str | None = None,
	notas_existentes: str = "",
) -> Peca | None:
	passagem_def = detalhe_forcado or rolar_tabela(TABELAS_GEOMETRIA["passagem"], 20, rng)
	larg_def = rolar_tabela(TABELAS_GEOMETRIA["largura_passagem"], 12, rng)
	largura = min(2, larg_def["largura_quads"])
	tipo_pass = passagem_def["tipo"]
	comprimento = max(2, passagem_def.get("comprimento_quads", 4))

	celulas, ponta, colisao_id = avancar_corredor_linha(
		entrada_x,
		entrada_y,
		saida_origem.direcao,
		comprimento,
		largura,
		ocupadas,
	)
	if not celulas and largura > 1:
		largura = 1
		celulas, ponta, colisao_id = avancar_corredor_linha(
			entrada_x,
			entrada_y,
			saida_origem.direcao,
			comprimento,
			1,
			ocupadas,
		)
	if not celulas or ponta is None:
		return None

	nova_id = peca_id_forcado or proximo_id_peca(masmorra, "corredor")
	dir_avanco = saida_origem.direcao
	dir_retorno = DIRECAO_OPOSTA[dir_avanco]

	saidas: list[Saida] = [
		Saida(
			id=f"{nova_id}_O1",
			x=entrada_x,
			y=entrada_y,
			direcao=dir_retorno,
			tipo_porta=saida_origem.tipo_porta,
			descricao_porta=saida_origem.descricao_porta,
			secreta=saida_origem.secreta,
			trancada=saida_origem.trancada,
			conectada_a=peca_origem.id,
			aberta=False,
		)
	]

	coords_atuais = {(c.x, c.y) for c in celulas}
	ocupadas_com_corredor = dict(ocupadas)
	for coord in coords_atuais:
		ocupadas_com_corredor[coord] = nova_id

	if tipo_pass in ("curva_dir", "curva_esq"):
		dir_dobra = VIRAR_DIREITA[dir_avanco] if tipo_pass == "curva_dir" else VIRAR_ESQUERDA[dir_avanco]
		dx_d, dy_d = VETORES_DIRECAO[dir_dobra]
		dobra_x = ponta[0] + dx_d
		dobra_y = ponta[1] + dy_d
		cel_dobra, ponta_dobra, _ = avancar_corredor_linha(
			dobra_x,
			dobra_y,
			dir_dobra,
			passagem_def.get("dobra_quads", 2),
			1,
			ocupadas_com_corredor,
		)
		if cel_dobra and ponta_dobra is not None:
			celulas.extend(cel_dobra)
			saidas.append(criar_saida_em_borda(nova_id, saidas, ponta_dobra[0], ponta_dobra[1], dir_dobra, "corredor", rng))
		else:
			saidas.append(criar_saida_em_borda(nova_id, saidas, ponta[0], ponta[1], dir_avanco, "corredor", rng))
	elif tipo_pass == "intersecao_t":
		for dir_lado in (VIRAR_ESQUERDA[dir_avanco], VIRAR_DIREITA[dir_avanco]):
			dx_l, dy_l = VETORES_DIRECAO[dir_lado]
			cel_l, ponta_l, _ = avancar_corredor_linha(
				ponta[0] + dx_l,
				ponta[1] + dy_l,
				dir_lado,
				2,
				1,
				ocupadas_com_corredor,
			)
			if cel_l and ponta_l is not None:
				celulas.extend(cel_l)
				for c in cel_l:
					ocupadas_com_corredor[(c.x, c.y)] = nova_id
				saidas.append(criar_saida_em_borda(nova_id, saidas, ponta_l[0], ponta_l[1], dir_lado, "corredor", rng))
	else:
		ram = passagem_def.get("ramificacao")
		if ram:
			dir_ram = VIRAR_DIREITA[dir_avanco] if ram["lado"] == "dir" else VIRAR_ESQUERDA[dir_avanco]
			pos_ram = escolher_celula_borda(celulas, dir_ram, saidas, ocupadas_com_corredor)
			if pos_ram is not None:
				saidas.append(criar_saida_em_borda(nova_id, saidas, pos_ram[0], pos_ram[1], dir_ram, ram["tipo"], rng))

		if passagem_def.get("continua_frente", False) and colisao_id is None:
			saidas.append(criar_saida_em_borda(nova_id, saidas, ponta[0], ponta[1], dir_avanco, "corredor", rng))
		elif passagem_def.get("porta_final", False) and colisao_id is None:
			saidas.append(criar_saida_em_borda(nova_id, saidas, ponta[0], ponta[1], dir_avanco, "porta", rng))
		elif tipo_pass == "beco_sem_saida" and rng.random() < passagem_def.get("chance_secreta", 0.0):
			saidas.append(criar_saida_em_borda(nova_id, saidas, ponta[0], ponta[1], dir_avanco, "porta_secreta", rng))

	celulas_unicas: list[Celula] = []
	vistos: set[tuple[int, int]] = set()
	for c in celulas:
		if (c.x, c.y) not in vistos:
			vistos.add((c.x, c.y))
			celulas_unicas.append(c)

	povoamento = povoar_peca(masmorra.tipo_masmorra, "corredor", rng, notas_existentes=notas_existentes)
	return Peca(
		id=nova_id,
		tipo="corredor",
		formato=tipo_pass,
		descricao_geometria=f"{passagem_def['descricao']} (Largura {larg_def['descricao']})",
		celulas=celulas_unicas,
		saidas=saidas,
		povoamento=povoamento,
	)


def construir_escada_conectada(
	masmorra: Masmorra,
	peca_origem: Peca,
	saida_origem: Saida,
	entrada_x: int,
	entrada_y: int,
	ocupadas: dict[tuple[int, int], str],
	rng: random.Random,
	peca_id_forcado: str | None = None,
	notas_existentes: str = "",
) -> Peca | None:
	escada_def = rolar_tabela(TABELAS_GEOMETRIA["escadas"], 20, rng)
	celulas, ponta, _ = avancar_corredor_linha(entrada_x, entrada_y, saida_origem.direcao, 2, 1, ocupadas)
	if not celulas or ponta is None:
		return None

	nova_id = peca_id_forcado or proximo_id_peca(masmorra, "escada")
	dir_retorno = DIRECAO_OPOSTA[saida_origem.direcao]
	saidas = [
		Saida(
			id=f"{nova_id}_O1",
			x=entrada_x,
			y=entrada_y,
			direcao=dir_retorno,
			tipo_porta=saida_origem.tipo_porta,
			descricao_porta=saida_origem.descricao_porta,
			secreta=saida_origem.secreta,
			trancada=saida_origem.trancada,
			conectada_a=peca_origem.id,
			aberta=False,
		)
	]

	if escada_def["destino"] in ("camara", "passagem"):
		saidas.append(
			criar_saida_em_borda(nova_id, saidas, ponta[0], ponta[1], saida_origem.direcao, "corredor", rng)
		)

	povoamento = Povoamento(
		proposito=f"Escadaria / Acesso Vertical: {escada_def['descricao']}",
		categoria_2024="Escadas",
		estado_atual=rolar_tabela(TABELAS_PROPOSITO["estado_atual_camara"], 20, rng)["descricao"],
		conteudo="Passagem vertical entre níveis",
		barulho=rolar_tabela(TABELAS_AMBIENTACAO["barulhos"], 100, rng)["descricao"],
		odor=rolar_tabela(TABELAS_AMBIENTACAO["odores"], 100, rng)["descricao"],
		mobilia="Degraus gastos pelo tempo",
		notas=notas_existentes,
	)

	return Peca(
		id=nova_id,
		tipo="escada",
		formato="escada",
		descricao_geometria=escada_def["descricao"],
		celulas=celulas,
		saidas=saidas,
		povoamento=povoamento,
	)


def conectar_em_loop(peca_origem: Peca, saida_origem: Saida, peca_alvo: Peca, entrada_x: int, entrada_y: int) -> None:
	saida_origem.aberta = False
	saida_origem.conectada_a = peca_alvo.id
	dir_oposta = DIRECAO_OPOSTA[saida_origem.direcao]
	for s in peca_alvo.saidas:
		if s.x == entrada_x and s.y == entrada_y and s.direcao == dir_oposta:
			s.aberta = False
			s.conectada_a = peca_origem.id
			return
	peca_alvo.saidas.append(
		Saida(
			id=gerar_id_saida(peca_alvo.id, peca_alvo.saidas),
			x=entrada_x,
			y=entrada_y,
			direcao=dir_oposta,
			tipo_porta=saida_origem.tipo_porta,
			descricao_porta=saida_origem.descricao_porta,
			secreta=saida_origem.secreta,
			trancada=saida_origem.trancada,
			conectada_a=peca_origem.id,
			aberta=False,
		)
	)


def expandir_saida(masmorra: Masmorra, peca_id: str, saida_id: str) -> tuple[Masmorra, Peca | None]:
	peca_origem = obter_peca(masmorra, peca_id)
	if peca_origem is None:
		return masmorra, None

	saida_origem = next((s for s in peca_origem.saidas if s.id == saida_id), None)
	if saida_origem is None or not saida_origem.aberta:
		return masmorra, None

	seed_efetiva = obter_seed_efetiva(masmorra)
	rng = criar_rng(seed_efetiva, f"expandir:{peca_id}:{saida_id}")

	dx, dy = VETORES_DIRECAO[saida_origem.direcao]
	entrada_x = saida_origem.x + dx
	entrada_y = saida_origem.y + dy
	ocupadas = conjunto_celulas_ocupadas(masmorra)

	if (entrada_x, entrada_y) in ocupadas:
		alvo_id = ocupadas[(entrada_x, entrada_y)]
		peca_alvo = obter_peca(masmorra, alvo_id)
		if peca_alvo is not None:
			conectar_em_loop(peca_origem, saida_origem, peca_alvo, entrada_x, entrada_y)
		else:
			saida_origem.aberta = False
		return masmorra, None

	nova_peca: Peca | None = None
	if saida_origem.tipo_porta != "corredor":
		atras = rolar_tabela(TABELAS_GEOMETRIA["atras_porta"], 20, rng)
		res = atras["resultado"]
		if res == "camara":
			nova_peca = construir_camara_conectada(masmorra, peca_origem, saida_origem, entrada_x, entrada_y, ocupadas, rng)
		elif res == "escada":
			nova_peca = construir_escada_conectada(masmorra, peca_origem, saida_origem, entrada_x, entrada_y, ocupadas, rng)
		elif res == "porta_falsa_armadilha":
			saida_origem.aberta = False
			saida_origem.descricao_porta = f"{saida_origem.descricao_porta} (Porta falsa com armadilha)"
			return masmorra, None
		else:
			detalhe = {
				"tipo": "intersecao_t" if res == "intersecao_t" else "reta",
				"comprimento_quads": 2 if res == "intersecao_t" else 4,
				"continua_frente": res != "intersecao_t",
				"descricao": atras["descricao"],
			}
			nova_peca = construir_corredor_conectado(
				masmorra,
				peca_origem,
				saida_origem,
				entrada_x,
				entrada_y,
				ocupadas,
				rng,
				detalhe_forcado=detalhe,
			)
	else:
		passagem_def = rolar_tabela(TABELAS_GEOMETRIA["passagem"], 20, rng)
		if passagem_def["tipo"] == "camara":
			nova_peca = construir_camara_conectada(masmorra, peca_origem, saida_origem, entrada_x, entrada_y, ocupadas, rng)
		elif passagem_def["tipo"] == "escada":
			nova_peca = construir_escada_conectada(masmorra, peca_origem, saida_origem, entrada_x, entrada_y, ocupadas, rng)
		else:
			nova_peca = construir_corredor_conectado(
				masmorra,
				peca_origem,
				saida_origem,
				entrada_x,
				entrada_y,
				ocupadas,
				rng,
				detalhe_forcado=passagem_def,
			)

	if nova_peca is None:
		saida_origem.aberta = False
		saida_origem.descricao_porta = f"{saida_origem.descricao_porta} (Bloqueada por desmoronamento)"
		return masmorra, None

	saida_origem.aberta = False
	saida_origem.conectada_a = nova_peca.id
	masmorra.pecas.append(nova_peca)
	return masmorra, nova_peca


def desconectar_referencias_peca(masmorra: Masmorra, peca_id: str) -> None:
	for outra in masmorra.pecas:
		if outra.id == peca_id:
			continue
		for s in outra.saidas:
			if s.conectada_a == peca_id:
				s.conectada_a = None
				s.aberta = True


def remover_peca(masmorra: Masmorra, peca_id: str) -> Masmorra:
	if len(masmorra.pecas) <= 1 and masmorra.pecas and masmorra.pecas[0].id == peca_id:
		return masmorra
	desconectar_referencias_peca(masmorra, peca_id)
	masmorra.pecas = [p for p in masmorra.pecas if p.id != peca_id]
	return masmorra


def rerolar_peca(masmorra: Masmorra, peca_id: str, escopo: str = "tudo") -> Masmorra:
	peca = obter_peca(masmorra, peca_id)
	if peca is None:
		return masmorra

	seed_efetiva = obter_seed_efetiva(masmorra)
	masmorra.passo_rng += 1
	rng = criar_rng(seed_efetiva, f"rerolar:{peca_id}:{escopo}:{masmorra.passo_rng}")

	notas_atuais = peca.povoamento.notas
	if escopo == "povoamento":
		peca.povoamento = povoar_peca(masmorra.tipo_masmorra, peca.tipo, rng, notas_existentes=notas_atuais)
		return masmorra

	if len(masmorra.pecas) == 1 and masmorra.pecas[0].id == peca_id:
		nova = construir_area_inicial(peca.id, masmorra.tipo_masmorra, rng)
		if escopo == "geometria":
			nova.povoamento = peca.povoamento
		else:
			nova.povoamento.notas = notas_atuais
		masmorra.pecas[0] = nova
		return masmorra

	entrada_conectada = next((s for s in peca.saidas if s.conectada_a), None)
	if entrada_conectada is None or entrada_conectada.conectada_a is None:
		if escopo == "tudo":
			peca.povoamento = povoar_peca(masmorra.tipo_masmorra, peca.tipo, rng, notas_existentes=notas_atuais)
		return masmorra

	peca_pai = obter_peca(masmorra, entrada_conectada.conectada_a)
	if peca_pai is None:
		return masmorra

	saida_pai = next((s for s in peca_pai.saidas if s.conectada_a == peca.id), None)
	if saida_pai is None:
		return masmorra

	for outra in masmorra.pecas:
		if outra.id in (peca.id, peca_pai.id):
			continue
		for s in outra.saidas:
			if s.conectada_a == peca.id:
				s.conectada_a = None
				s.aberta = True

	ocupadas = conjunto_celulas_ocupadas(masmorra, ignorar_peca_id=peca.id)
	dx, dy = VETORES_DIRECAO[saida_pai.direcao]
	entrada_x = saida_pai.x + dx
	entrada_y = saida_pai.y + dy

	if peca.tipo == "sala":
		nova = construir_camara_conectada(
			masmorra,
			peca_pai,
			saida_pai,
			entrada_x,
			entrada_y,
			ocupadas,
			rng,
			peca_id_forcado=peca.id,
			notas_existentes=notas_atuais,
		)
	elif peca.tipo == "escada":
		nova = construir_escada_conectada(
			masmorra,
			peca_pai,
			saida_pai,
			entrada_x,
			entrada_y,
			ocupadas,
			rng,
			peca_id_forcado=peca.id,
			notas_existentes=notas_atuais,
		)
	else:
		nova = construir_corredor_conectado(
			masmorra,
			peca_pai,
			saida_pai,
			entrada_x,
			entrada_y,
			ocupadas,
			rng,
			peca_id_forcado=peca.id,
			notas_existentes=notas_atuais,
		)

	if nova is not None:
		if escopo == "geometria":
			nova.povoamento = peca.povoamento
		indice = next(i for i, p in enumerate(masmorra.pecas) if p.id == peca.id)
		masmorra.pecas[indice] = nova

	return masmorra


def gerar_masmorra_completa(masmorra: Masmorra, total_salas: int = 10) -> Masmorra:
	seed_efetiva = obter_seed_efetiva(masmorra)
	masmorra.passo_rng += 1
	rng_escolha = criar_rng(seed_efetiva, f"completa:{total_salas}:{masmorra.passo_rng}")

	iteracoes = 0
	limite_iteracoes = total_salas * 12

	while iteracoes < limite_iteracoes:
		qtd_salas = sum(1 for p in masmorra.pecas if p.tipo == "sala")
		if qtd_salas >= total_salas:
			break

		saidas_abertas: list[tuple[str, str]] = []
		for peca in masmorra.pecas:
			for saida in peca.saidas:
				if saida.aberta:
					saidas_abertas.append((peca.id, saida.id))

		if not saidas_abertas:
			break

		peca_id, saida_id = rng_escolha.choice(saidas_abertas)
		expandir_saida(masmorra, peca_id, saida_id)
		iteracoes += 1

	return masmorra
