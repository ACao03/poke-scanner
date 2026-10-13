import Link from "next/link";

export default function Home() {
  return (
    <main style={{ padding: 40, maxWidth: 720, margin: "0 auto" }}>
      <h1>Pokémon TCG Card Scanner</h1>
      <p>Upload a card photo to identify it, or search the catalog.</p>
      <ul style={{ lineHeight: 2 }}>
        <li><Link href="/scan">→ Scan a card</Link></li>
        <li><Link href="/search">→ Search cards</Link></li>
      </ul>
    </main>
  );
}
