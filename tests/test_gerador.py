import random

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
	assert masmorra.peculiaridade != ""
	assert masmorra.estado_conservacao != ""
	assert len(masmorra.pecas) == 1
	assert len(masmorra.pecas[0].celulas) >= 4
	assert len(masmorra.pecas[0].saidas) >= 1


def test_expandir_saidas_sem_sobreposicao():
	random.seed(42)
	masmorra = criar_masmorra("Masmorra Sem Sobreposicao", "geral")
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
	masmorra = criar_masmorra("Masmorra Rerol", "fortaleza")
	peca = masmorra.pecas[0]
	peca.povoamento.notas = "Nota importante do mestre"
	celulas_antes = [(c.x, c.y) for c in peca.celulas]

	rerolar_peca(masmorra, peca.id, "povoamento")
	celulas_depois = [(c.x, c.y) for c in masmorra.pecas[0].celulas]

	assert celulas_antes == celulas_depois
	assert masmorra.pecas[0].povoamento.notas == "Nota importante do mestre"


def test_rerolar_geometria_preserva_povoamento():
	random.seed(7)
	masmorra = criar_masmorra("Masmorra Geo", "covil")
	peca = masmorra.pecas[0]
	saida = peca.saidas[0]
	masmorra, nova = expandir_saida(masmorra, peca.id, saida.id)
	assert nova is not None
	nova.povoamento.proposito = "Propósito Fixo"

	rerolar_peca(masmorra, nova.id, "geometria")
	peca_atualizada = next(p for p in masmorra.pecas if p.id == nova.id)
	assert peca_atualizada.povoamento.proposito == "Propósito Fixo"


def test_gerar_masmorra_completa():
	random.seed(99)
	masmorra = criar_masmorra("Masmorra Completa", "mina")
	gerar_masmorra_completa(masmorra, total_salas=6)
	qtd_salas = sum(1 for p in masmorra.pecas if p.tipo == "sala")
	todas_celulas = [(c.x, c.y) for p in masmorra.pecas for c in p.celulas]

	assert qtd_salas >= 3
	assert len(todas_celulas) == len(set(todas_celulas))
