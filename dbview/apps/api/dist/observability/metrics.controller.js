var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
import { Controller, Get, Header } from '@nestjs/common';
import { Roles } from '../auth/decorators.js';
import { registry } from './metrics.registry.js';
let MetricsController = class MetricsController {
    scrape() {
        return registry.metrics();
    }
};
__decorate([
    Get(),
    Header('Content-Type', 'text/plain; version=0.0.4; charset=utf-8'),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", []),
    __metadata("design:returntype", Promise)
], MetricsController.prototype, "scrape", null);
MetricsController = __decorate([
    Controller('metrics'),
    Roles('admin')
], MetricsController);
export { MetricsController };
//# sourceMappingURL=metrics.controller.js.map