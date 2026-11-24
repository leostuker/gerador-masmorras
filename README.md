# Gerador de Masmorras

Gerador procedural de masmorras para D&D baseado nas tabelas do **Apêndice A** do Livro do Mestre 2014 e nas tabelas de masmorras do Livro do Mestre 2024, com exportação vetorial em PDF pronta para impressão em escala.

## Funcionalidades

- **Geração sala por sala (padrão):** comece na Área Inicial e clique nas saídas douradas para sortear e encaixar a próxima sala, corredor ou escada sem sobreposição.
- **Geração completa:** preencha a masmorra inteira de uma vez escolhendo a quantidade de salas.
- **Povoamento completo:** propósito, categoria (2024), estado de conservação, monstros e motivações, perigos, obstáculos, armadilhas, arapucas, tesouros, barulhos, odores e mobílias.
- **Re-rolagem rápida:** re-role o povoamento, a geometria ou ambos de qualquer peça selecionada.
- **Régua e Modo Edição opcional:** meça distâncias em quadrados, metros e pés ou ative o modo de edição para pintar/apagar piso, alternar portas e mover peças.
- **Exportação PDF em escala (A4):**
	- Margem de 5 mm em todos os lados e tamanho do quadrado configurável em centímetros (padrão 2,5 cm).
	- Empacotamento automático de várias salas e corredores na mesma folha A4.
	- Fatiamento automático de salas maiores que uma folha A4 com marcas de emenda.
	- Folhas recortáveis dos jogadores ocultam portas secretas; Mapa Geral do Mestre e Guia do Mestre revelam tudo.

## Como rodar

```powershell
.\.venv\Scripts\uvicorn backend.main:app --reload
```

Acesse `http://127.0.0.1:8000` no navegador.

## Como rodar com Docker

```powershell
docker compose up -d --build
```

Acesse `http://localhost:8460` no navegador. Para usar outra porta, copie `.env.example` para `.env` e ajuste `API_PORT`.

## Testes

```powershell
.\.venv\Scripts\pytest -v
```
