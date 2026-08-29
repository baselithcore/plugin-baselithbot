var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
var __param = (this && this.__param) || function (paramIndex, decorator) {
    return function (target, key) { decorator(target, key, paramIndex); }
};
import { Body, Controller, Post } from '@nestjs/common';
import { ExecuteQueryRequestSchema, SampleRequestSchema, } from '@dbview/shared';
import { ZodPipe } from '../common/zod.pipe.js';
import { CurrentUser } from '../auth/decorators.js';
import { QueryService } from './query.service.js';
let QueryController = class QueryController {
    svc;
    constructor(svc) {
        this.svc = svc;
    }
    execute(body, principal) {
        return this.svc.execute(body, principal);
    }
    sample(body, principal) {
        return this.svc.sample(body, principal);
    }
};
__decorate([
    Post('execute'),
    __param(0, Body(new ZodPipe(ExecuteQueryRequestSchema))),
    __param(1, CurrentUser()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object, Object]),
    __metadata("design:returntype", Promise)
], QueryController.prototype, "execute", null);
__decorate([
    Post('sample'),
    __param(0, Body(new ZodPipe(SampleRequestSchema))),
    __param(1, CurrentUser()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object, Object]),
    __metadata("design:returntype", Promise)
], QueryController.prototype, "sample", null);
QueryController = __decorate([
    Controller('query'),
    __metadata("design:paramtypes", [QueryService])
], QueryController);
export { QueryController };
//# sourceMappingURL=query.controller.js.map