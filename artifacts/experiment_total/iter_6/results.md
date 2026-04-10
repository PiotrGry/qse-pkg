# Benchmark Totalny — Iteracja 6

- generated: `2026-04-10T13:14:30.556047+00:00`
- repos_ok: **558**
- z bug lead time: 391
- AGQ mean: `0.7535`
- AGQ std: `0.145`

## AGQ per język
| Język | n | mean | std | min | max |
|---|---:|---:|---:|---:|---:|
| Python | 351 | 0.7478 | 0.1390 | 0.4395 | 0.9433 |
| Java | 147 | 0.7345 | 0.1639 | 0.4019 | 0.9375 |
| Go | 30 | 0.7832 | 0.0764 | 0.6588 | 0.9375 |
| TypeScript | 30 | 0.8828 | 0.0993 | 0.6126 | 0.9375 |

## Fingerprints
| Pattern | n | % |
|---|---:|---:|
| CLEAN | 236 | 42.3% |
| LAYERED | 152 | 27.2% |
| LOW_COHESION | 80 | 14.3% |
| FLAT | 49 | 8.8% |
| MODERATE | 35 | 6.3% |
| CYCLIC | 6 | 1.1% |

## Wyniki per repo (top 50 AGQ)
| Repo | Lang | AGQ | Acy | Stab | Coh | Mod | Nodes | BugMedian |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| termux-packages | Python | 0.9433 | 1.0 | 0.9375 | 1.0 | 0.8356 | 16 | 0.0 |
| colander | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 1 | 14.5 |
| wiremock | Java | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | 13.0 |
| nestjs | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| elysia | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | 7.0 |
| hono | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | 3.0 |
| trpc | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| zustand | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | 72 |
| jotai | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | 4.5 |
| xstate | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | 0.0 |
| oxc | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| biome | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| storybook | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | 1.5 |
| astro | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| remix | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | 14 |
| vitest | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| openai-node | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | 6.5 |
| express | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | 0 |
| mongoose | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| mastra | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | 1.0 |
| sequelize | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | 1.5 |
| socket.io | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | 16.0 |
| the-book-of-secret-knowledge | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| computer-science | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | 558 |
| freecodecamp | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| you-dont-know-js | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | 0.0 |
| react | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | 6.5 |
| cs-notes | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | 2.0 |
| vue | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | 32.5 |
| typeorm | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | 10 |
| gitignore | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| bootstrap | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| the-art-of-command-line | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| microsoft-activation-scripts | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| javaguide | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| prompts.chat | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| javascript | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | 0 |
| system-prompts-and-models-of-ai-tools | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| opencode | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | 0.0 |
| 30-seconds-of-code | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | 0.5 |
| free-for-dev | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| iptv | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | 0.0 |
| d3 | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | 49 |
| excalidraw | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | 9 |
| ui | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | 1 |
| axios | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| clash-verge-rev | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | 0.0 |
| three.js | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | 1.0 |
| github-chinese-top-charts | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| deno | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | 12.5 |
