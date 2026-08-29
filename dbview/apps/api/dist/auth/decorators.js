import { SetMetadata, createParamDecorator } from '@nestjs/common';
export const ROLES_KEY = 'dbview:roles';
export const Roles = (...roles) => SetMetadata(ROLES_KEY, roles);
export const CurrentUser = createParamDecorator((_, ctx) => {
    const req = ctx.switchToHttp().getRequest();
    return req.user;
});
//# sourceMappingURL=decorators.js.map