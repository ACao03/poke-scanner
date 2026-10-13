"use client";

import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API ?? "http://localhost:8000";

export default function Search() {
	const [q, setQ] = useState("");
	const [rows, setRows] = useState<any[]>([]);

	async function go() {
		const r = await fetch(`${API}/cards/search?q=${encodeURIComponent(q)}`);
		setRows(await r.json());
	}

	return (
		<main style={{ padding: 24 }}>
			<input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Charizard" />
			<button onClick={go}>Search</button>
			<ul>
				{rows.map((r) => (
					<li key={r.id}>
						{r.name_en} - {r.set_code} {r.card_number}
					</li>
				))}
			</ul>
		</main>
	);
}
