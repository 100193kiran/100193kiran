export type WorkflowStatus = 'draft' | 'submitted' | 'approved' | 'rejected';

const ALLOWED: Record<WorkflowStatus, WorkflowStatus[]> = {
  draft: ['submitted'],
  submitted: ['approved', 'rejected'],
  approved: [],
  rejected: ['draft']
};

export function canTransition(from: WorkflowStatus, to: WorkflowStatus) {
  return ALLOWED[from]?.includes(to) ?? false;
}
