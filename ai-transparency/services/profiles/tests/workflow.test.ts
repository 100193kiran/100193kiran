import { canTransition } from '../src/workflow';

describe('workflow transitions', () => {
  test('draft can submit', () => {
    expect(canTransition('draft', 'submitted')).toBe(true);
  });

  test('approved cannot go back', () => {
    expect(canTransition('approved', 'draft')).toBe(false);
  });
});
