const TAMANHO_CELULA = 36;
const VETORES = {
	N: [0, -1],
	S: [0, 1],
	L: [1, 0],
	O: [-1, 0],
};

let estado = {
	masmorra: null,
	pecaSelecionadaId: null,
	modoEdicao: false,
	ferramentaEdicao: "pintar",
	modoRegua: false,
	reguaInicio: null,
	reguaFim: null,
	zoom: 1,
	panX: 160,
	panY: 160,
	arrastandoMapa: false,
	ultimoPonteiro: null,
	timerSalvar: null,
};

const elSvg = document.getElementById("mapa-svg");
const elMundo = document.getElementById("camada-mundo");
const elGrade = document.getElementById("camada-grade");
const elPecas = document.getElementById("camada-pecas");
const elSaidas = document.getElementById("camada-saidas");
const elRotulos = document.getElementById("camada-rotulos");
const elEdicao = document.getElementById("camada-edicao");
const elRegua = document.getElementById("camada-regua");
const elStatus = document.getElementById("status-salvamento");

function definirStatus(texto) {
	elStatus.textContent = texto;
}

async function requisicaoJson(url, opcoes = {}) {
	const resposta = await fetch(url, {
		headers: { "Content-Type": "application/json" },
		...opcoes,
	});
	if (!resposta.ok) {
		const msg = await resposta.text();
		throw new Error(msg || "Erro na requisição");
	}
	return resposta.json();
}

function criarElementoSvg(tag, atributos = {}) {
	const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
	for (const [k, v] of Object.entries(atributos)) {
		el.setAttribute(k, String(v));
	}
	return el;
}

function aplicarTransformacao() {
	elMundo.setAttribute("transform", `translate(${estado.panX}, ${estado.panY}) scale(${estado.zoom})`);
}

function centralizarMapa() {
	if (!estado.masmorra || estado.masmorra.pecas.length === 0) {
		return;
	}
	const todas = estado.masmorra.pecas.flatMap((p) => p.celulas);
	const minX = Math.min(...todas.map((c) => c.x));
	const maxX = Math.max(...todas.map((c) => c.x));
	const minY = Math.min(...todas.map((c) => c.y));
	const maxY = Math.max(...todas.map((c) => c.y));

	const rect = elSvg.getBoundingClientRect();
	const largMundo = (maxX - minX + 3) * TAMANHO_CELULA;
	const altMundo = (maxY - minY + 3) * TAMANHO_CELULA;
	const escalaX = rect.width / Math.max(largMundo, 100);
	const escalaY = rect.height / Math.max(altMundo, 100);
	estado.zoom = Math.max(0.35, Math.min(1.6, Math.min(escalaX, escalaY) * 0.85));

	const centroX = ((minX + maxX + 1) / 2) * TAMANHO_CELULA;
	const centroY = ((minY + maxY + 1) / 2) * TAMANHO_CELULA;
	estado.panX = rect.width / 2 - centroX * estado.zoom;
	estado.panY = rect.height / 2 - centroY * estado.zoom;
	aplicarTransformacao();
}

function pontoSvgParaGrid(clientX, clientY) {
	const rect = elSvg.getBoundingClientRect();
	const mundoX = (clientX - rect.left - estado.panX) / estado.zoom;
	const mundoY = (clientY - rect.top - estado.panY) / estado.zoom;
	return {
		gx: Math.floor(mundoX / TAMANHO_CELULA),
		gy: Math.floor(mundoY / TAMANHO_CELULA),
		wx: mundoX,
		wy: mundoY,
	};
}

function obterPecaSelecionada() {
	if (!estado.masmorra || !estado.pecaSelecionadaId) {
		return null;
	}
	return estado.masmorra.pecas.find((p) => p.id === estado.pecaSelecionadaId) || null;
}

function renderizarGradeFundo() {
	elGrade.innerHTML = "";
	const passo = TAMANHO_CELULA;
	const inicio = -50 * passo;
	const fim = 50 * passo;
	for (let i = -50; i <= 50; i++) {
		const pos = i * passo;
		elGrade.appendChild(
			criarElementoSvg("line", {
				x1: inicio,
				y1: pos,
				x2: fim,
				y2: pos,
				stroke: "#2d2d2d",
				"stroke-width": 1,
			})
		);
		elGrade.appendChild(
			criarElementoSvg("line", {
				x1: pos,
				y1: inicio,
				x2: pos,
				y2: fim,
				stroke: "#2d2d2d",
				"stroke-width": 1,
			})
		);
	}
}

function corPeca(peca, selecionada) {
	if (selecionada) {
		return "#3b3520";
	}
	if (peca.tipo === "corredor") {
		return "#2a2a2a";
	}
	if (peca.tipo === "escada") {
		return "#352e23";
	}
	return "#313131";
}

