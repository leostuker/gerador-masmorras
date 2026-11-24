from backend.gerador import (
	TABELAS_AMBIENTACAO,
	TABELAS_GEOMETRIA,
	TABELAS_POVOAMENTO,
	TABELAS_PROPOSITO,
	criar_masmorra,
	expandir_saida,
	gerar_masmorra_completa,
	rerolar_peca,
)


def test_tabelas_json_carregadas():
	assert len(TABELAS_GEOMETRIA["area_inicial"]) == 10
	assert len(TABELAS_PROPOSITO["peculiaridades_masmorra"]) > 20
	assert len(TABELAS_POVOAMENTO["conteudo_camara"]) == 14
	assert len(TABELAS_AMBIENTACAO["barulhos"]) > 30


def test_criar_masmorra_inicial():
	masmorra = criar_masmorra("Tumba Teste", "tumba")
	assert masmorra.nome == "Tumba Teste"
	assert len(masmorra.seed) == 8
	assert masmorra.peculiaridade != ""
	assert masmorra.estado_conservacao != ""
	assert len(masmorra.pecas) == 1
	assert len(masmorra.pecas[0].celulas) >= 4
	assert len(masmorra.pecas[0].saidas) >= 1


def test_expandir_saidas_sem_sobreposicao():
	masmorra = criar_masmorra("Masmorra Sem Sobreposicao", "geral", seed="TESTE-42")
	for _ in range(12):
		abertas = [
			(p.id, s.id)
			for p in masmorra.pecas
			for s in p.saidas
			if s.aberta
		]
		if not abertas:
			break
		peca_id, saida_id = abertas[0]
		masmorra, _ = expandir_saida(masmorra, peca_id, saida_id)

	todas_celulas = [(c.x, c.y) for p in masmorra.pecas for c in p.celulas]
	assert len(todas_celulas) == len(set(todas_celulas))


def test_rerolar_povoamento_preserva_geometria_e_notas():
	masmorra = criar_masmorra("Masmorra Rerol", "fortaleza", seed="REROL-01")
	peca = masmorra.pecas[0]
	peca.povoamento.notas = "Nota importante do mestre"
	celulas_antes = [(c.x, c.y) for c in peca.celulas]

	rerolar_peca(masmorra, peca.id, "povoamento")
	celulas_depois = [(c.x, c.y) for c in masmorra.pecas[0].celulas]

	assert celulas_antes == celulas_depois
	assert masmorra.pecas[0].povoamento.notas == "Nota importante do mestre"


def test_rerolar_geometria_preserva_povoamento():
	masmorra = criar_masmorra("Masmorra Geo", "covil", seed="COVIL-7")
	peca = masmorra.pecas[0]
	saida = peca.saidas[0]
	masmorra, nova = expandir_saida(masmorra, peca.id, saida.id)
	assert nova is not None
	nova.povoamento.proposito = "Propósito Fixo"

	rerolar_peca(masmorra, nova.id, "geometria")
	peca_atualizada = next(p for p in masmorra.pecas if p.id == nova.id)
	assert peca_atualizada.povoamento.proposito == "Propósito Fixo"


def test_gerar_masmorra_completa():
	masmorra = criar_masmorra("Masmorra Completa", "mina", seed="MINA-99")
	gerar_masmorra_completa(masmorra, total_salas=6)
	qtd_salas = sum(1 for p in masmorra.pecas if p.tipo == "sala")
	todas_celulas = [(c.x, c.y) for p in masmorra.pecas for c in p.celulas]

	assert qtd_salas >= 3
	assert len(todas_celulas) == len(set(todas_celulas))


def test_mesma_seed_gera_masmorra_identica():
	m1 = criar_masmorra("Masmorra A", "geral", seed="CRISTAIS-42")
	gerar_masmorra_completa(m1, total_salas=6)

	m2 = criar_masmorra("Masmorra A", "geral", seed="CRISTAIS-42")
	gerar_masmorra_completa(m2, total_salas=6)

	dados1 = m1.model_dump()
	dados2 = m2.model_dump()
	dados1.pop("id")
	dados2.pop("id")
	assert dados1 == dados2


def test_expandir_mesma_saida_com_mesma_seed_eh_deterministico():
	m1 = criar_masmorra("Masmorra B", "tumba", seed="ESPINHO-13")
	m2 = criar_masmorra("Masmorra B", "tumba", seed="ESPINHO-13")

	saida1 = m1.pecas[0].saidas[0]
	saida2 = m2.pecas[0].saidas[0]
	m1, p1 = expandir_saida(m1, m1.pecas[0].id, saida1.id)
	m2, p2 = expandir_saida(m2, m2.pecas[0].id, saida2.id)

	assert (p1 is None) == (p2 is None)
	if p1 is not None and p2 is not None:
		assert p1.model_dump() == p2.model_dump()


def test_seeds_diferentes_geram_masmorras_diferentes():
	m1 = criar_masmorra("Masmorra 1", "geral", seed="SEED-ALFA")
	gerar_masmorra_completa(m1, total_salas=5)

	m2 = criar_masmorra("Masmorra 2", "geral", seed="SEED-BETA")
	gerar_masmorra_completa(m2, total_salas=5)

	assert m1.pecas != m2.pecas


def test_rerolar_avanca_passo_rng():
	m1 = criar_masmorra("Masmorra Passo", "fortaleza", seed="FORTE-88")
	m2 = criar_masmorra("Masmorra Passo", "fortaleza", seed="FORTE-88")

	assert m1.passo_rng == 0
	rerolar_peca(m1, m1.pecas[0].id, "tudo")
	rerolar_peca(m2, m2.pecas[0].id, "tudo")

	assert m1.passo_rng == 1
	assert m1.pecas[0].model_dump() == m2.pecas[0].model_dump()
