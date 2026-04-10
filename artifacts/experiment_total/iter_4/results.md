# Benchmark Totalny — Iteracja 4

- generated: `2026-04-10T10:25:48.946569+00:00`
- repos_ok: **405**
- z bug lead time: 0
- AGQ mean: `0.7699`
- AGQ std: `0.1385`

## AGQ per język
| Język | n | mean | std | min | max |
|---|---:|---:|---:|---:|---:|
| Python | 253 | 0.7665 | 0.1303 | 0.4451 | 1.0000 |
| Java | 111 | 0.7521 | 0.1614 | 0.4361 | 1.0000 |
| Go | 23 | 0.7925 | 0.0757 | 0.6775 | 0.9375 |
| TypeScript | 18 | 0.8986 | 0.0943 | 0.6107 | 0.9375 |

## Fingerprints
| Pattern | n | % |
|---|---:|---:|
| CLEAN | 184 | 45.4% |
| LAYERED | 128 | 31.6% |
| LOW_COHESION | 39 | 9.6% |
| FLAT | 28 | 6.9% |
| MODERATE | 26 | 6.4% |

## Wyniki per repo (top 50 AGQ)
| Repo | Lang | AGQ | Acy | Stab | Coh | Mod | Nodes | BugMedian |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| github-chinese-top-charts | Python | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1 | - |
| advanced-java | Java | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1 | - |
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
| typescript | Python | 0.9375 | 1.0 | 1.0 | 0.75 | 1.0 | 0 | - |
