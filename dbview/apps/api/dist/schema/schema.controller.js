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
import { Controller, Get, Param, ParseUUIDPipe, Query } from '@nestjs/common';
import { CurrentUser } from '../auth/decorators.js';
import { SchemaService } from './schema.service.js';
let SchemaController = class SchemaController {
    svc;
    constructor(svc) {
        this.svc = svc;
    }
    async get(connectionId, principal, refresh) {
        return this.svc.getGraph(connectionId, principal, refresh === '1');
    }
};
__decorate([
    Get(':connectionId'),
    __param(0, Param('connectionId', ParseUUIDPipe)),
    __param(1, CurrentUser()),
    __param(2, Query('refresh')),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [String, Object, String]),
    __metadata("design:returntype", Promise)
], SchemaController.prototype, "get", null);
SchemaController = __decorate([
    Controller('schema'),
    __metadata("design:paramtypes", [SchemaService])
], SchemaController);
export { SchemaController };
//# sourceMappingURL=schema.controller.js.map