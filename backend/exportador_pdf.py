import math
import pymupdf

from backend.modelos import Celula, ConfigExportacaoPDF, Masmorra, Peca, Saida


MM_PARA_PT = 72.0 / 25.4
LARGURA_A4_MM = 210.0
ALTURA_A4_MM = 297.0
MARGEM_MM = 5.0
AREA_UTIL_LARG_MM = LARGURA_A4_MM - 2 * MARGEM_MM
RODAPE_MM = 7.0
AREA_UTIL_ALT_MM = ALTURA_A4_MM - 2 * MARGEM_MM - RODAPE_MM
ESPACO_ENTRE_PECAS_MM = 7.5

ROTACIONAR_HORARIO = {"N": "L", "L": "S", "S": "O", "O": "N"}


def mm_pt(valor_mm: float) -> float:
	return valor_mm * MM_PARA_PT


def limpar_texto_pdf(texto: str) -> str:
	return texto.replace("—", "-").replace("–", "-").replace("→", "->")


def limites_celulas(celulas: list[Celula]) -> tuple[int, int, int, int]:
	xs = [c.x for c in celulas]
	ys = [c.y for c in celulas]
	return min(xs), min(ys), max(xs), max(ys)


def normalizar_peca(peca: Peca, rotacionada: bool) -> dict:
	min_x, min_y, max_x, max_y = limites_celulas(peca.celulas)
	larg = max_x - min_x + 1
	alt = max_y - min_y + 1

	celulas_norm: set[tuple[int, int]] = set()
	for c in peca.celulas:
		dx = c.x - min_x
		dy = c.y - min_y
		if rotacionada:
			celulas_norm.add((alt - 1 - dy, dx))
		else:
			celulas_norm.add((dx, dy))

	saidas_norm: dict[tuple[int, int, str], Saida] = {}
	for s in peca.saidas:
		dx = s.x - min_x
		dy = s.y - min_y
		if rotacionada:
			nx = alt - 1 - dy
			ny = dx
			ndir = ROTACIONAR_HORARIO[s.direcao]
		else:
			nx = dx
			ny = dy
			ndir = s.direcao
		saidas_norm[(nx, ny, ndir)] = s

	if rotacionada:
		larg, alt = alt, larg

	return {
		"peca": peca,
		"larg_quads": larg,
		"alt_quads": alt,
		"celulas": celulas_norm,
		"saidas": saidas_norm,
		"rotacionada": rotacionada,
	}


