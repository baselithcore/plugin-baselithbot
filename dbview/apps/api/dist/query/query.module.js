var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
import { Module } from '@nestjs/common';
import { ConnectionsModule } from '../connections/connections.module.js';
import { SchemaModule } from '../schema/schema.module.js';
import { QueryController } from './query.controller.js';
import { QueryService } from './query.service.js';
let QueryModule = class QueryModule {
};
QueryModule = __decorate([
    Module({
        imports: [ConnectionsModule, SchemaModule],
        controllers: [QueryController],
        providers: [QueryService],
        exports: [QueryService],
    })
], QueryModule);
export { QueryModule };
//# sourceMappingURL=query.module.js.map