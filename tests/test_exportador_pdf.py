import pymupdf

from backend.exportador_pdf import MM_PARA_PT, gerar_pdf_masmorra
from backend.modelos import Celula, ConfigExportacaoPDF, Masmorra, Peca, Povoamento, Saida


def criar_peca_simples(peca_id: str, larg: int, alt: int, tipo: str = "sala", saidas: list[Saida] | None = None) -> Peca:
	celulas = [Celula(x=x, y=y) for y in range(alt) for x in range(larg)]
	return Peca(
		id=peca_id,
		tipo=tipo,
		formato="retangular",
		descricao_geometria=f"{larg}x{alt}",
		celulas=celulas,
		saidas=saidas or [],
		povoamento=Povoamento(proposito=f"Sala {peca_id}", conteudo="Sala vazia"),
	)


def test_pdf_formato_a4_e_escalas_variadas():
	masmorra = Masmorra(
		id="t1",
		nome="Masmorra Escala",
		tipo_masmorra="geral",
		peculiaridade="Teste",
		estado_conservacao="Normal",
		pecas=[criar_peca_simples("S1", 4, 4)],
	)
	for tam_mm in (15.0, 25.0, 35.0):
		pdf_bytes = gerar_pdf_masmorra(masmorra, ConfigExportacaoPDF(tamanho_quadrado_mm=tam_mm))
		doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
		assert len(doc) >= 3
		rect = doc[0].rect
		assert abs(rect.width - 210.0 * MM_PARA_PT) < 1.0
		assert abs(rect.height - 297.0 * MM_PARA_PT) < 1.0
		doc.close()


def test_empacotamento_multiplas_pecas_mesma_folha():
	pecas = [
		criar_peca_simples("S1", 3, 3),
		criar_peca_simples("S2", 3, 3),
		criar_peca_simples("C1", 2, 4, tipo="corredor"),
		criar_peca_simples("C2", 2, 4, tipo="corredor"),
	]
	masmorra = Masmorra(
		id="t2",
		nome="Empacotamento",
		tipo_masmorra="geral",
		peculiaridade="Teste",
		estado_conservacao="Normal",
		pecas=pecas,
	)
	pdf_bytes = gerar_pdf_masmorra(
		masmorra,
		ConfigExportacaoPDF(tamanho_quadrado_mm=25.0, incluir_mapa_geral=False, incluir_guia_mestre=False),
	)
	doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
	assert len(doc) == 1
	texto = doc[0].get_text()
	assert "S1" in texto
	assert "S2" in texto
	assert "C1" in texto
	assert "C2" in texto
	doc.close()


def test_fatiamento_sala_gigante():
	masmorra = Masmorra(
		id="t3",
		nome="Sala Gigante",
		tipo_masmorra="geral",
		peculiaridade="Teste",
		estado_conservacao="Normal",
		pecas=[criar_peca_simples("S1", 12, 12)],
	)
	pdf_bytes = gerar_pdf_masmorra(
		masmorra,
		ConfigExportacaoPDF(tamanho_quadrado_mm=25.0, incluir_mapa_geral=False, incluir_guia_mestre=False),
	)
	doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
	assert len(doc) >= 2
	assert "Parte 1/" in doc[0].get_text()
	doc.close()


def test_sigilo_portas_secretas_nas_folhas_jogadores():
	saida_secreta = Saida(
		id="S1_O1",
		x=3,
		y=1,
		direcao="L",
		tipo_porta="secreta",
		descricao_porta="Porta secreta",
		secreta=True,
		trancada=False,
		conectada_a="C9",
		aberta=False,
	)
	saida_normal = Saida(
		id="S1_O2",
		x=0,
		y=1,
		direcao="O",
		tipo_porta="madeira",
		descricao_porta="Madeira",
		secreta=False,
		trancada=False,
		conectada_a="C2",
		aberta=False,
	)
	masmorra = Masmorra(
		id="t4",
		nome="Sigilo",
		tipo_masmorra="geral",
		peculiaridade="Teste",
		estado_conservacao="Normal",
		pecas=[criar_peca_simples("S1", 4, 4, saidas=[saida_secreta, saida_normal])],
	)

	pdf_jogadores = gerar_pdf_masmorra(
		masmorra,
		ConfigExportacaoPDF(tamanho_quadrado_mm=25.0, incluir_mapa_geral=False, incluir_guia_mestre=False),
	)
	doc_jog = pymupdf.open(stream=pdf_jogadores, filetype="pdf")
	texto_jog = doc_jog[0].get_text()
	assert "C9" not in texto_jog
	assert "C2" in texto_jog
	doc_jog.close()

	pdf_mestre = gerar_pdf_masmorra(
		masmorra,
		ConfigExportacaoPDF(tamanho_quadrado_mm=25.0, incluir_mapa_geral=True, incluir_guia_mestre=True),
	)
	doc_mestre = pymupdf.open(stream=pdf_mestre, filetype="pdf")
	texto_mapa_mestre = doc_mestre[0].get_text()
	texto_guia_mestre = doc_mestre[-1].get_text()
	assert "S" in texto_mapa_mestre
	assert "SECRETA" in texto_guia_mestre
	assert "C9" in texto_guia_mestre
	doc_mestre.close()


def test_rotulos_sempre_fora_dos_quadrados_nas_folhas_jogadores():
	saidas_quatro_lados = [
		Saida(id="S5_O1", x=1, y=0, direcao="N", tipo_porta="corredor", descricao_porta="Passagem", conectada_a="C5", aberta=False),
		Saida(id="S5_O2", x=0, y=0, direcao="O", tipo_porta="madeira", descricao_porta="Madeira", conectada_a="C11", aberta=False),
		Saida(id="S5_O3", x=0, y=1, direcao="O", tipo_porta="corredor", descricao_porta="Passagem", conectada_a="S1", aberta=False),
		Saida(id="S5_O4", x=1, y=1, direcao="S", tipo_porta="madeira", descricao_porta="Madeira", conectada_a="S2", aberta=False),
		Saida(id="S5_O5", x=1, y=0, direcao="L", tipo_porta="corredor", descricao_porta="Passagem", conectada_a="C8", aberta=False),
	]
	pecas = [
		criar_peca_simples("S5", 2, 2, saidas=saidas_quatro_lados),
		criar_peca_simples("S1", 2, 2),
	]
	masmorra = Masmorra(
		id="t5",
		nome="Fora do Grid",
		tipo_masmorra="geral",
		peculiaridade="Teste",
		estado_conservacao="Normal",
		pecas=pecas,
	)
	pdf_bytes = gerar_pdf_masmorra(
		masmorra,
		ConfigExportacaoPDF(tamanho_quadrado_mm=25.0, incluir_mapa_geral=False, incluir_guia_mestre=False),
	)
	doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
	assert len(doc) == 1
	pag = doc[0]
	retangulos_grade = []
	for desenho in pag.get_drawings():
		r = desenho["rect"]
		if abs(r.width - 25.0 * MM_PARA_PT) < 1.0 and abs(r.height - 25.0 * MM_PARA_PT) < 1.0:
			retangulos_grade.append(r)
	assert len(retangulos_grade) == 8

	for x0, y0, x1, y1, palavra, *_ in pag.get_text("words"):
		cx = (x0 + x1) / 2.0
		cy = (y0 + y1) / 2.0
		for rg in retangulos_grade:
			dentro = rg.x0 + 1.0 < cx < rg.x1 - 1.0 and rg.y0 + 1.0 < cy < rg.y1 - 1.0
			assert not dentro, f"Texto '{palavra}' invadiu o quadrado da grade"
	doc.close()