def desenhar_celula_peca(
	pagina: pymupdf.Page,
	info: dict,
	gx: int,
	gy: int,
	x0_mm: float,
	y0_mm: float,
	q_mm: float,
	ocultar_secretas: bool,
	offset_x: int = 0,
	offset_y: int = 0,
	mostrar_etiquetas_externas: bool = True,
	escala_traco: float = 1.0,
) -> None:
	px = x0_mm + (gx - offset_x) * q_mm
	py = y0_mm + (gy - offset_y) * q_mm
	rect = pymupdf.Rect(mm_pt(px), mm_pt(py), mm_pt(px + q_mm), mm_pt(py + q_mm))

	peca: Peca = info["peca"]
	cor_fundo = (0.98, 0.98, 0.98)
	if not ocultar_secretas:
		if peca.tipo == "corredor":
			cor_fundo = (0.91, 0.91, 0.91)
		elif peca.tipo == "escada":
			cor_fundo = (0.95, 0.92, 0.84)
		else:
			cor_fundo = (0.96, 0.96, 0.96)

	pagina.draw_rect(
		rect,
		color=(0.72, 0.72, 0.72),
		fill=cor_fundo,
		width=0.35 * escala_traco,
	)

	if peca.tipo == "escada":
		for i in range(1, 4):
			ry = py + (q_mm * i / 4.0)
			pagina.draw_line(
				pymupdf.Point(mm_pt(px + q_mm * 0.15), mm_pt(ry)),
				pymupdf.Point(mm_pt(px + q_mm * 0.85), mm_pt(ry)),
				color=(0.45, 0.45, 0.45),
				width=0.6 * escala_traco,
			)

	celulas = info["celulas"]
	saidas: dict[tuple[int, int, str], Saida] = info["saidas"]

	bordas = {
		"N": (0, -1, (px, py), (px + q_mm, py), (0.0, -1.0)),
		"S": (0, 1, (px, py + q_mm), (px + q_mm, py + q_mm), (0.0, 1.0)),
		"O": (-1, 0, (px, py), (px, py + q_mm), (-1.0, 0.0)),
		"L": (1, 0, (px + q_mm, py), (px + q_mm, py + q_mm), (1.0, 0.0)),
	}

	larg_parede = 2.0 * escala_traco
	for direcao, (vx, vy, p1, p2, normal) in bordas.items():
		if (gx + vx, gy + vy) in celulas:
			continue

		saida = saidas.get((gx, gy, direcao))
		revelar_como_parede = saida is None or (ocultar_secretas and saida.secreta)

		if revelar_como_parede:
			pagina.draw_line(
				pymupdf.Point(mm_pt(p1[0]), mm_pt(p1[1])),
				pymupdf.Point(mm_pt(p2[0]), mm_pt(p2[1])),
				color=(0.05, 0.05, 0.05),
				width=larg_parede,
			)
			continue

		x1, y1 = p1
		x2, y2 = p2
		mx1 = x1 + (x2 - x1) * 0.22
		my1 = y1 + (y2 - y1) * 0.22
		mx2 = x1 + (x2 - x1) * 0.78
		my2 = y1 + (y2 - y1) * 0.78

		pagina.draw_line(
			pymupdf.Point(mm_pt(x1), mm_pt(y1)),
			pymupdf.Point(mm_pt(mx1), mm_pt(my1)),
			color=(0.05, 0.05, 0.05),
			width=larg_parede,
		)
		pagina.draw_line(
			pymupdf.Point(mm_pt(mx2), mm_pt(my2)),
			pymupdf.Point(mm_pt(x2), mm_pt(y2)),
			color=(0.05, 0.05, 0.05),
			width=larg_parede,
		)

		if saida.tipo_porta != "corredor":
			esp_porta = max(1.2, q_mm * 0.14)
			cx_m = (x1 + x2) / 2.0
			cy_m = (y1 + y2) / 2.0
			if direcao in ("N", "S"):
				pr = pymupdf.Rect(
					mm_pt(mx1),
					mm_pt(cy_m - esp_porta / 2.0),
					mm_pt(mx2),
					mm_pt(cy_m + esp_porta / 2.0),
				)
			else:
				pr = pymupdf.Rect(
					mm_pt(cx_m - esp_porta / 2.0),
					mm_pt(my1),
					mm_pt(cx_m + esp_porta / 2.0),
					mm_pt(my2),
				)

			cor_borda_porta = (0.1, 0.1, 0.1)
			cor_preenchimento = (1.0, 1.0, 1.0)
			if not ocultar_secretas and saida.secreta:
				cor_borda_porta = (0.75, 0.1, 0.1)
				cor_preenchimento = (1.0, 0.88, 0.88)
			elif not ocultar_secretas and saida.trancada:
				cor_borda_porta = (0.55, 0.35, 0.0)
				cor_preenchimento = (1.0, 0.94, 0.8)

			pagina.draw_rect(pr, color=cor_borda_porta, fill=cor_preenchimento, width=0.9 * escala_traco)

			if not ocultar_secretas and (saida.secreta or saida.trancada):
				sigla = "S" if saida.secreta else "T"
				tam_sigla = max(4.5, min(7.0, q_mm * 0.38))
				pagina.insert_text(
					pymupdf.Point(mm_pt(cx_m) - tam_sigla * 0.32, mm_pt(cy_m) + tam_sigla * 0.35),
					sigla,
					fontsize=tam_sigla,
					fontname="hebo",
					color=cor_borda_porta,
				)

		if mostrar_etiquetas_externas and saida.conectada_a:
			etiqueta = f"-> {saida.conectada_a}"
			cx_e = (x1 + x2) / 2.0
			cy_e = (y1 + y2) / 2.0
			nx_v, ny_v = normal
			ex = cx_e + nx_v * 3.0
			ey = cy_e + ny_v * 3.0
			fora_margem = (
				ex < MARGEM_MM + 1.0
				or ex > LARGURA_A4_MM - MARGEM_MM - 5.0
				or ey < MARGEM_MM + 1.5
				or ey > ALTURA_A4_MM - MARGEM_MM - RODAPE_MM - 1.5
			)
			if fora_margem:
				ex = cx_e - nx_v * min(4.5, q_mm * 0.35)
				ey = cy_e - ny_v * min(4.5, q_mm * 0.35)

			pagina.insert_text(
				pymupdf.Point(mm_pt(ex) - 8.0, mm_pt(ey) + 2.2),
				etiqueta,
				fontsize=6.5,
				fontname="hebo",
				color=(0.25, 0.25, 0.25),
			)


