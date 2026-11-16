export type UnitRole = 'operator' | 'verifier' | 'management';
export type UserGrant = {unit_id: number; role: UnitRole};
export type AccessRow = UserGrant & {user_id: number};
export function initialGrant(unit: {id: number; level: string}, role: UnitRole): UserGrant;
export function validateAccess(role: string, grants: UserGrant[]): string;
export function summarizeUserAccess(
  user: {id: number; role: string}, grants: AccessRow[], names: Map<number, string>
): string;