function renderizarMapa() {
	elPecas.innerHTML = "";
	elSaidas.innerHTML = "";
	elRotulos.innerHTML = "";
	elEdicao.innerHTML = "";

	if (!estado.masmorra) {
		return;
	}

	for (const peca of estado.masmorra.pecas) {
		const selecionada = peca.id === estado.pecaSelecionadaId;
		const conjunto = new Set(peca.celulas.map((c) => `${c.x},${c.y}`));
		const mapaSaidas = new Map();
		for (const s of peca.saidas) {
			mapaSaidas.set(`${s.x},${s.y},${s.direcao}`, s);
		}

		for (const cel of peca.celulas) {
			const x = cel.x * TAMANHO_CELULA;
			const y = cel.y * TAMANHO_CELULA;
			const quadrado = criarElementoSvg("rect", {
				x,
				y,
				width: TAMANHO_CELULA,
				height: TAMANHO_CELULA,
				fill: corPeca(peca, selecionada),
				stroke: "#484848",
				"stroke-width": 0.8,
				class: "celula-piso",
			});
			quadrado.addEventListener("click", (ev) => {
				ev.stopPropagation();
				tratarCliqueCelula(peca, cel);
			});
			elPecas.appendChild(quadrado);

			if (peca.tipo === "escada") {
				for (let i = 1; i <= 3; i++) {
					const ry = y + (TAMANHO_CELULA * i) / 4;
					elPecas.appendChild(
						criarElementoSvg("line", {
							x1: x + 6,
							y1: ry,
							x2: x + TAMANHO_CELULA - 6,
							y2: ry,
							stroke: "#b89f6d",
							"stroke-width": 1.4,
							"pointer-events": "none",
						})
					);
				}
			}

			const bordas = {
				N: [0, -1, x, y, x + TAMANHO_CELULA, y],
				S: [0, 1, x, y + TAMANHO_CELULA, x + TAMANHO_CELULA, y + TAMANHO_CELULA],
				O: [-1, 0, x, y, x, y + TAMANHO_CELULA],
				L: [1, 0, x + TAMANHO_CELULA, y, x + TAMANHO_CELULA, y + TAMANHO_CELULA],
			};

			for (const [dir, [vx, vy, x1, y1, x2, y2]] of Object.entries(bordas)) {
				if (conjunto.has(`${cel.x + vx},${cel.y + vy}`)) {
					continue;
				}
				const saida = mapaSaidas.get(`${cel.x},${cel.y},${dir}`);
				if (!saida) {
					elPecas.appendChild(
						criarElementoSvg("line", {
							x1,
							y1,
							x2,
							y2,
							stroke: selecionada ? "#FFD700" : "#e0e0e0",
							"stroke-width": selecionada ? 3.2 : 2.6,
							"pointer-events": "none",
						})
					);
					continue;
				}

				const mx1 = x1 + (x2 - x1) * 0.22;
				const my1 = y1 + (y2 - y1) * 0.22;
				const mx2 = x1 + (x2 - x1) * 0.78;
				const my2 = y1 + (y2 - y1) * 0.78;
				elPecas.appendChild(
					criarElementoSvg("line", {
						x1,
						y1,
						x2: mx1,
						y2: my1,
						stroke: selecionada ? "#FFD700" : "#e0e0e0",
						"stroke-width": 2.6,
						"pointer-events": "none",
					})
				);
				elPecas.appendChild(
					criarElementoSvg("line", {
						x1: mx2,
						y1: my2,
						x2,
						y2,
						stroke: selecionada ? "#FFD700" : "#e0e0e0",
						"stroke-width": 2.6,
						"pointer-events": "none",
					})
				);

				desenharSaidaInterativa(peca, saida, x1, y1, x2, y2);
			}
		}

		if (peca.celulas.length > 0) {
			const mediaX = peca.celulas.reduce((acc, c) => acc + c.x, 0) / peca.celulas.length;
			const mediaY = peca.celulas.reduce((acc, c) => acc + c.y, 0) / peca.celulas.length;
			let celCentro = peca.celulas[0];
			let melhorDist = Infinity;
			for (const c of peca.celulas) {
				const d = (c.x - mediaX) ** 2 + (c.y - mediaY) ** 2;
				if (d < melhorDist) {
					melhorDist = d;
					celCentro = c;
				}
			}
			const texto = criarElementoSvg("text", {
				x: (celCentro.x + 0.5) * TAMANHO_CELULA,
				y: (celCentro.y + 0.5) * TAMANHO_CELULA + 4,
				"text-anchor": "middle",
				fill: selecionada ? "#FFD700" : "#cccccc",
				"font-size": 13,
				"font-weight": "bold",
				"pointer-events": "none",
			});
			texto.textContent = peca.id;
			elRotulos.appendChild(texto);
		}
	}

	if (estado.modoEdicao && estado.ferramentaEdicao === "pintar") {
		renderizarAlvosPintura();
	}
	renderizarRegua();
}

