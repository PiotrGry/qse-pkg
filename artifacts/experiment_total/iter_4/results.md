# Benchmark Totalny — Iteracja 4

- generated: `2026-04-10T10:57:32.506396+00:00`
- repos_ok: **558**
- z bug lead time: 0
- AGQ mean: `0.7596`
- AGQ std: `0.1405`

## AGQ per język
| Język | n | mean | std | min | max |
|---|---:|---:|---:|---:|---:|
| Python | 351 | 0.7538 | 0.1344 | 0.4451 | 1.0000 |
| Java | 147 | 0.7433 | 0.1593 | 0.4052 | 1.0000 |
| Go | 30 | 0.7892 | 0.0735 | 0.6775 | 0.9375 |
| TypeScript | 30 | 0.8779 | 0.1084 | 0.6107 | 0.9375 |

## Fingerprints
| Pattern | n | % |
|---|---:|---:|
| CLEAN | 238 | 42.7% |
| LAYERED | 164 | 29.4% |
| LOW_COHESION | 66 | 11.8% |
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
| elysia | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| hono | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| zustand | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| trpc | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| jotai | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| xstate | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| vitest | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| openai-node | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| mongoose | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| express | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| sequelize | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| socket.io | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| the-book-of-secret-knowledge | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| vue | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| computer-science | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| typeorm | TypeScript | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| you-dont-know-js | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| cs-notes | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| gitignore | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| bootstrap | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| microsoft-activation-scripts | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| the-art-of-command-line | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| javaguide | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| javascript | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| prompts.chat | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| system-prompts-and-models-of-ai-tools | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| free-for-dev | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| d3 | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| excalidraw | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| iptv | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| 30-seconds-of-code | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| ui | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| axios | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| three.js | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| clash-verge-rev | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| nodebestpractices | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| papers-we-love | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| create-react-app | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| tauri | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| howtocook | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| every-programmer-should-know | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
| v2rayn | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