def celula_central_peca(celulas: set[tuple[int, int]]) -> tuple[int, int]:
	xs = [c[0] for c in celulas]
	ys = [c[1] for c in celulas]
	mx = sum(xs) / len(xs)
	my = sum(ys) / len(ys)
	return min(celulas, key=lambda c: (c[0] - mx) ** 2 + (c[1] - my) ** 2)


def desenhar_rotulo_peca(
	pagina: pymupdf.Page,
	peca: Peca,
	celulas_slice: set[tuple[int, int]],
	x0_mm: float,
	y0_mm: float,
	q_mm: float,
	offset_x: int = 0,
	offset_y: int = 0,
	sufixo: str = "",
	tamanho_fonte: float | None = None,
) -> None:
	if not celulas_slice:
		return
	cx, cy = celula_central_peca(celulas_slice)
	px = x0_mm + (cx - offset_x + 0.5) * q_mm
	py = y0_mm + (cy - offset_y + 0.5) * q_mm
	texto = f"{peca.id}{sufixo}"
	fonte = tamanho_fonte or max(7.0, min(14.0, q_mm * 0.48))
	larg_estimada = len(texto) * fonte * 0.58
	pagina.insert_text(
		pymupdf.Point(mm_pt(px) - larg_estimada / 2.0, mm_pt(py) + fonte * 0.35),
		texto,
		fontsize=fonte,
		fontname="hebo",
		color=(0.35, 0.35, 0.35),
	)


def empacotar_pecas_unitarias(pecas_info: list[dict], q_mm: float) -> list[dict]:
	def chave_ordem(item: dict) -> float:
		return max(item["larg_quads"], item["alt_quads"]) * (item["larg_quads"] * item["alt_quads"])

	ordenadas = sorted(pecas_info, key=chave_ordem, reverse=True)
	paginas: list[dict] = []

	for info in ordenadas:
		w0 = info["larg_quads"] * q_mm
		h0 = info["alt_quads"] * q_mm
		info_rot = normalizar_peca(info["peca"], not info["rotacionada"])
		w1 = info_rot["larg_quads"] * q_mm
		h1 = info_rot["alt_quads"] * q_mm

		colocada = False
		for pag in paginas:
			if colocada:
				break
			for indice_ret, (rx, ry, rw, rh) in enumerate(pag["livres"]):
				candidatos = []
				pad0_w = w0 + (ESPACO_ENTRE_PECAS_MM if w0 + ESPACO_ENTRE_PECAS_MM <= rw else 0.0)
				pad0_h = h0 + (ESPACO_ENTRE_PECAS_MM if h0 + ESPACO_ENTRE_PECAS_MM <= rh else 0.0)
				if w0 <= rw + 0.01 and h0 <= rh + 0.01:
					candidatos.append((info, w0, h0, pad0_w, pad0_h))

				pad1_w = w1 + (ESPACO_ENTRE_PECAS_MM if w1 + ESPACO_ENTRE_PECAS_MM <= rw else 0.0)
				pad1_h = h1 + (ESPACO_ENTRE_PECAS_MM if h1 + ESPACO_ENTRE_PECAS_MM <= rh else 0.0)
				if w1 <= rw + 0.01 and h1 <= rh + 0.01:
					candidatos.append((info_rot, w1, h1, pad1_w, pad1_h))

				if not candidatos:
					continue

				escolhido, bw, bh, pw, ph = min(candidatos, key=lambda c: (c[2], c[1]))
				pag["itens"].append({"info": escolhido, "x_mm": MARGEM_MM + rx, "y_mm": MARGEM_MM + ry})
				pag["livres"].pop(indice_ret)

				sobra_dir = rw - pw
				sobra_baixo = rh - ph
				if sobra_dir > 12.0 and ph > 12.0:
					pag["livres"].append((rx + pw, ry, sobra_dir, ph))
				if sobra_baixo > 12.0:
					pag["livres"].append((rx, ry + ph, rw, sobra_baixo))
				pag["livres"].sort(key=lambda r: (r[1], r[0]))
				colocada = True
				break

		if not colocada:
			if w0 <= AREA_UTIL_LARG_MM + 0.01 and h0 <= AREA_UTIL_ALT_MM + 0.01:
				escolhido, bw, bh = info, w0, h0
			else:
				escolhido, bw, bh = info_rot, w1, h1
			pw = min(AREA_UTIL_LARG_MM, bw + ESPACO_ENTRE_PECAS_MM)
			ph = min(AREA_UTIL_ALT_MM, bh + ESPACO_ENTRE_PECAS_MM)
			livres = []
			if AREA_UTIL_LARG_MM - pw > 12.0:
				livres.append((pw, 0.0, AREA_UTIL_LARG_MM - pw, ph))
			if AREA_UTIL_ALT_MM - ph > 12.0:
				livres.append((0.0, ph, AREA_UTIL_LARG_MM, AREA_UTIL_ALT_MM - ph))
			paginas.append({
				"itens": [{"info": escolhido, "x_mm": MARGEM_MM, "y_mm": MARGEM_MM}],
				"livres": livres,
			})

	return paginas