function desenharSaidaInterativa(peca, saida, x1, y1, x2, y2) {
	const cx = (x1 + x2) / 2;
	const cy = (y1 + y2) / 2;
	const horizontal = saida.direcao === "N" || saida.direcao === "S";
	const cor = saida.secreta ? "#4aa3ff" : saida.trancada ? "#ff8844" : "#FFD700";

	if (saida.tipo_porta !== "corredor") {
		const rect = criarElementoSvg("rect", {
			x: horizontal ? cx - 9 : cx - 4,
			y: horizontal ? cy - 4 : cy - 9,
			width: horizontal ? 18 : 8,
			height: horizontal ? 8 : 18,
			fill: saida.aberta ? cor : "#181818",
			stroke: cor,
			"stroke-width": 1.8,
			rx: 2,
		});
		elSaidas.appendChild(rect);
	}

	if (saida.secreta || saida.trancada) {
		const sigla = criarElementoSvg("text", {
			x: cx,
			y: cy + 3,
			"text-anchor": "middle",
			fill: saida.aberta ? "#181818" : cor,
			"font-size": 8,
			"font-weight": "bold",
			"pointer-events": "none",
		});
		sigla.textContent = saida.secreta ? "S" : "T";
		elSaidas.appendChild(sigla);
	}

	if (saida.aberta) {
		const [vx, vy] = VETORES[saida.direcao];
		const bx = cx + vx * 14;
		const by = cy + vy * 14;
		const botao = criarElementoSvg("circle", {
			cx: bx,
			cy: by,
			r: 7,
			fill: "#FFD700",
			stroke: "#181818",
			"stroke-width": 1.5,
			class: "saida-aberta",
		});
		const mais = criarElementoSvg("text", {
			x: bx,
			y: by + 3.5,
			"text-anchor": "middle",
			fill: "#181818",
			"font-size": 11,
			"font-weight": "bold",
			"pointer-events": "none",
		});
		mais.textContent = "+";
		botao.addEventListener("click", (ev) => {
			ev.stopPropagation();
			if (estado.modoEdicao && estado.ferramentaEdicao === "porta") {
				alternarSaidaNaBorda(peca, saida.x, saida.y, saida.direcao);
				return;
			}
			expandirSaida(peca.id, saida.id);
		});
		elSaidas.appendChild(botao);
		elSaidas.appendChild(mais);
	}
}

function renderizarAlvosPintura() {
	const peca = obterPecaSelecionada();
	if (!peca) {
		return;
	}
	const ocupadas = new Set();
	for (const p of estado.masmorra.pecas) {
		for (const c of p.celulas) {
			ocupadas.add(`${c.x},${c.y}`);
		}
	}
	const candidatas = new Map();
	for (const c of peca.celulas) {
		for (const [vx, vy] of Object.values(VETORES)) {
			const nx = c.x + vx;
			const ny = c.y + vy;
			const chave = `${nx},${ny}`;
			if (!ocupadas.has(chave)) {
				candidatas.set(chave, { x: nx, y: ny });
			}
		}
	}
	for (const cel of candidatas.values()) {
		const rect = criarElementoSvg("rect", {
			x: cel.x * TAMANHO_CELULA + 2,
			y: cel.y * TAMANHO_CELULA + 2,
			width: TAMANHO_CELULA - 4,
			height: TAMANHO_CELULA - 4,
			fill: "rgba(255, 215, 0, 0.14)",
			stroke: "#FFD700",
			"stroke-dasharray": "4 3",
			"stroke-width": 1.2,
			cursor: "pointer",
		});
		rect.addEventListener("click", (ev) => {
			ev.stopPropagation();
			peca.celulas.push({ x: cel.x, y: cel.y });
			renderizarMapa();
			agendarSalvamento();
		});
		elEdicao.appendChild(rect);
	}
}

function tratarCliqueCelula(peca, cel) {
	if (estado.modoRegua) {
		return;
	}
	if (estado.modoEdicao && estado.pecaSelecionadaId === peca.id) {
		if (estado.ferramentaEdicao === "apagar") {
			if (peca.celulas.length <= 1) {
				return;
			}
			peca.celulas = peca.celulas.filter((c) => !(c.x === cel.x && c.y === cel.y));
			peca.saidas = peca.saidas.filter((s) => !(s.x === cel.x && s.y === cel.y));
			renderizarMapa();
			atualizarPainelLateral();
			agendarSalvamento();
			return;
		}
		if (estado.ferramentaEdicao === "porta") {
			const conjunto = new Set(peca.celulas.map((c) => `${c.x},${c.y}`));
			for (const [dir, [vx, vy]] of Object.entries(VETORES)) {
				if (!conjunto.has(`${cel.x + vx},${cel.y + vy}`)) {
					alternarSaidaNaBorda(peca, cel.x, cel.y, dir);
					break;
				}
			}
			return;
		}
	}
	estado.pecaSelecionadaId = peca.id;
	renderizarMapa();
	atualizarPainelLateral();
}

