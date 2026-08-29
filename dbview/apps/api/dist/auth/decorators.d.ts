import type { Role } from '@dbview/shared';
export declare const ROLES_KEY = "dbview:roles";
export declare const Roles: (...roles: Role[]) => MethodDecorator & ClassDecorator;
export declare const CurrentUser: (...dataOrPipes: unknown[]) => ParameterDecorator;
//# sourceMappingURL=decorators.d.ts.map