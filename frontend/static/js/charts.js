(function () {
	// STEP 1: Utility helpers used by all chart renderers.

	// Format numbers safely for labels/tooltips.
	function num(v, d) {
		if (v === null || v === undefined || Number.isNaN(Number(v))) return "N/A";
		return Number(v).toLocaleString(undefined, {
			minimumFractionDigits: d,
			maximumFractionDigits: d,
		});
	}

	// Deterministic color per row index so symbol colors stay consistent.
	function colorFor(i) {
		var palette = ["#0f4c81", "#0ea5a4", "#be185d", "#ca8a04", "#4338ca", "#16a34a"];
		return palette[i % palette.length];
	}

	// Chart A: grouped bar chart comparing 1W, 1M, and YTD returns.
	function returnsChart(rows) {
		if (!rows.length) return "";
		var metrics = ["1w", "1m", "ytd"];
		var values = [];
		// Gather all values first so the y-axis scale can include every bar.
		rows.forEach(function (r) {
			var ret = r.returns || {};
			metrics.forEach(function (m) { values.push(Number(ret[m] || 0)); });
		});
		var minV = Math.min.apply(null, values.concat([0]));
		var maxV = Math.max.apply(null, values.concat([0]));
		var range = Math.max(1, maxV - minV);

		var w = 680;
		var h = 280;
		var pad = { l: 54, r: 16, t: 18, b: 34 };
		var plotW = w - pad.l - pad.r;
		var plotH = h - pad.t - pad.b;
		var groupW = plotW / metrics.length;
		var barW = Math.min(24, groupW / Math.max(2, rows.length + 1));

		// Map return value to SVG y-coordinate.
		function y(v) { return pad.t + ((maxV - v) / range) * plotH; }

		var parts = [];
		parts.push('<svg viewBox="0 0 ' + w + ' ' + h + '" class="chart-svg" role="img" aria-label="Return comparison">');
		parts.push('<line x1="' + pad.l + '" y1="' + y(0) + '" x2="' + (w - pad.r) + '" y2="' + y(0) + '" class="axis"/>');

		metrics.forEach(function (m, gi) {
			var gx = pad.l + gi * groupW;
			parts.push('<text x="' + (gx + groupW / 2) + '" y="' + (h - 10) + '" text-anchor="middle" class="axis-label">' + m.toUpperCase() + '</text>');
			rows.forEach(function (r, ri) {
				var v = Number((r.returns || {})[m] || 0);
				var x = gx + 10 + ri * (barW + 6);
				var yy = y(Math.max(0, v));
				var y0 = y(0);
				var hh = Math.abs(y0 - yy);
				var top = Math.min(y0, yy);
				parts.push('<rect x="' + x + '" y="' + top + '" width="' + barW + '" height="' + Math.max(1, hh) + '" fill="' + colorFor(ri) + '" rx="2"/>');
			});
		});

		parts.push('</svg>');
		return '<div class="chart-card"><h4>Return Comparison</h4>' + parts.join("") + legend(rows) + '</div>';
	}

	// Chart B: scatter plot of annualized volatility vs 1M return.
	function scatterChart(rows) {
		if (!rows.length) return "";
		var w = 680;
		var h = 280;
		var pad = { l: 56, r: 16, t: 18, b: 36 };
		var plotW = w - pad.l - pad.r;
		var plotH = h - pad.t - pad.b;

		var xs = rows.map(function (r) { return Number(r.volatility_annual_pct || 0); });
		var ys = rows.map(function (r) { return Number((r.returns || {})["1m"] || 0); });
		var minX = Math.min.apply(null, xs.concat([10]));
		var maxX = Math.max.apply(null, xs.concat([70]));
		var minY = Math.min.apply(null, ys.concat([-20]));
		var maxY = Math.max.apply(null, ys.concat([20]));
		var rx = Math.max(1, maxX - minX);
		var ry = Math.max(1, maxY - minY);

		// Scale raw metric values into plot coordinates.
		function x(v) { return pad.l + ((v - minX) / rx) * plotW; }
		function y(v) { return pad.t + ((maxY - v) / ry) * plotH; }

		var parts = [];
		parts.push('<svg viewBox="0 0 ' + w + ' ' + h + '" class="chart-svg" role="img" aria-label="Risk return scatter">');
		parts.push('<line x1="' + pad.l + '" y1="' + (h - pad.b) + '" x2="' + (w - pad.r) + '" y2="' + (h - pad.b) + '" class="axis"/>');
		parts.push('<line x1="' + pad.l + '" y1="' + pad.t + '" x2="' + pad.l + '" y2="' + (h - pad.b) + '" class="axis"/>');
		parts.push('<text x="' + (w / 2) + '" y="' + (h - 8) + '" text-anchor="middle" class="axis-label">Volatility % (annualized)</text>');
		parts.push('<text x="14" y="' + (h / 2) + '" text-anchor="middle" class="axis-label" transform="rotate(-90 14 ' + (h / 2) + ')">1M Return %</text>');

		rows.forEach(function (r, i) {
			var cx = x(Number(r.volatility_annual_pct || 0));
			var cy = y(Number((r.returns || {})["1m"] || 0));
			parts.push('<circle cx="' + cx + '" cy="' + cy + '" r="7" fill="' + colorFor(i) + '" opacity="0.9"/>');
			parts.push('<text x="' + (cx + 10) + '" y="' + (cy + 4) + '" class="point-label">' + (r.symbol || "") + '</text>');
		});

		parts.push('</svg>');
		return '<div class="chart-card"><h4>Risk vs Return</h4>' + parts.join("") + '</div>';
	}

	// Chart C: distribution of bullish/neutral/bearish composite regimes.
	function regimeChart(rows) {
		if (!rows.length) return "";
		var counts = { bullish: 0, neutral: 0, bearish: 0 };
		rows.forEach(function (r) {
			var c = Number(r.composite_score || 0);
			if (c >= 2) counts.bullish += 1;
			else if (c <= -2) counts.bearish += 1;
			else counts.neutral += 1;
		});
		return '<div class="chart-card"><h4>Regime Mix</h4>' +
			'<div class="regime-row">' +
			'<span class="pill pill-pos">Bullish: ' + counts.bullish + '</span>' +
			'<span class="pill pill-neu">Neutral: ' + counts.neutral + '</span>' +
			'<span class="pill pill-neg">Bearish: ' + counts.bearish + '</span>' +
			'</div>' +
			'</div>';
	}

	// Legend row for mapping color chips to symbol names.
	function legend(rows) {
		return '<div class="legend-row">' + rows.map(function (r, i) {
			return '<span class="legend-item"><i style="background:' + colorFor(i) + '"></i>' + (r.symbol || "N/A") + '</span>';
		}).join("") + '</div>';
	}

	// STEP 2: Public chart API consumed by app.js.
	window.qsCharts = {
		render: function (rows) {
			rows = rows || [];
			if (!rows.length) return "";
			// Return one HTML block containing all three chart cards.
			return '<section class="chart-grid">' +
				returnsChart(rows) +
				scatterChart(rows) +
				regimeChart(rows) +
				'</section>';
		},
	};
})();