function alternarSaidaNaBorda(peca, x, y, dir) {
	const idx = peca.saidas.findIndex((s) => s.x === x && s.y === y && s.direcao === dir);
	if (idx === -1) {
		peca.saidas.push({
			id: `${peca.id}_O${Date.now().toString().slice(-4)}`,
			x,
			y,
			direcao: dir,
			tipo_porta: "madeira",
			descricao_porta: "Madeira",
			secreta: false,
			trancada: false,
			conectada_a: null,
			aberta: true,
		});
	} else {
		const s = peca.saidas[idx];
		if (s.tipo_porta === "madeira" && !s.trancada && !s.secreta) {
			s.trancada = true;
			s.descricao_porta = "Madeira, barrada ou trancada";
		} else if (s.trancada && !s.secreta) {
			s.trancada = false;
			s.secreta = true;
			s.tipo_porta = "secreta";
			s.descricao_porta = "Porta secreta";
		} else if (s.secreta) {
			s.secreta = false;
			s.tipo_porta = "corredor";
			s.descricao_porta = "Passagem aberta";
		} else if (!s.conectada_a) {
			peca.saidas.splice(idx, 1);
		} else {
			s.tipo_porta = "madeira";
			s.descricao_porta = "Madeira";
		}
	}
	renderizarMapa();
	atualizarPainelLateral();
	agendarSalvamento();
}

function moverPecaSelecionada(dx, dy) {
	const peca = obterPecaSelecionada();
	if (!peca) {
		return;
	}
	const ocupadasOutras = new Set();
	for (const p of estado.masmorra.pecas) {
		if (p.id === peca.id) {
			continue;
		}
		for (const c of p.celulas) {
			ocupadasOutras.add(`${c.x},${c.y}`);
		}
	}
	for (const c of peca.celulas) {
		if (ocupadasOutras.has(`${c.x + dx},${c.y + dy}`)) {
			return;
		}
	}
	for (const c of peca.celulas) {
		c.x += dx;
		c.y += dy;
	}
	for (const s of peca.saidas) {
		s.x += dx;
		s.y += dy;
	}
	renderizarMapa();
	agendarSalvamento();
}

function renderizarRegua() {
	elRegua.innerHTML = "";
	const badge = document.getElementById("info-regua");
	if (!estado.modoRegua || !estado.reguaInicio || !estado.reguaFim) {
		badge.classList.add("oculto");
		return;
	}
	const p1 = estado.reguaInicio;
	const p2 = estado.reguaFim;
	const x1 = (p1.gx + 0.5) * TAMANHO_CELULA;
	const y1 = (p1.gy + 0.5) * TAMANHO_CELULA;
	const x2 = (p2.gx + 0.5) * TAMANHO_CELULA;
	const y2 = (p2.gy + 0.5) * TAMANHO_CELULA;

	elRegua.appendChild(
		criarElementoSvg("line", {
			x1,
			y1,
			x2,
			y2,
			stroke: "#FFD700",
			"stroke-width": 2.5,
			"stroke-dasharray": "6 4",
		})
	);
	elRegua.appendChild(criarElementoSvg("circle", { cx: x1, cy: y1, r: 4, fill: "#FFD700" }));
	elRegua.appendChild(criarElementoSvg("circle", { cx: x2, cy: y2, r: 4, fill: "#FFD700" }));

	const dx = Math.abs(p2.gx - p1.gx);
	const dy = Math.abs(p2.gy - p1.gy);
	const quadradosDnd = Math.max(dx, dy);
	const distanciaEuclidiana = Math.hypot(dx, dy);
	const metros = (quadradosDnd * 1.5).toFixed(1).replace(".", ",");
	const pes = quadradosDnd * 5;
	const texto = `${quadradosDnd} quad (${metros} m / ${pes} pés) | Reta: ${distanciaEuclidiana.toFixed(1)} quad`;
	badge.textContent = texto;
	badge.classList.remove("oculto");
}

