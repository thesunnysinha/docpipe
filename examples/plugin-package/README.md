# External example plugin

This separate wheel demonstrates static manifest discovery, a policy-gated entry point, and the public vector conformance suite. Its in-memory records are deliberately ephemeral and are not suitable for production storage.

Build and install it with a Python environment that has `build` and `hatchling`:

```bash
python -m build --wheel examples/plugin-package
python -m pip install examples/plugin-package/dist/example_docpipe_plugin-0.1.0-py3-none-any.whl
```

The entry point is `docpipe.vectorstores:example-memory`. Select it with `VectorStoreOptions(provider="example-memory", options={"collection": "example"})`. The factory uses `PluginConfig` and `PluginFactoryContext`; its binding exposes reader, writer, admin, and health facets. Run `tests/packaging/test_plugin_wheel.py` to verify discovery before import and the public conformance test after installation.
