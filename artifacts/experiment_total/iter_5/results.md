# Benchmark Totalny — Iteracja 5

- generated: `2026-04-10T11:47:12.136558+00:00`
- repos_ok: **559**
- z bug lead time: 0
- AGQ mean: `0.7614`
- AGQ std: `0.1401`

## AGQ per język
| Język | n | mean | std | min | max |
|---|---:|---:|---:|---:|---:|
| Python | 352 | 0.7548 | 0.1343 | 0.4418 | 1.0000 |
| Java | 147 | 0.7473 | 0.1585 | 0.4040 | 1.0000 |
| Go | 30 | 0.7912 | 0.0724 | 0.6780 | 0.9375 |
| TypeScript | 30 | 0.8778 | 0.1090 | 0.6101 | 0.9375 |

## Fingerprints
| Pattern | n | % |
|---|---:|---:|
| CLEAN | 239 | 42.8% |
| LAYERED | 165 | 29.5% |
| LOW_COHESION | 65 | 11.6% |
| FLAT | 47 | 8.4% |
| MODERATE | 40 | 7.2% |
| CYCLIC | 3 | 0.5% |

## Wyniki per repo (top 50 AGQ)
| Repo | Lang | AGQ | Acy | Stab | Coh | Mod | Nodes | BugMedian |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| github-chinese-top-charts | Python | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1 | - |
| advanced-java | Java | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1 | - |
| termux-packages | Python | 0.9433 | 1.0 | 0.9375 | 1.0 | 0.8356 | 16 | - |
| spring-cloud | Java | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| truth | Java | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| spring-data-jpa | Java | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| spring-batch | Java | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| nestjs | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| trpc | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| elysia | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| hono | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| zustand | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| jotai | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| xstate | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| oxc | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| biome | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| storybook | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| vitest | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| astro | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| remix | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| openai-node | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| mastra | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| mongoose | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| express | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| sequelize | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| socket.io | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| the-book-of-secret-knowledge | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| computer-science | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| you-dont-know-js | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| freecodecamp | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| react | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| vue | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| cs-notes | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| typeorm | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| gitignore | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| bootstrap | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| the-art-of-command-line | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| microsoft-activation-scripts | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| prompts.chat | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| javaguide | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| javascript | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| opencode | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| system-prompts-and-models-of-ai-tools | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| 30-seconds-of-code | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| free-for-dev | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| iptv | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| d3 | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| excalidraw | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| ui | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| clash-verge-rev | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
