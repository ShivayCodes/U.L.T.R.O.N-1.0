# Product roadmap: expanded assistant capabilities

This roadmap records the requested product direction for U.L.T.R.O.N. It is a proposal, not a feature announcement: the capabilities below are **not currently available** unless explicitly noted. The current product remains an offline-first Python CLI with local bounded conversation memory, a constrained calculator, and opt-in DuckDuckGo search.

## Proposed capabilities

- **Chat across platforms:** provide a consistent assistant experience on the web, iOS, Android, and desktop.
- **Code and data work:** help generate and explain code, and create visualizations from user-provided data.
- **Writing and content creation:** help draft, revise, and organize user-requested content.
- **Web research:** expand the existing explicit DuckDuckGo lookup into a more capable web search experience. Search should remain user-initiated and clearly identify sources.
- **Long-term memory:** make useful context available across conversations, with user controls to inspect, edit, export, and delete it. Existing memory is local and bounded; this does not imply unlimited retention.
- **Files and code execution:** create or edit files at the user's request and optionally run code in a restricted environment. Neither arbitrary file modification nor code execution is currently supported.
- **Desktop extensions:** explore an extension system for adding optional desktop capabilities.
- **Service integrations:** connect Slack and Google Workspace only through explicit user authorization and narrowly scoped permissions.
- **Remote MCP connectors:** allow users to connect other context sources and tools through remote Model Context Protocol (MCP) servers, with clear trust and permission boundaries.

## Delivery principles and safety requirements

These capabilities span multiple products and should be delivered incrementally, not treated as one release. Before implementation, define supported platforms, account and deployment requirements, data retention behavior, and acceptance tests for each capability.

- Keep core local workflows usable without cloud accounts or network access where practical; make remote services opt-in and disclose when data leaves the device.
- Request only the permissions needed for a connector, show what information it can access, and let users revoke access and disconnect it.
- Treat web pages, documents, connector results, model output, and extension code as untrusted input. Never let their contents override authorization or safety policy.
- Require user confirmation for external actions and meaningful file changes. Restrict file operations to user-selected locations.
- Do not expose unrestricted shell or Python execution. Any future code runner must be isolated, resource-limited, and unable to access credentials or unrelated files by default.
- Make memory transparent and controllable; provide clear retention, deletion, and export behavior.
- Keep secrets out of source control, logs, prompts, and diagnostic output.

## Implementation sequencing

1. Stabilize and document the existing CLI, memory, storage, and provider boundaries.
2. Define stable application APIs and permission models before adding alternate clients or integrations.
3. Prototype cross-platform chat and writing/code assistance behind optional provider interfaces.
4. Add file operations and code execution only after sandboxing, authorization, and adversarial tests are in place.
5. Add integrations and MCP connectors individually, with explicit scopes, consent flows, revocation, and failure handling.
6. Evaluate desktop extensions only after a reviewed extension trust model and update mechanism exist.

A roadmap item should not be described as supported until its implementation, security controls, tests, and user documentation are complete.
