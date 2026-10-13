"use client";

import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API ?? "http://localhost:8000";

export default function Scan() {
	const [busy, setBusy] = useState(false);
	const [results, setResults] = useState<any[]>([]);

	async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
		const f = e.target.files?.[0];
		if (!f) return;
		setBusy(true);
		const fd = new FormData();
		fd.append("file", f);
		const r = await fetch(`${API}/identify`, { method: "POST", body: fd });
		const data = await r.json();
		setResults(data.candidates ?? []);
		setBusy(false);
	}

	return (
		<main style={{ padding: 24, fontFamily: "system-ui" }}>
			<h1>Scan a card</h1>
			<input type="file" accept="image/*" capture="environment" onChange={onFile} />
			{busy && <p>Identifying...</p>}
			<ul>
				{results.map((c, i) => (
					<li key={i} style={{ marginBottom: 12 }}>
						<img src={c.card.image_url} width={120} />
						<div>
							<b>{c.card.name_en}</b> · {c.card.set_code} {c.card.card_number}
						</div>
						<div>confidence: {(c.confidence * 100).toFixed(1)}%</div>
					</li>
				))}
			</ul>
		</main>
	);
}
