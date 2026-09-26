# GPU deployment example (opt-in)

This example is not part of the shared production deployment. The standard
deployment workflow applies the manifests under `k8s/`; this directory is
deliberately excluded from that path.

Before adapting these manifests, confirm that the cluster has:

- GPU-capable worker nodes labelled `accelerator=nvidia`;
- the NVIDIA device plugin and `nvidia.com/gpu` resource exposed to Kubernetes;
- namespace CPU and memory quota sufficient for the requests in the Deployment;
- an image built locally with `DOPIPE_PROFILE=gpu` and published to a registry
  the cluster can access. The repository does not currently publish a `:gpu`
  image tag.

The shared Hostinger VPS is CPU-only and its Docpipe namespace quota is below
the requests in this example. Do not apply these files there. Treat this as a
starting point for an operator-managed GPU cluster, not a supported turnkey
production deployment. Review the image, resource limits, model-cache storage,
secrets, and scaling policy against the target cluster before use.

To build an image for a compatible cluster, use the repository Dockerfile with
`DOPIPE_PROFILE=gpu`, tag it in your own registry, update `deployment.yaml`,
and validate the manifests and rollout in a non-production namespace first.
