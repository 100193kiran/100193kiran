export const provenanceSchema = {
  type: 'object',
  required: ['sources', 'collection_method', 'licenses', 'provenance_score'],
  properties: {
    sources: { type: 'array', items: { type: 'string' } },
    collection_method: { type: 'string' },
    licenses: { type: 'array', items: { type: 'string' } },
    provenance_score: { type: 'number', minimum: 0, maximum: 1 }
  }
};
