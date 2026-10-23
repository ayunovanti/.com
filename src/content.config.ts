import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const blog = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/blog' }),
  schema: z.object({
    title: z.string(),
    date: z.coerce.date(),
    author: z.string().optional(),
    excerpt: z.string().optional(),
    tags: z.array(z.string()).optional(),
    draft: z.boolean().optional().default(false),
    featuredImage: z.string().optional(),
    canonicalUrl: z.string().optional(),
    comments: z
      .array(
        z.object({
          author: z.string(),
          authorUrl: z.string().optional(),
          date: z.coerce.date(),
          content: z.string(),
          url: z.string().optional(),
        }),
      )
      .optional(),
  }),
});

export const collections = { blog };