def desenhar_rodape_pagina(pagina: pymupdf.Page, masmorra: Masmorra, rotulo_pecas: str, q_mm: float, numero_pag: int, total_pags: int) -> None:
	y_rodape = ALTURA_A4_MM - MARGEM_MM - 1.5
	escala_cm = q_mm / 10.0
	texto_esq = f"{masmorra.nome} | Peças: {rotulo_pecas}"
	texto_dir = f"Escala: 1 quad = {escala_cm:.2f} cm (1,5 m) | Pág. {numero_pag}/{total_pags}"
	pagina.draw_line(
		pymupdf.Point(mm_pt(MARGEM_MM), mm_pt(y_rodape - 4.0)),
		pymupdf.Point(mm_pt(LARGURA_A4_MM - MARGEM_MM), mm_pt(y_rodape - 4.0)),
		color=(0.75, 0.75, 0.75),
		width=0.5,
	)
	pagina.insert_text(
		pymupdf.Point(mm_pt(MARGEM_MM), mm_pt(y_rodape)),
		texto_esq[:95],
		fontsize=7.5,
		fontname="helv",
		color=(0.3, 0.3, 0.3),
	)
	pagina.insert_text(
		pymupdf.Point(mm_pt(LARGURA_A4_MM - MARGEM_MM - 82.0), mm_pt(y_rodape)),
		texto_dir,
		fontsize=7.5,
		fontname="helv",
		color=(0.3, 0.3, 0.3),
	)