function atualizarPainelLateral() {
	if (!estado.masmorra) {
		return;
	}
	document.getElementById("input-nome-masmorra").value = estado.masmorra.nome;
	document.getElementById("select-tipo-masmorra").value = estado.masmorra.tipo_masmorra;
	document.getElementById("texto-seed").textContent = estado.masmorra.seed || "-";
	document.getElementById("texto-peculiaridade").textContent = estado.masmorra.peculiaridade;
	document.getElementById("texto-conservacao").textContent = estado.masmorra.estado_conservacao;

	const qtdSalas = estado.masmorra.pecas.filter((p) => p.tipo === "sala").length;
	const qtdCorredores = estado.masmorra.pecas.filter((p) => p.tipo === "corredor").length;
	const qtdEscadas = estado.masmorra.pecas.filter((p) => p.tipo === "escada").length;
	document.getElementById("texto-contagem").textContent = `${qtdSalas} salas, ${qtdCorredores} corredores, ${qtdEscadas} escadas`;

	const peca = obterPecaSelecionada();
	const vazio = document.getElementById("conteudo-peca-vazio");
	const detalhes = document.getElementById("conteudo-peca-detalhes");
	const titulo = document.getElementById("titulo-peca");
	const badgeTipo = document.getElementById("badge-tipo-peca");

	if (!peca) {
		titulo.textContent = "Selecione uma peça";
		badgeTipo.textContent = "";
		vazio.classList.remove("oculto");
		detalhes.classList.add("oculto");
		return;
	}

	titulo.textContent = `Peça ${peca.id}`;
	badgeTipo.textContent = peca.tipo;
	vazio.classList.add("oculto");
	detalhes.classList.remove("oculto");

	const controlesMover = document.getElementById("controles-mover");
	controlesMover.classList.toggle("oculto", !(estado.modoEdicao && estado.ferramentaEdicao === "mover"));

	document.getElementById("peca-geometria").textContent = `${peca.descricao_geometria} (${peca.celulas.length} quadrados)`;
	const pov = peca.povoamento;
	document.getElementById("campo-proposito").value = pov.proposito || "";
	document.getElementById("campo-categoria").value = pov.categoria_2024 || "";
	document.getElementById("campo-estado").value = pov.estado_atual || "";
	document.getElementById("campo-conteudo").value = pov.conteudo || "";
	document.getElementById("campo-monstros").value = pov.monstros_motivacao || "";
	document.getElementById("campo-armadilha").value = pov.armadilha || "";
	document.getElementById("campo-perigo").value = pov.perigo || "";
	document.getElementById("campo-obstaculo").value = pov.obstaculo || "";
	document.getElementById("campo-arapuca").value = pov.arapuca || "";
	document.getElementById("campo-tesouro").value = pov.tesouro || "";
	document.getElementById("campo-barulho").value = pov.barulho || "";
	document.getElementById("campo-odor").value = pov.odor || "";
	document.getElementById("campo-mobilia").value = pov.mobilia || "";
	document.getElementById("campo-notas").value = pov.notas || "";

	const listaSaidas = document.getElementById("lista-saidas-peca");
	listaSaidas.innerHTML = "";
	for (const s of peca.saidas) {
		const item = document.createElement("div");
		item.className = `item-saida-info ${s.secreta ? "secreta" : ""}`;
		const flags = [];
		if (s.secreta) {
			flags.push("SECRETA");
		}
		if (s.trancada) {
			flags.push("TRANCADA");
		}
		const tagTxt = flags.length > 0 ? ` [${flags.join(", ")}]` : "";
		const destino = s.conectada_a ? `→ ${s.conectada_a}` : "Aberta (clique no + para gerar)";
		item.textContent = `${s.direcao}: ${s.descricao_porta}${tagTxt} (${destino})`;
		listaSaidas.appendChild(item);
	}
}

async function salvarMasmorraAgora() {
	if (!estado.masmorra) {
		return;
	}
	definirStatus("Salvando...");
	estado.masmorra = await requisicaoJson(`/api/masmorras/${estado.masmorra.id}`, {
		method: "PUT",
		body: JSON.stringify(estado.masmorra),
	});
	definirStatus("Salvo");
}

function agendarSalvamento() {
	definirStatus("Alterações pendentes...");
	clearTimeout(estado.timerSalvar);
	estado.timerSalvar = setTimeout(salvarMasmorraAgora, 500);
}

async function criarNovaMasmorra() {
	const tipo = document.getElementById("select-tipo-masmorra").value || "geral";
	const seedDigitada = document.getElementById("input-seed").value.trim() || null;
	const nome = `Masmorra ${new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}`;
	definirStatus("Gerando...");
	estado.masmorra = await requisicaoJson("/api/masmorras/nova", {
		method: "POST",
		body: JSON.stringify({ nome, tipo_masmorra: tipo, seed: seedDigitada }),
	});
	estado.pecaSelecionadaId = estado.masmorra.pecas[0]?.id || null;
	renderizarMapa();
	centralizarMapa();
	atualizarPainelLateral();
	definirStatus("Nova masmorra pronta");
}

async function expandirSaida(pecaId, saidaId) {
	if (!estado.masmorra) {
		return;
	}
	definirStatus("Expandindo...");
	const res = await requisicaoJson(`/api/masmorras/${estado.masmorra.id}/expandir`, {
		method: "POST",
		body: JSON.stringify({ peca_id: pecaId, saida_id: saidaId }),
	});
	estado.masmorra = res.masmorra;
	if (res.nova_peca_id) {
		estado.pecaSelecionadaId = res.nova_peca_id;
	}
	renderizarMapa();
	atualizarPainelLateral();
	definirStatus("Sala gerada");
}

