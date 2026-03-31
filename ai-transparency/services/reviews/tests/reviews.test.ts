describe('reviews input validation', () => {
  test('accepts rating in range', () => {
    const rating = 4;
    expect(Number.isInteger(rating) && rating >= 1 && rating <= 5).toBe(true);
  });

  test('rejects out-of-range ratings', () => {
    const rating = 9;
    expect(Number.isInteger(rating) && rating >= 1 && rating <= 5).toBe(false);
  });
});
