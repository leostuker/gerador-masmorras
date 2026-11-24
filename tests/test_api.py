from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_health_e_pagina_inicial():
	res_health = client.get("/health")
	assert res_health.status_code == 200
	assert res_health.json()["status"] == "ok"

	res_home = client.get("/")
	assert res_home.status_code == 200
	assert "Gerador de Masmorras" in res_home.text


def test_fluxo_completo_masmorra_e_exportacao_pdf():
	res_nova = client.post("/api/masmorras/nova", json={"nome": "Teste API", "tipo_masmorra": "covil"})
	assert res_nova.status_code == 200
	masmorra = res_nova.json()
	masmorra_id = masmorra["id"]

	try:
		peca = masmorra["pecas"][0]
		saida_id = peca["saidas"][0]["id"]
		res_exp = client.post(
			f"/api/masmorras/{masmorra_id}/expandir",
			json={"peca_id": peca["id"], "saida_id": saida_id},
		)
		assert res_exp.status_code == 200

		res_comp = client.post(
			f"/api/masmorras/{masmorra_id}/gerar-completa",
			json={"total_salas": 5},
		)
		assert res_comp.status_code == 200
		assert len(res_comp.json()["pecas"]) >= 2

		res_rerol = client.post(
			f"/api/masmorras/{masmorra_id}/rerolar/{peca['id']}",
			json={"escopo": "povoamento"},
		)
		assert res_rerol.status_code == 200

		res_pdf = client.post(
			f"/api/masmorras/{masmorra_id}/exportar-pdf",
			json={"tamanho_quadrado_mm": 25.0, "incluir_mapa_geral": True, "incluir_guia_mestre": True},
		)
		assert res_pdf.status_code == 200
		assert res_pdf.headers["content-type"] == "application/pdf"
		assert res_pdf.content.startswith(b"%PDF")
	finally:
		res_del = client.delete(f"/api/masmorras/{masmorra_id}")
		assert res_del.status_code == 200


def test_criar_masmorra_com_seed_reprodutivel():
	payload = {"nome": "Seed API", "tipo_masmorra": "tumba", "seed": "TUMBA-99"}
	res1 = client.post("/api/masmorras/nova", json=payload)
	res2 = client.post("/api/masmorras/nova", json=payload)
	assert res1.status_code == 200
	assert res2.status_code == 200

	d1 = res1.json()
	d2 = res2.json()
	try:
		assert d1["seed"] == "TUMBA-99"
		assert d2["seed"] == "TUMBA-99"
		assert d1["peculiaridade"] == d2["peculiaridade"]
		assert d1["estado_conservacao"] == d2["estado_conservacao"]
		assert d1["pecas"][0] == d2["pecas"][0]
	finally:
		client.delete(f"/api/masmorras/{d1['id']}")
		client.delete(f"/api/masmorras/{d2['id']}")
