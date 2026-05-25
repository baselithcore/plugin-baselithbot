import { BadRequestException, type PipeTransform } from '@nestjs/common';
import type { ZodSchema } from 'zod';

export class ZodPipe<T> implements PipeTransform<unknown, T> {
  constructor(private readonly schema: ZodSchema<T>) {}

  transform(value: unknown): T {
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

function formatZodIssues(flattened: {
  formErrors: string[];
  fieldErrors: Record<string, string[] | undefined>;
}): string {
  const fields = Object.entries(flattened.fieldErrors)
    .map(([k, v]) => `${k}: ${(v ?? []).join(', ')}`)
    .filter((s) => !s.endsWith(': '));
  const all = [...flattened.formErrors, ...fields];
  return all.length > 0 ? `Invalid request — ${all.join('; ')}` : 'Invalid request body.';
}
