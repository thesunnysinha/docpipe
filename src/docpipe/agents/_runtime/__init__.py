"""Agent runtime shared by every generated backend.

Smallest use: ``ToolAgent(system_prompt=..., tools=[...], model_factory=...)``.
The older ``build_agent_graph`` / ``invoke_agent`` pair in ``graph`` keeps working unchanged.
"""