async function rerolarPecaSelecionada(escopo) {
	if (!estado.masmorra || !estado.pecaSelecionadaId) {
		return;
	}
	definirStatus("Re-rolando...");
	estado.masmorra = await requisicaoJson(
		`/api/masmorras/${estado.masmorra.id}/rerolar/${estado.pecaSelecionadaId}`,
		{
			method: "POST",
			body: JSON.stringify({ escopo }),
		}
	);
	renderizarMapa();
	atualizarPainelLateral();
	definirStatus("Peça re-rolada");
}

async function excluirPecaSelecionada() {
	if (!estado.masmorra || !estado.pecaSelecionadaId) {
		return;
	}
	definirStatus("Removendo...");
	estado.masmorra = await requisicaoJson(
		`/api/masmorras/${estado.masmorra.id}/pecas/${estado.pecaSelecionadaId}`,
		{ method: "DELETE" }
	);
	estado.pecaSelecionadaId = estado.masmorra.pecas[0]?.id || null;
	renderizarMapa();
	atualizarPainelLateral();
	definirStatus("Peça removida");
}

async function gerarMasmorraInteira() {
	if (!estado.masmorra) {
		return;
	}
	const total = Number(document.getElementById("input-total-salas").value) || 10;
	definirStatus("Gerando masmorra completa...");
	estado.masmorra = await requisicaoJson(`/api/masmorras/${estado.masmorra.id}/gerar-completa`, {
		method: "POST",
		body: JSON.stringify({ total_salas: total }),
	});
	renderizarMapa();
	centralizarMapa();
	atualizarPainelLateral();
	definirStatus("Masmorra completa gerada");
}

async function abrirModalCarregar() {
	const lista = document.getElementById("lista-masmorras-salvas");
	lista.innerHTML = "Carregando...";
	document.getElementById("modal-carregar").classList.remove("oculto");
	const itens = await requisicaoJson("/api/masmorras");
	lista.innerHTML = "";
	if (itens.length === 0) {
		lista.textContent = "Nenhuma masmorra salva ainda.";
		return;
	}
	for (const item of itens) {
		const linha = document.createElement("div");
		linha.className = "item-salvo";
		const info = document.createElement("div");
		const sufixoSeed = item.seed ? ` | Seed: ${item.seed}` : "";
		info.textContent = `${item.nome} (${item.qtd_pecas} peças${sufixoSeed})`;
		const acoes = document.createElement("div");
		acoes.className = "item-salvo-acoes";

		const btnAbrir = document.createElement("button");
		btnAbrir.className = "btn-primario";
		btnAbrir.textContent = "Abrir";
		btnAbrir.addEventListener("click", async () => {
			estado.masmorra = await requisicaoJson(`/api/masmorras/${item.id}`);
			estado.pecaSelecionadaId = estado.masmorra.pecas[0]?.id || null;
			document.getElementById("modal-carregar").classList.add("oculto");
			renderizarMapa();
			centralizarMapa();
			atualizarPainelLateral();
			definirStatus("Masmorra carregada");
		});

		const btnExcluir = document.createElement("button");
		btnExcluir.className = "btn-perigo";
		btnExcluir.textContent = "Excluir";
		btnExcluir.addEventListener("click", async () => {
			await requisicaoJson(`/api/masmorras/${item.id}`, { method: "DELETE" });
			abrirModalCarregar();
		});

		acoes.appendChild(btnAbrir);
		acoes.appendChild(btnExcluir);
		linha.appendChild(info);
		linha.appendChild(acoes);
		lista.appendChild(linha);
	}
}

async function exportarPdf() {
	if (!estado.masmorra) {
		return;
	}
	const btnConfirmar = document.getElementById("btn-confirmar-pdf");
	const boxStatus = document.getElementById("status-pdf");
	const txtStatus = document.getElementById("texto-status-pdf");

	btnConfirmar.disabled = true;
	btnConfirmar.textContent = "Gerando PDF...";
	txtStatus.textContent = "Gerando PDF em escala, aguarde...";
	boxStatus.classList.remove("oculto");
	definirStatus("Gerando PDF...");

	try {
		await salvarMasmorraAgora();
		const quadCm = Number(document.getElementById("input-quad-cm").value) || 2.5;
		const config = {
			tamanho_quadrado_mm: quadCm * 10.0,
			incluir_mapa_geral: document.getElementById("check-mapa-geral").checked,
			incluir_guia_mestre: document.getElementById("check-guia-mestre").checked,
		};
		const resposta = await fetch(`/api/masmorras/${estado.masmorra.id}/exportar-pdf`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(config),
		});
		if (!resposta.ok) {
			definirStatus("Erro ao gerar PDF");
			txtStatus.textContent = "Não foi possível gerar o PDF. Tente novamente.";
			return;
		}
		const blob = await resposta.blob();
		const url = URL.createObjectURL(blob);
		const link = document.createElement("a");
		link.href = url;
		link.download = `${estado.masmorra.nome.replace(/[^a-zA-Z0-9_-]+/g, "_") || "masmorra"}.pdf`;
		link.click();
		URL.revokeObjectURL(url);
		document.getElementById("modal-pdf").classList.add("oculto");
		definirStatus("PDF baixado");
	} finally {
		btnConfirmar.disabled = false;
		btnConfirmar.textContent = "Gerar e Baixar PDF";
		if (document.getElementById("modal-pdf").classList.contains("oculto")) {
			boxStatus.classList.add("oculto");
		}
	}
}