def fatiar_peca_grande(peca: Peca, q_mm: float) -> list[dict]:
	cabecalho_fatia_mm = 8.0
	alt_disponivel_mm = AREA_UTIL_ALT_MM - cabecalho_fatia_mm
	max_qx = max(1, int(AREA_UTIL_LARG_MM // q_mm))
	max_qy = max(1, int(alt_disponivel_mm // q_mm))

	opcoes = []
	for rot in (False, True):
		info = normalizar_peca(peca, rot)
		nx = math.ceil(info["larg_quads"] / max_qx)
		ny = math.ceil(info["alt_quads"] / max_qy)
		opcoes.append((nx * ny, nx, ny, info))

	_, nx, ny, info = min(opcoes, key=lambda o: o[0])
	fatias: list[dict] = []

	for iy in range(ny):
		for ix in range(nx):
			ox = ix * max_qx
			oy = iy * max_qy
			fx = min(ox + max_qx, info["larg_quads"])
			fy = min(oy + max_qy, info["alt_quads"])
			celulas_fatia = {
				(cx, cy) for (cx, cy) in info["celulas"]
				if ox <= cx < fx and oy <= cy < fy
			}
			if not celulas_fatia:
				continue
			fatias.append({
				"info": info,
				"ox": ox,
				"oy": oy,
				"fx": fx,
				"fy": fy,
				"ix": ix,
				"iy": iy,
				"nx": nx,
				"ny": ny,
				"celulas_fatia": celulas_fatia,
			})

	return fatias


def desenhar_fatia_grande(pagina: pymupdf.Page, fatia: dict, indice: int, total_fatias: int, q_mm: float) -> None:
	info = fatia["info"]
	peca: Peca = info["peca"]
	ox = fatia["ox"]
	oy = fatia["oy"]
	fx = fatia["fx"]
	fy = fatia["fy"]
	y_grade = MARGEM_MM + 7.5

	pagina.insert_text(
		pymupdf.Point(mm_pt(MARGEM_MM), mm_pt(MARGEM_MM + 4.5)),
		f"{peca.id} - Parte {indice}/{total_fatias} (Grade {ox + 1}..{fx} x {oy + 1}..{fy})",
		fontsize=10.0,
		fontname="hebo",
		color=(0.15, 0.15, 0.15),
	)

	for cx, cy in sorted(fatia["celulas_fatia"]):
		desenhar_celula_peca(
			pagina,
			info,
			cx,
			cy,
			MARGEM_MM,
			y_grade,
			q_mm,
			ocultar_secretas=True,
			offset_x=ox,
			offset_y=oy,
			mostrar_etiquetas_externas=True,
		)

	larg_fatia_mm = (fx - ox) * q_mm
	alt_fatia_mm = (fy - oy) * q_mm

	if fatia["ix"] > 0:
		pagina.draw_line(
			pymupdf.Point(mm_pt(MARGEM_MM), mm_pt(y_grade)),
			pymupdf.Point(mm_pt(MARGEM_MM), mm_pt(y_grade + alt_fatia_mm)),
			color=(0.2, 0.45, 0.8),
			width=0.9,
			dashes="[3 3] 0",
		)
		pagina.insert_text(
			pymupdf.Point(mm_pt(MARGEM_MM + 1.0), mm_pt(y_grade + alt_fatia_mm / 2.0)),
			f"EMENDA H{fatia['iy'] + 1}-{fatia['ix']}",
			fontsize=6.5,
			fontname="hebo",
			color=(0.2, 0.45, 0.8),
		)

	if fatia["ix"] + 1 < fatia["nx"]:
		x_dir = MARGEM_MM + larg_fatia_mm
		pagina.draw_line(
			pymupdf.Point(mm_pt(x_dir), mm_pt(y_grade)),
			pymupdf.Point(mm_pt(x_dir), mm_pt(y_grade + alt_fatia_mm)),
			color=(0.2, 0.45, 0.8),
			width=0.9,
			dashes="[3 3] 0",
		)
		pagina.insert_text(
			pymupdf.Point(mm_pt(x_dir - 20.0), mm_pt(y_grade + alt_fatia_mm / 2.0)),
			f"EMENDA H{fatia['iy'] + 1}-{fatia['ix'] + 1}",
			fontsize=6.5,
			fontname="hebo",
			color=(0.2, 0.45, 0.8),
		)

	if fatia["iy"] > 0:
		pagina.draw_line(
			pymupdf.Point(mm_pt(MARGEM_MM), mm_pt(y_grade)),
			pymupdf.Point(mm_pt(MARGEM_MM + larg_fatia_mm), mm_pt(y_grade)),
			color=(0.2, 0.45, 0.8),
			width=0.9,
			dashes="[3 3] 0",
		)
		pagina.insert_text(
			pymupdf.Point(mm_pt(MARGEM_MM + larg_fatia_mm / 2.0 - 12.0), mm_pt(y_grade + 4.0)),
			f"EMENDA V{fatia['iy']}-{fatia['ix'] + 1}",
			fontsize=6.5,
			fontname="hebo",
			color=(0.2, 0.45, 0.8),
		)

	if fatia["iy"] + 1 < fatia["ny"]:
		y_baixo = y_grade + alt_fatia_mm
		pagina.draw_line(
			pymupdf.Point(mm_pt(MARGEM_MM), mm_pt(y_baixo)),
			pymupdf.Point(mm_pt(MARGEM_MM + larg_fatia_mm), mm_pt(y_baixo)),
			color=(0.2, 0.45, 0.8),
			width=0.9,
			dashes="[3 3] 0",
		)
		pagina.insert_text(
			pymupdf.Point(mm_pt(MARGEM_MM + larg_fatia_mm / 2.0 - 12.0), mm_pt(y_baixo - 2.0)),
			f"EMENDA V{fatia['iy'] + 1}-{fatia['ix'] + 1}",
			fontsize=6.5,
			fontname="hebo",
			color=(0.2, 0.45, 0.8),
		)

	desenhar_rotulo_peca(
		pagina,
		peca,
		fatia["celulas_fatia"],
		MARGEM_MM,
		y_grade,
		q_mm,
		offset_x=ox,
		offset_y=oy,
		sufixo=f" ({indice}/{total_fatias})",
	)


def desenhar_mapa_geral_mestre(doc: pymupdf.Document, masmorra: Masmorra) -> None:
	pagina = doc.new_page(width=mm_pt(LARGURA_A4_MM), height=mm_pt(ALTURA_A4_MM))
	pagina.insert_text(
		pymupdf.Point(mm_pt(MARGEM_MM), mm_pt(MARGEM_MM + 5.0)),
		f"Mapa Geral do Mestre - {masmorra.nome}",
		fontsize=13.0,
		fontname="hebo",
		color=(0.1, 0.1, 0.1),
	)
	pagina.insert_text(
		pymupdf.Point(mm_pt(MARGEM_MM), mm_pt(MARGEM_MM + 10.0)),
		limpar_texto_pdf(f"Tipo: {masmorra.tipo_masmorra} | Conservação: {masmorra.estado_conservacao[:78]}"),
		fontsize=7.5,
		fontname="helv",
		color=(0.35, 0.35, 0.35),
	)

	todas_celulas = [c for p in masmorra.pecas for c in p.celulas]
	if not todas_celulas:
		return

	min_x, min_y, max_x, max_y = limites_celulas(todas_celulas)
	total_qx = max_x - min_x + 1
	total_qy = max_y - min_y + 1

	area_x = AREA_UTIL_LARG_MM - 4.0
	area_y = ALTURA_A4_MM - 2 * MARGEM_MM - 24.0
	q_mm = min(12.0, area_x / max(1, total_qx), area_y / max(1, total_qy))
	escala_traco = max(0.35, min(1.0, q_mm / 15.0))

	x0_mm = MARGEM_MM + (AREA_UTIL_LARG_MM - total_qx * q_mm) / 2.0
	y0_mm = MARGEM_MM + 14.0 + (area_y - total_qy * q_mm) / 2.0

	for peca in masmorra.pecas:
		p_min_x, p_min_y, _, _ = limites_celulas(peca.celulas)
		info = normalizar_peca(peca, False)
		px_peca = x0_mm + (p_min_x - min_x) * q_mm
		py_peca = y0_mm + (p_min_y - min_y) * q_mm
		for cx, cy in info["celulas"]:
			desenhar_celula_peca(
				pagina,
				info,
				cx,
				cy,
				px_peca,
				py_peca,
				q_mm,
				ocultar_secretas=False,
				mostrar_etiquetas_externas=False,
				escala_traco=escala_traco,
			)
		desenhar_rotulo_peca(
			pagina,
			peca,
			info["celulas"],
			px_peca,
			py_peca,
			q_mm,
			tamanho_fonte=max(5.5, min(10.0, q_mm * 0.55)),
		)

	y_legenda = ALTURA_A4_MM - MARGEM_MM - 2.0
	pagina.insert_text(
		pymupdf.Point(mm_pt(MARGEM_MM), mm_pt(y_legenda)),
		"Legenda do Mestre: S = Sala | C = Corredor | E = Escada | [S vermelho] = Porta Secreta | [T âmbar] = Porta Trancada",
		fontsize=7.5,
		fontname="hebo",
		color=(0.3, 0.3, 0.3),
	)


def desenhar_guia_mestre(doc: pymupdf.Document, masmorra: Masmorra) -> None:
	pagina = doc.new_page(width=mm_pt(LARGURA_A4_MM), height=mm_pt(ALTURA_A4_MM))
	margem_x = mm_pt(MARGEM_MM + 3.0)
	larg_texto = mm_pt(AREA_UTIL_LARG_MM - 6.0)
	y_atual = mm_pt(MARGEM_MM + 7.0)
	y_limite = mm_pt(ALTURA_A4_MM - MARGEM_MM - 8.0)

	def nova_pagina_se_preciso(altura_necessaria: float) -> None:
		nonlocal pagina, y_atual
		if y_atual + altura_necessaria > y_limite:
			pagina = doc.new_page(width=mm_pt(LARGURA_A4_MM), height=mm_pt(ALTURA_A4_MM))
			y_atual = mm_pt(MARGEM_MM + 7.0)

	def escrever_bloco(texto: str, fontsize: float = 8.5, fontname: str = "helv", cor: tuple = (0.15, 0.15, 0.15)) -> None:
		nonlocal y_atual
		texto_limpo = limpar_texto_pdf(texto)
		max_chars = int(larg_texto / (fontsize * 0.48))
		palavras = texto_limpo.split()
		linhas = []
		atual = ""
		for p in palavras:
			if len(atual) + len(p) + 1 <= max_chars:
				atual = f"{atual} {p}".strip()
			else:
				if atual:
					linhas.append(atual)
				atual = p
		if atual:
			linhas.append(atual)
		if not linhas:
			return
		altura_linha = fontsize * 1.32
		nova_pagina_se_preciso(len(linhas) * altura_linha + 2.0)
		for linha in linhas:
			pagina.insert_text(
				pymupdf.Point(margem_x, y_atual),
				linha,
				fontsize=fontsize,
				fontname=fontname,
				color=cor,
			)
			y_atual += altura_linha

	escrever_bloco(f"Guia do Mestre - {masmorra.nome}", fontsize=13.0, fontname="hebo")
	escrever_bloco(f"Peculiaridade: {masmorra.peculiaridade}", fontsize=8.5)
	escrever_bloco(f"Estado de Conservação: {masmorra.estado_conservacao}", fontsize=8.5)
	y_atual += 6.0

	for peca in masmorra.pecas:
		nova_pagina_se_preciso(45.0)
		pagina.draw_line(
			pymupdf.Point(margem_x, y_atual - 4.0),
			pymupdf.Point(margem_x + larg_texto, y_atual - 4.0),
			color=(0.75, 0.75, 0.75),
			width=0.6,
		)
		y_atual += 6.0
		pov = peca.povoamento
		escrever_bloco(f"[{peca.id}] {pov.proposito} - {peca.descricao_geometria}", fontsize=10.0, fontname="hebo")
		if pov.categoria_2024:
			escrever_bloco(f"Categoria: {pov.categoria_2024} | Estado: {pov.estado_atual}", fontsize=8.2)
		escrever_bloco(f"Conteúdo: {pov.conteudo}", fontsize=8.5, fontname="hebo", cor=(0.1, 0.1, 0.1))
		if pov.monstros_motivacao:
			escrever_bloco(f"Motivação dos Monstros: {pov.monstros_motivacao}", fontsize=8.2)
		if pov.armadilha:
			escrever_bloco(f"Armadilha: {pov.armadilha}", fontsize=8.2, cor=(0.6, 0.1, 0.1))
		if pov.perigo:
			escrever_bloco(f"Perigo: {pov.perigo}", fontsize=8.2)
		if pov.obstaculo:
			escrever_bloco(f"Obstáculo: {pov.obstaculo}", fontsize=8.2)
		if pov.arapuca:
			escrever_bloco(f"Arapuca: {pov.arapuca}", fontsize=8.2)
		if pov.tesouro:
			escrever_bloco(f"Tesouro: {pov.tesouro}", fontsize=8.2)
		escrever_bloco(f"Ambiente - Som: {pov.barulho} | Odor: {pov.odor} | Mobília/Detalhes: {pov.mobilia}", fontsize=8.0, cor=(0.3, 0.3, 0.3))

		if peca.saidas:
			conexoes = []
			for s in peca.saidas:
				tags = []
				if s.secreta:
					tags.append("SECRETA")
				if s.trancada:
					tags.append("TRANCADA")
				tag_txt = f" [{' / '.join(tags)}]" if tags else ""
				destino = s.conectada_a or "Saída não explorada"
				conexoes.append(f"{s.direcao} ({s.descricao_porta}{tag_txt}) -> {destino}")
			escrever_bloco(f"Saídas: {'; '.join(conexoes)}", fontsize=8.0)

		if pov.notas:
			escrever_bloco(f"Notas do Mestre: {pov.notas}", fontsize=8.2, fontname="hebo")
		y_atual += 5.0


def gerar_pdf_masmorra(masmorra: Masmorra, config: ConfigExportacaoPDF) -> bytes:
	doc = pymupdf.open()
	q_mm = config.tamanho_quadrado_mm

	if config.incluir_mapa_geral:
		desenhar_mapa_geral_mestre(doc, masmorra)

	unitarias: list[dict] = []
	grandes: list[Peca] = []

	for peca in masmorra.pecas:
		if not peca.celulas:
			continue
		info0 = normalizar_peca(peca, False)
		w0 = info0["larg_quads"] * q_mm
		h0 = info0["alt_quads"] * q_mm
		cabe_normal = w0 <= AREA_UTIL_LARG_MM + 0.01 and h0 <= AREA_UTIL_ALT_MM + 0.01
		cabe_rot = h0 <= AREA_UTIL_LARG_MM + 0.01 and w0 <= AREA_UTIL_ALT_MM + 0.01
		if cabe_normal or cabe_rot:
			unitarias.append(info0 if cabe_normal else normalizar_peca(peca, True))
		else:
			grandes.append(peca)

	paginas_empacotadas = empacotar_pecas_unitarias(unitarias, q_mm)
	fatias_grandes: list[tuple[Peca, list[dict]]] = [
		(peca, fatiar_peca_grande(peca, q_mm)) for peca in grandes
	]

	total_paginas_grid = len(paginas_empacotadas) + sum(len(f) for _, f in fatias_grandes)
	indice_grid = 0

	for pag_data in paginas_empacotadas:
		indice_grid += 1
		pagina = doc.new_page(width=mm_pt(LARGURA_A4_MM), height=mm_pt(ALTURA_A4_MM))
		ids_na_pagina = []
		for item in pag_data["itens"]:
			info = item["info"]
			peca = info["peca"]
			ids_na_pagina.append(peca.id)
			for cx, cy in sorted(info["celulas"]):
				desenhar_celula_peca(
					pagina,
					info,
					cx,
					cy,
					item["x_mm"],
					item["y_mm"],
					q_mm,
					ocultar_secretas=True,
					mostrar_etiquetas_externas=True,
				)
			desenhar_rotulo_peca(pagina, peca, info["celulas"], item["x_mm"], item["y_mm"], q_mm)
		desenhar_rodape_pagina(pagina, masmorra, ", ".join(ids_na_pagina), q_mm, indice_grid, total_paginas_grid)

	for peca, fatias in fatias_grandes:
		total_f = len(fatias)
		for idx_f, fatia in enumerate(fatias, start=1):
			indice_grid += 1
			pagina = doc.new_page(width=mm_pt(LARGURA_A4_MM), height=mm_pt(ALTURA_A4_MM))
			desenhar_fatia_grande(pagina, fatia, idx_f, total_f, q_mm)
			desenhar_rodape_pagina(pagina, masmorra, f"{peca.id} (Parte {idx_f}/{total_f})", q_mm, indice_grid, total_paginas_grid)

	if config.incluir_guia_mestre:
		desenhar_guia_mestre(doc, masmorra)

	pdf_bytes = doc.tobytes()
	doc.close()
	return pdf_bytes
