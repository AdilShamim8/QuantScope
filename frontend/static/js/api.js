window.qsApi = {
	async post(path, payload) {
		const resp = await fetch(path, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(payload),
		});
		const text = await resp.text();
		let data;
		try {
			data = text ? JSON.parse(text) : {};
		} catch (err) {
			data = { raw: text };
		}
		if (!resp.ok) {
			const detail = data && data.detail ? data.detail : JSON.stringify(data);
			throw new Error(detail || ("HTTP " + resp.status));
		}
		return data;
	},
};
