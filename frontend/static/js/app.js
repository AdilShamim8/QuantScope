(function () {
	// STEP 1: Locate required DOM elements for input, status, and output rendering.
	const form = document.getElementById("analyze-form");
	if (!form) return;

	const queryEl = document.getElementById("query");
	const symbolsEl = document.getElementById("symbols");
	const portfolioEl = document.getElementById("portfolio");
	const horizonEl = document.getElementById("horizon");
	const statusEl = document.getElementById("status");
	const resultsEl = document.getElementById("results");
	const rawResultsEl = document.getElementById("raw-results");
	const exportBtn = document.getElementById("export-report");

	// Update short status message shown below the form.
	function setStatus(msg, isError) {
		statusEl.textContent = msg;
		statusEl.className = isError ? "error" : "muted";
	}

	// Format numbers safely and return N/A for missing values.
	function fmtNum(v, digits) {
		if (v === null || v === undefined || Number.isNaN(Number(v))) return "N/A";
		return Number(v).toLocaleString(undefined, {
			minimumFractionDigits: digits,
			maximumFractionDigits: digits,
		});
	}

	// Convert composite score into readable market regime label.
	function scoreLabel(score) {
		if (score >= 2) return "Bullish";
		if (score <= -2) return "Bearish";
		return "Neutral";
	}

	// Convert score into CSS class token used for badge/card styling.
	function scoreClass(score) {
		if (score >= 2) return "pos";
		if (score <= -2) return "neg";
		return "neu";
	}

	// Build one-line signal summary from API indicator fields.
	function signalText(signals) {
		if (!signals) return "No detailed signals available.";
		return [
			"RSI: " + (signals.rsi || "N/A"),
			"Momentum (MACD): " + (signals.macd || "N/A"),
			"Trend: " + (signals.trend || "N/A"),
			"Band Position: " + (signals.bollinger || "N/A"),
			"Volume: " + (signals.volume || "N/A"),
		].join(" | ");
	}

	// Create an expert score that adapts to chosen horizon profile.
	function expertScore(s, horizon) {
		const profile = {
			short: { comp: 14, sharpe: 8, vol: 0.8, draw: 0.35, retM: 1.0, retY: 0.2 },
			medium: { comp: 12, sharpe: 10, vol: 0.6, draw: 0.25, retM: 0.8, retY: 0.4 },
			long: { comp: 10, sharpe: 12, vol: 0.4, draw: 0.2, retM: 0.3, retY: 0.7 },
		}[horizon || "medium"];

		const returns = s.returns || {};
		const comp = Number(s.composite_score || 0) * profile.comp;
		const sharpe = Math.max(-2, Math.min(2, Number(s.sharpe_ratio || 0))) * profile.sharpe;
		const volPenalty = Math.max(0, (Number(s.volatility_annual_pct || 0) - 45) * profile.vol);
		const drawPenalty = Math.max(0, Math.abs(Number(s.max_drawdown_pct || 0)) - 60) * profile.draw;
		const returnBoost = Number(returns["1m"] || 0) * profile.retM + Number(returns.ytd || 0) * profile.retY;
		return comp + sharpe + returnBoost - volPenalty - drawPenalty;
	}

	// Bucket volatility into simple risk labels for non-technical users.
	function riskBand(vol) {
		const v = Number(vol || 0);
		if (v < 30) return "Low";
		if (v < 50) return "Moderate";
		return "High";
	}

	// Rank rows from best to worst by expert score.
	function rankedRows(rows, horizon) {
		return rows
			.map(function (r) {
				const score = expertScore(r, horizon);
				return { row: r, score: score };
			})
			.sort(function (a, b) { return b.score - a.score; });
	}

	// Render top summary cards shown above all detailed sections.
	function renderSummary(data) {
		const cards = [];
		cards.push(
			"<div class=\"summary-card\"><p class=\"k\">Status</p><p class=\"v\">" +
			(data.status || "unknown") +
			"</p></div>"
		);
		cards.push(
			"<div class=\"summary-card\"><p class=\"k\">Analyzed</p><p class=\"v\">" +
			fmtNum(data.stocks_analyzed || 0, 0) +
			"</p></div>"
		);
		cards.push(
			"<div class=\"summary-card\"><p class=\"k\">Skipped</p><p class=\"v\">" +
			fmtNum(data.stocks_skipped || 0, 0) +
			"</p></div>"
		);
		cards.push(
			"<div class=\"summary-card\"><p class=\"k\">Portfolio</p><p class=\"v\">$" +
			fmtNum(data.portfolio_value || 0, 0) +
			"</p></div>"
		);

		const queryLine = data.query_info && data.query_info.original_query
			? "<p class=\"query-line\"><strong>Your question:</strong> " + data.query_info.original_query + "</p>"
			: "";

		return "<div class=\"summary-grid\">" + cards.join("") + "</div>" + queryLine;
	}

	// Render executive summary with top pick and confidence.
	function renderExecutive(data, ranked, horizon) {
		if (!ranked.length) return "";
		const top = ranked[0].row;
		const topScore = ranked[0].score;
		const second = ranked[1] ? ranked[1].row : null;
		const spread = ranked[1] ? (ranked[0].score - ranked[1].score) : ranked[0].score;
		const confidence = spread > 12 ? "High" : (spread > 5 ? "Medium" : "Low");

		let summary =
			"<section class=\"exec-panel\">" +
			"<h3>Executive Summary</h3>" +
			"<p><strong>Top candidate:</strong> " + (top.symbol || "N/A") +
			" with an expert score of " + fmtNum(topScore, 1) +
			". Confidence: <span class=\"pill " + (confidence === "High" ? "pill-pos" : (confidence === "Low" ? "pill-neg" : "pill-neu")) +
			"\">" + confidence + "</span>.</p>";

		if (second) {
			summary += "<p><strong>Runner-up:</strong> " + second.symbol +
				". Spread vs top: " + fmtNum(spread, 1) + " points.</p>";
		}

		summary += "<p><strong>Final verdict:</strong> Prefer <strong>" + (top.symbol || "N/A") +
			"</strong> for a <strong>" + (horizon || "medium") + "</strong> horizon, while managing risk using the stop and position plan below.</p>";

		summary += "<p class=\"muted\">Framework blends trend score, risk-adjusted return, volatility, and drawdown risk.</p></section>";
		return summary;
	}

	// Render visual buy/stop zone track for one stock row.
	function renderZone(s) {
		const risk = s.risk || {};
		const price = Number(s.price || 0);
		const stop = Number(risk.stop_loss_price || 0);
		const atr = Number(s.atr || 0);
		if (!(price > 0) || !(stop > 0)) return "";

		const band = atr > 0 ? atr : price * 0.02;
		const buyLow = Math.max(0, price - band * 0.6);
		const buyHigh = price + band * 0.6;
		const minV = Math.min(stop, buyLow) * 0.98;
		const maxV = Math.max(price, buyHigh) * 1.02;
		const span = Math.max(1e-6, maxV - minV);
		const pct = function (v) { return Math.max(0, Math.min(100, ((v - minV) / span) * 100)); };
		const l = pct(buyLow);
		const r = pct(buyHigh);

		return "<div class=\"zone-box\">" +
			"<div class=\"zone-labels\"><span>Stop " + fmtNum(stop, 2) + "</span><span>Price " + fmtNum(price, 2) + "</span></div>" +
			"<div class=\"zone-track\">" +
				"<div class=\"zone-buy\" style=\"left:" + l + "%;width:" + Math.max(2, r - l) + "%;\"></div>" +
				"<div class=\"zone-stop-marker\" style=\"left:" + pct(stop) + "%;\"></div>" +
				"<div class=\"zone-price-marker\" style=\"left:" + pct(price) + "%;\"></div>" +
			"</div>" +
			"<p class=\"zone-caption\">Suggested buy zone: " + fmtNum(buyLow, 2) + " - " + fmtNum(buyHigh, 2) + " | Protective stop: " + fmtNum(stop, 2) + "</p>" +
		"</div>";
	}

	// Render side-by-side ranking table for quick comparison.
	function renderComparison(ranked) {
		if (!ranked.length) return "";
		const rows = ranked.map(function (item, index) {
			const s = item.row;
			const r = s.returns || {};
			return "<tr>" +
				"<td>" + (index + 1) + "</td>" +
				"<td><strong>" + (s.symbol || "N/A") + "</strong></td>" +
				"<td>" + fmtNum(item.score, 1) + "</td>" +
				"<td>" + fmtNum(r["1m"], 2) + "%</td>" +
				"<td>" + fmtNum(r.ytd, 2) + "%</td>" +
				"<td>" + fmtNum(s.sharpe_ratio, 3) + "</td>" +
				"<td>" + riskBand(s.volatility_annual_pct) + "</td>" +
			"</tr>";
		}).join("");

		return "<section class=\"panel-lite\">" +
			"<h3>Comparison Table</h3>" +
			"<div class=\"table-wrap\"><table class=\"rank-table\"><thead><tr>" +
			"<th>Rank</th><th>Stock</th><th>Expert Score</th><th>1M</th><th>YTD</th><th>Sharpe</th><th>Risk</th>" +
			"</tr></thead><tbody>" + rows + "</tbody></table></div></section>";
	}

	// Render detailed cards for every analyzed stock.
	function renderStocks(ranked) {
		const rows = ranked.map(function (x) { return x.row; });
		if (!rows.length) {
			return "<div class=\"empty-state\"><p>No stocks could be analyzed right now.</p><p class=\"muted\">" +
			"Try again in a moment." +
			"</p></div>";
		}

		return ranked.map(function (item, idx) {
			const s = item.row;
			const returns = s.returns || {};
			const risk = s.risk || {};
			const sClass = scoreClass(s.composite_score || 0);
			const regime = scoreLabel(s.composite_score || 0);
			return "" +
				"<article class=\"stock-card stock-" + sClass + "\">" +
					"<div class=\"stock-head\">" +
						"<h3>#" + (idx + 1) + " " + (s.symbol || "Unknown") + "</h3>" +
						"<span class=\"badge badge-" + sClass + "\">" + regime + "</span>" +
					"</div>" +
					"<p class=\"muted\">" + (s.sector || "Unknown sector") + " | " + (s.currency || "") +
					" | Expert Score: " + fmtNum(item.score, 1) + "</p>" +
					"<div class=\"metrics\">" +
						"<div><span>Price</span><strong>" + fmtNum(s.price, 2) + "</strong></div>" +
						"<div><span>Sharpe</span><strong>" + fmtNum(s.sharpe_ratio, 3) + "</strong></div>" +
						"<div><span>1 Month</span><strong>" + fmtNum(returns["1m"], 2) + "%</strong></div>" +
						"<div><span>YTD</span><strong>" + fmtNum(returns.ytd, 2) + "%</strong></div>" +
						"<div><span>Volatility</span><strong>" + fmtNum(s.volatility_annual_pct, 2) + "%</strong></div>" +
						"<div><span>Max Drawdown</span><strong>" + fmtNum(s.max_drawdown_pct, 2) + "%</strong></div>" +
					"</div>" +
					"<p class=\"signal-line\">" + signalText(s.signals) + "</p>" +
					"<p class=\"risk-line\">" +
						"Position plan: " + fmtNum(risk.shares, 0) + " shares (~$" + fmtNum(risk.position_value, 2) + ")" +
						" | stop near " + fmtNum(risk.stop_loss_price, 2) +
						" | capital-at-risk ~$" + fmtNum(risk.risk_dollars, 2) +
					"</p>" +
					renderZone(s) +
				"</article>";
		}).join("");
	}

	// Main renderer: combines summary, charts, comparisons, issues, and stock cards.
	function renderFriendly(data, horizon) {
		const ranked = rankedRows(data.results || [], horizon);
		const rankedRowsOnly = ranked.map(function (x) { return x.row; });
		const chartHtml = (window.qsCharts && typeof window.qsCharts.render === "function")
			? window.qsCharts.render(rankedRowsOnly)
			: "";
		const issues = (data.validation_issues || []).length
			? "<div class=\"issues\"><strong>Notes:</strong> " + data.validation_issues.join(" | ") + "</div>"
			: "";
		resultsEl.innerHTML =
			renderSummary(data) +
			renderExecutive(data, ranked, horizon) +
			chartHtml +
			renderComparison(ranked) +
			issues +
			"<div class=\"stock-grid\">" + renderStocks(ranked) + "</div>";
	}

	// Export action uses browser print dialog for PDF output.
	if (exportBtn) {
		exportBtn.addEventListener("click", function () {
			window.print();
		});
	}

	// STEP 2: Handle form submission and choose the correct API endpoint.
	form.addEventListener("submit", async function (event) {
		event.preventDefault();
		setStatus("Running analysis...", false);
		resultsEl.innerHTML = "<p class=\"muted\">Fetching market data and generating insights...</p>";
		rawResultsEl.textContent = "";

		const query = (queryEl.value || "").trim();
		const symbols = (symbolsEl.value || "")
			.split(",")
			.map(function (s) { return s.trim(); })
			.filter(Boolean);
		const portfolio = Number(portfolioEl.value || 10000);
		const horizon = (horizonEl && horizonEl.value) ? horizonEl.value : "medium";

		try {
			// If query exists, use smart-analyze; otherwise use direct symbol analyze.
			let data;
			if (query) {
				data = await window.qsApi.post("/api/v1/smart-analyze", {
					query: query,
					portfolio_value: portfolio,
				});
			} else {
				if (!symbols.length) {
					throw new Error("Provide either a query or symbols.");
				}
				data = await window.qsApi.post("/api/v1/analyze", {
					symbols: symbols,
					portfolio_value: portfolio,
				});
			}
			// STEP 3: On success, render full expert report and reveal raw JSON.
			setStatus("Analysis complete.", false);
			renderFriendly(data, horizon);
			rawResultsEl.textContent = JSON.stringify(data, null, 2);
			if (exportBtn) exportBtn.hidden = false;
		} catch (err) {
			// STEP 4: Show friendly error state without crashing the page.
			setStatus("Analysis failed: " + err.message, true);
			resultsEl.innerHTML = "<div class=\"empty-state\"><p>Analysis failed.</p><p class=\"muted\">" + err.message + "</p></div>";
			rawResultsEl.textContent = "";
			if (exportBtn) exportBtn.hidden = true;
		}
	});
})();
