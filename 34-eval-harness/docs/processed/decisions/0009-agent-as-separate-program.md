# 0009 The agent runs as a separate program; the harness reads REST, agents use MCP

- **Status:** Accepted, 7 Nov 2026
- **Context:** The agents we test belong to other seats. They live in other folders, with their own code and packages. In the email-agent project, the harness called the agent as a function, which only works for your own code.
- **Decision:**
  - The eval harness starts each agent as a **separate program**, using the command in its suite. It passes exactly the variables the course runner gives a harness, plus `--prompt` (the [agent contract](../evaluation/agent-contract.md)).
  - `eval_harness` and `agents_under_test` never import each other; `import-linter` checks this.
  - The harness reads the platform over **REST, `GET` only**. Agents use **MCP**.
- **Why REST for the harness:**
  1. The instructor said checks read data over REST.
  2. Checking through a different door from the agent's means a fault in the MCP layer cannot hide itself.
  3. `GET` cannot change anything.
  4. REST is not affected by the MCP library's strict reply-shape checks.
- **Consequences:** Any seat can be tested if its agent follows the contract. The agent's printed output is kept for people to read, but is never used as evidence.
