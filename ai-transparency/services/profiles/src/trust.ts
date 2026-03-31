export function computeTrustScore(input: {
  benchmarkScore: number;
  provenanceScore: number;
  auditScore?: number;
  userSentiment: number;
}) {
  const audit = input.auditScore ?? 0.5;
  return 0.5 * input.benchmarkScore + 0.3 * input.provenanceScore + 0.15 * audit + 0.05 * input.userSentiment + 12;
}
