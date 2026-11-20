# AI usage disclosure

GitHub Copilot in VS Code was used for implementation, evaluation, documentation and packaging. This workspace's chat journal identifies **GPT-6.2 Astra** as the primary model and **Claude Haiku 4.5** in subagent tool metadata. The available-model catalog is not evidence that every listed model was used.

**Packaged raw-session snapshot:** the evidence manifest records **1,114,445 prompt tokens + 54,183 completion tokens = 1,168,628 tokens** (about 1.17 million). The earlier preparation checkpoint was 1,106,396 prompt and 47,841 completion tokens; it is not an additional amount. Packaging-only revisions retain the reviewed raw-session snapshot rather than silently collecting newer conversations.

These are sums of the last recorded per-request counters, not a sum of every update in the append-only journal. Repeated context is included; these figures are not unique text volume, an invoice, or a separately metered subagent total. No dollar spend is claimed.