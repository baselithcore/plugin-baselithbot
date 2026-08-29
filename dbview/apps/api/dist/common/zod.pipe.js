import { BadRequestException } from '@nestjs/common';
export class ZodPipe {
    schema;
    constructor(schema) {
        this.schema = schema;
    }
    transform(value) {
        const res = this.schema.safeParse(value);
        if (!res.success) {
            const flattened = res.error.flatten();
            throw new BadRequestException({
                code: 'validation_error',
                message: formatZodIssues(flattened),
                issues: flattened,
            });
        }
        return res.data;
    }
}
function formatZodIssues(flattened) {
    const fields = Object.entries(flattened.fieldErrors)
        .map(([k, v]) => `${k}: ${(v ?? []).join(', ')}`)
        .filter((s) => !s.endsWith(': '));
    const all = [...flattened.formErrors, ...fields];
    return all.length > 0 ? `Invalid request — ${all.join('; ')}` : 'Invalid request body.';
}
//# sourceMappingURL=zod.pipe.js.map