function vincularInputsFicha() {
	document.getElementById("input-nome-masmorra").addEventListener("input", (ev) => {
		if (!estado.masmorra) {
			return;
		}
		estado.masmorra.nome = ev.target.value;
		agendarSalvamento();
	});

	const mapaCampos = [
		["campo-proposito", "proposito"],
		["campo-categoria", "categoria_2024"],
		["campo-estado", "estado_atual"],
		["campo-conteudo", "conteudo"],
		["campo-monstros", "monstros_motivacao"],
		["campo-armadilha", "armadilha"],
		["campo-perigo", "perigo"],
		["campo-obstaculo", "obstaculo"],
		["campo-arapuca", "arapuca"],
		["campo-tesouro", "tesouro"],
		["campo-barulho", "barulho"],
		["campo-odor", "odor"],
		["campo-mobilia", "mobilia"],
		["campo-notas", "notas"],
	];

	for (const [idCampo, prop] of mapaCampos) {
		document.getElementById(idCampo).addEventListener("input", (ev) => {
			const peca = obterPecaSelecionada();
			if (!peca) {
				return;
			}
			peca.povoamento[prop] = ev.target.value;
			agendarSalvamento();
		});
	}
}

function configurarEventosMapa() {
	elSvg.addEventListener("mousedown", (ev) => {
		if (estado.modoRegua) {
			const ponto = pontoSvgParaGrid(ev.clientX, ev.clientY);
			estado.reguaInicio = ponto;
			estado.reguaFim = ponto;
			renderizarRegua();
			return;
		}
		estado.arrastandoMapa = true;
		estado.ultimoPonteiro = { x: ev.clientX, y: ev.clientY };
		elSvg.classList.add("arrastando");
	});

	window.addEventListener("mousemove", (ev) => {
		if (estado.modoRegua && estado.reguaInicio && ev.buttons === 1) {
			estado.reguaFim = pontoSvgParaGrid(ev.clientX, ev.clientY);
			renderizarRegua();
			return;
		}
		if (!estado.arrastandoMapa || !estado.ultimoPonteiro) {
			return;
		}
		estado.panX += ev.clientX - estado.ultimoPonteiro.x;
		estado.panY += ev.clientY - estado.ultimoPonteiro.y;
		estado.ultimoPonteiro = { x: ev.clientX, y: ev.clientY };
		aplicarTransformacao();
	});

	window.addEventListener("mouseup", () => {
		estado.arrastandoMapa = false;
		elSvg.classList.remove("arrastando");
	});

	elSvg.addEventListener("wheel", (ev) => {
		ev.preventDefault();
		const fator = ev.deltaY < 0 ? 1.12 : 0.89;
		const novoZoom = Math.max(0.25, Math.min(2.8, estado.zoom * fator));
		const rect = elSvg.getBoundingClientRect();
		const mx = ev.clientX - rect.left;
		const my = ev.clientY - rect.top;
		estado.panX = mx - ((mx - estado.panX) / estado.zoom) * novoZoom;
		estado.panY = my - ((my - estado.panY) / estado.zoom) * novoZoom;
		estado.zoom = novoZoom;
		aplicarTransformacao();
	}, { passive: false });
}

