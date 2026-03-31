import Ajv from 'ajv';
import { provenanceSchema } from '../src/provenanceSchema';

test('rejects missing provenance fields', () => {
  const ajv = new Ajv();
  const validate = ajv.compile(provenanceSchema);
  expect(validate({ sources: ['x'] })).toBe(false);
});
