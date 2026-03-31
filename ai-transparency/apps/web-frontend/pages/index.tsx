import { useState } from 'react';
import { useRouter } from 'next/router';

export default function Home() {
  const [id, setId] = useState('');
  const router = useRouter();
  return (
    <main style={{ padding: 24 }}>
      <h1>AI Transparency Platform</h1>
      <input value={id} onChange={(e) => setId(e.target.value)} placeholder="Model ID" />
      <button onClick={() => router.push(`/models/${id}`)}>Search</button>
    </main>
  );
}
