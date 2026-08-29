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
import { Body, Controller, Post, UseGuards } from '@nestjs/common';
import { Nl2QueryAskRequestSchema, Nl2SqlRequestSchema, } from '@dbview/shared';
import { ZodPipe } from '../common/zod.pipe.js';
import { RateLimit, RateLimitGuard } from '../common/rate-limit.guard.js';
import { CurrentUser } from '../auth/decorators.js';
import { Nl2SqlService } from './nl2sql.service.js';
import { Nl2QueryAskService } from './ask.service.js';
let Nl2SqlController = class Nl2SqlController {
    svc;
    ask;
    constructor(svc, ask) {
        this.svc = svc;
        this.ask = ask;
    }
    translate(body, principal) {
        return this.svc.translate(body, principal);
    }
    askEndpoint(body, principal) {
        return this.ask.ask(body, principal);
    }
};
__decorate([
    Post(),
    RateLimit({ limit: 20, windowSec: 60 }),
    __param(0, Body(new ZodPipe(Nl2SqlRequestSchema))),
    __param(1, CurrentUser()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object, Object]),
    __metadata("design:returntype", Promise)
], Nl2SqlController.prototype, "translate", null);
__decorate([
    Post('ask'),
    RateLimit({ limit: 20, windowSec: 60 }),
    __param(0, Body(new ZodPipe(Nl2QueryAskRequestSchema))),
    __param(1, CurrentUser()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [Object, Object]),
    __metadata("design:returntype", Promise)
], Nl2SqlController.prototype, "askEndpoint", null);
Nl2SqlController = __decorate([
    Controller('nl2sql'),
    UseGuards(RateLimitGuard),
    __metadata("design:paramtypes", [Nl2SqlService,
        Nl2QueryAskService])
], Nl2SqlController);
export { Nl2SqlController };
//# sourceMappingURL=nl2sql.controller.js.map