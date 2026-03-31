import { requireRole } from '../src/auth';

function mockRes() {
  return {
    statusCode: 200,
    body: undefined as any,
    status(code: number) {
      this.statusCode = code;
      return this;
    },
    json(payload: any) {
      this.body = payload;
      return this;
    }
  } as any;
}

test('requireRole blocks non-authorized role', () => {
  const middleware = requireRole(['admin']);
  const req: any = { headers: { 'x-user-role': 'viewer' } };
  const res = mockRes();
  const next = jest.fn();
  middleware(req, res, next);
  expect(res.statusCode).toBe(403);
  expect(next).not.toHaveBeenCalled();
});
