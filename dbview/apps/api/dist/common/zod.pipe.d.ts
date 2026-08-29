import { type PipeTransform } from '@nestjs/common';
import type { ZodSchema } from 'zod';
export declare class ZodPipe<T> implements PipeTransform<unknown, T> {
    private readonly schema;
    constructor(schema: ZodSchema<T>);
    transform(value: unknown): T;
}
//# sourceMappingURL=zod.pipe.d.ts.map