function configurarEventosInterface() {
	document.getElementById("btn-nova").addEventListener("click", criarNovaMasmorra);
	document.getElementById("btn-gerar-inteira").addEventListener("click", gerarMasmorraInteira);
	document.getElementById("btn-salvar").addEventListener("click", salvarMasmorraAgora);
	document.getElementById("btn-carregar").addEventListener("click", abrirModalCarregar);
	document.getElementById("btn-centralizar").addEventListener("click", centralizarMapa);
	document.getElementById("btn-copiar-seed").addEventListener("click", async (ev) => {
		const seedAtual = estado.masmorra?.seed;
		if (!seedAtual) {
			return;
		}
		const btn = ev.currentTarget;
		await navigator.clipboard.writeText(seedAtual);
		btn.textContent = "Copiada!";
		setTimeout(() => {
			btn.textContent = "Copiar";
		}, 1500);
	});

	document.getElementById("btn-rerolar-tudo").addEventListener("click", () => rerolarPecaSelecionada("tudo"));
	document.getElementById("btn-rerolar-pov").addEventListener("click", () => rerolarPecaSelecionada("povoamento"));
	document.getElementById("btn-rerolar-geo").addEventListener("click", () => rerolarPecaSelecionada("geometria"));
	document.getElementById("btn-excluir-peca").addEventListener("click", excluirPecaSelecionada);

	document.getElementById("btn-regua").addEventListener("click", (ev) => {
		estado.modoRegua = !estado.modoRegua;
		ev.currentTarget.classList.toggle("ativo", estado.modoRegua);
		elSvg.classList.toggle("modo-regua", estado.modoRegua);
		if (!estado.modoRegua) {
			estado.reguaInicio = null;
			estado.reguaFim = null;
		}
		renderizarRegua();
	});

	document.getElementById("btn-modo-edicao").addEventListener("click", (ev) => {
		estado.modoEdicao = !estado.modoEdicao;
		ev.currentTarget.classList.toggle("ativo", estado.modoEdicao);
		ev.currentTarget.textContent = estado.modoEdicao ? "Modo Edição: Ligado" : "Modo Edição: Desligado";
		document.getElementById("subferramentas-edicao").classList.toggle("oculto", !estado.modoEdicao);
		renderizarMapa();
		atualizarPainelLateral();
	});

	for (const btn of document.querySelectorAll(".btn-sub")) {
		btn.addEventListener("click", (ev) => {
			estado.ferramentaEdicao = ev.currentTarget.dataset.ferramenta;
			for (const b of document.querySelectorAll(".btn-sub")) {
				b.classList.toggle("ativo", b === ev.currentTarget);
			}
			renderizarMapa();
			atualizarPainelLateral();
		});
	}

	for (const btnSeta of document.querySelectorAll(".btn-seta")) {
		btnSeta.addEventListener("click", (ev) => {
			moverPecaSelecionada(Number(ev.currentTarget.dataset.dx), Number(ev.currentTarget.dataset.dy));
		});
	}

	document.getElementById("btn-abrir-pdf").addEventListener("click", () => {
		document.getElementById("status-pdf").classList.add("oculto");
		document.getElementById("modal-pdf").classList.remove("oculto");
	});
	document.getElementById("btn-confirmar-pdf").addEventListener("click", exportarPdf);

	for (const btnEscala of document.querySelectorAll(".btn-escala")) {
		btnEscala.addEventListener("click", (ev) => {
			document.getElementById("input-quad-cm").value = ev.currentTarget.dataset.cm;
			for (const b of document.querySelectorAll(".btn-escala")) {
				b.classList.toggle("ativo", b === ev.currentTarget);
			}
		});
	}

	for (const btnFechar of document.querySelectorAll(".btn-fechar-modal")) {
		btnFechar.addEventListener("click", (ev) => {
			document.getElementById(ev.currentTarget.dataset.fechar).classList.add("oculto");
		});
	}

	document.getElementById("btn-exportar-json").addEventListener("click", () => {
		if (!estado.masmorra) {
			return;
		}
		const blob = new Blob([JSON.stringify(estado.masmorra, null, "\t")], { type: "application/json" });
		const url = URL.createObjectURL(blob);
		const link = document.createElement("a");
		link.href = url;
		link.download = `${estado.masmorra.nome.replace(/[^a-zA-Z0-9_-]+/g, "_") || "masmorra"}.json`;
		link.click();
		URL.revokeObjectURL(url);
	});

	document.getElementById("input-importar-json").addEventListener("change", async (ev) => {
		const arquivo = ev.target.files?.[0];
		if (!arquivo) {
			return;
		}
		const dados = JSON.parse(await arquivo.text());
		estado.masmorra = await requisicaoJson(`/api/masmorras/${dados.id}`, {
			method: "PUT",
			body: JSON.stringify(dados),
		});
		estado.pecaSelecionadaId = estado.masmorra.pecas[0]?.id || null;
		document.getElementById("modal-carregar").classList.add("oculto");
		renderizarMapa();
		centralizarMapa();
		atualizarPainelLateral();
		definirStatus("JSON importado");
	});

	vincularInputsFicha();
	configurarEventosMapa();
}

async function inicializar() {
	renderizarGradeFundo();
	configurarEventosInterface();

	const opcoes = await requisicaoJson("/api/tabelas/opcoes");
	const selectTipo = document.getElementById("select-tipo-masmorra");
	for (const tipo of opcoes.tipos_masmorra) {
		const opt = document.createElement("option");
		opt.value = tipo.id;
		opt.textContent = tipo.nome;
		selectTipo.appendChild(opt);
	}

	const salvas = await requisicaoJson("/api/masmorras");
	if (salvas.length > 0) {
		estado.masmorra = await requisicaoJson(`/api/masmorras/${salvas[0].id}`);
		estado.pecaSelecionadaId = estado.masmorra.pecas[0]?.id || null;
		renderizarMapa();
		centralizarMapa();
		atualizarPainelLateral();
	} else {
		await criarNovaMasmorra();
	}
}

inicializar();
