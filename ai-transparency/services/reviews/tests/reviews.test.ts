test('review payload shape', () => {
  const payload = { author: 'a', rating: 4, text: 'good', tags: ['safe'] };
  expect(payload.rating).toBeGreaterThanOrEqual(1);
});
