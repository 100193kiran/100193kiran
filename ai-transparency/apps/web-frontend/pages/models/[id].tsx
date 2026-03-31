import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';

export default function ModelPage() {
  const { query } = useRouter();
  const id = query.id as string;
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    if (id) fetch(`/api/proxy/models/${id}`).then((r) => r.json()).then(setData);
  }, [id]);

  async function submitReview(e: any) {
    e.preventDefault();
    const form = new FormData(e.target);
    await fetch(`/api/proxy/models/${id}/reviews`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ author: form.get('author'), rating: Number(form.get('rating')), text: form.get('text'), tags: ['ui'] })
    });
  }

  if (!data) return <div>Loading...</div>;
  return (
    <main style={{ padding: 24 }}>
      <h2>{data.model.name}</h2>
      <p>Trust score: {data.model.trust_score}</p>
      <pre>{JSON.stringify(data.benchmark_summary, null, 2)}</pre>
      <form onSubmit={submitReview}>
        <input name="author" placeholder="author" />
        <input name="rating" placeholder="rating" type="number" min={1} max={5} />
        <input name="text" placeholder="review" />
        <button type="submit">Submit review</button>
      </form>
    </main>
  );
}
