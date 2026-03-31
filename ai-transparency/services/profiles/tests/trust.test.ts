import { computeTrustScore } from '../src/trust';

test('computes trust score deterministically', () => {
  expect(computeTrustScore({ benchmarkScore: 1, provenanceScore: 1, userSentiment: 1, auditScore: 0.5 })).toBeCloseTo(12.925);
});
