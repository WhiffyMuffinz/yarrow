"""Build and run the OCR cluster, excluding the VLM server.

These are integration tests that confirm, for a given stack, that the images
build and every non-VLM service starts up and reports healthy on its own
health endpoint:

    paddlex-pipeline, paddleocr-vl-api, hybrid-gateway, gateway

The sglang/vllm ``vlm-server`` is deliberately excluded: it needs a real GPU
and a multi-GB model pull, and is validated separately. The paddlex GenAI
client is lazy (it only dials the VLM at inference time), so the paddlex
services stay healthy with the VLM server absent.

The stack is selected with the ``OCR_CLUSTER_STACK`` environment variable
(``x86`` or ``dgx``; default ``x86``). Set it to ``x86,dgx`` to run both in
one invocation.

Run explicitly (skipped unless ``OCR_CLUSTER_TEST`` is set):

    OCR_CLUSTER_TEST=1 OCR_CLUSTER_STACK=x86 pytest ocr_cluster/tests -v

Environment:
    OCR_CLUSTER_TEST    Set to run the test (otherwise it is skipped).
    OCR_CLUSTER_STACK   Stack to test: ``x86``, ``dgx``, or ``x86,dgx`` (default ``x86``).
    OCR_SKIP_BUILD      Set to reuse already-built images (skips the build step).
    OCR_DEVICE          Force a device for every service, e.g. ``cpu`` on a busy
                        GPU host. When unset, each service uses the device its
                        compose stack declares (falling back to CPU when no GPU
                        is available).
    OCR_BUILD_CACHE     BuildKit local-cache directory (default
                        ``~/.cache/yarrow-ocr-build/<stack>``). CI persists it
                        between runs via actions/cache.
    OCR_HEALTH_TIMEOUT  Per-paddlex-service health wait in seconds (default 1800).
    OCR_HEALTH_TIMEOUT_FAST  Per-other-service health wait in seconds (default 300).

The ``dgx`` (aarch64) stack is a from-source Paddle build for sm_121 (GB10)
and runs on the GitHub-hosted ``ubuntu-24.04-arm`` runner; see
``.github/workflows/ci-ocr-cluster.yml``. That runner has no GPU, so every
service runs on CPU: ``service_device`` falls back per service, and the image
imports fine without CUDA (its build-time warmup layers already run on a
GPU-less build host).
"""

import json
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
OCR_SHARED = REPO_ROOT / "ocr_cluster" / "shared"

# Test image tags. The paddlex image is built once per stack and shared by the
# paddlex-pipeline and paddleocr-vl-api services (both use the same Dockerfile
# via the x-pipeline-image anchor); only their environment differs.
PADDLEX_TAG = "yarrow-ocr-test-paddlex"
HYBRID_TAG = "yarrow-ocr-test-hybrid-gateway"

# Services brought up for the run check, in dependency order (vlm-server
# excluded). gateway is last because nginx resolves its upstream hostname
# once at boot.
RUN_SERVICES = ["paddlex-pipeline", "paddleocr-vl-api", "hybrid-gateway", "gateway"]

# Generous per-service wait: model loading on a CPU-only runner is slow.
HEALTH_TIMEOUT = int(os.environ.get("OCR_HEALTH_TIMEOUT", "1800"))
FAST_HEALTH_TIMEOUT = int(os.environ.get("OCR_HEALTH_TIMEOUT_FAST", "300"))

pytestmark = pytest.mark.ocr_cluster


# --------------------------------------------------------------------------- #
# Environment helpers
# --------------------------------------------------------------------------- #
def _run(cmd, **kwargs):
    """Run a command, raising with captured output on failure."""
    kwargs.setdefault("text", True)
    print(f"$ {' '.join(cmd)}", flush=True)
    return subprocess.run(cmd, check=True, **kwargs)


def _tail(text, n=40):
    lines = (text or "").splitlines()
    return "\n".join(lines[-n:])


def has_gpu() -> bool:
    try:
        return subprocess.run(["nvidia-smi"], capture_output=True, check=False).returncode == 0
    except (FileNotFoundError, OSError):
        return False


def host_arch() -> str:
    machine = platform.machine().lower()
    return "arm64" if machine in ("arm64", "aarch64") else "amd64"


def service_device(service: dict) -> str:
    # Use the device the compose stack declares for this service (defaulting
    # to CPU). If it wants the GPU but this host has none (e.g. the x86
    # ubuntu-latest runner), fall back to CPU: the x86 image ships a libcuda
    # stub so the GPU build still imports and runs on CPU, and the dgx
    # paddleocr-vl-api is a CPU service in the real stack anyway.
    # OCR_DEVICE forces one device for every service (useful to pin CPU on a
    # busy GPU host).
    override = os.environ.get("OCR_DEVICE")
    if override:
        return override
    env = service.get("environment") or {}
    device = env.get("DEVICE", "cpu")
    if device == "gpu" and not has_gpu():
        device = "cpu"
    return device


# --------------------------------------------------------------------------- #
# Resolve the compose stack
# --------------------------------------------------------------------------- #
def resolve_config(stack: str) -> dict:
    env = dict(os.environ, GATEWAY_API_KEY="ci-ocr-test-key")
    res = subprocess.run(
        [
            "docker", "compose",
            "-f", f"ocr_cluster/{stack}/docker-compose.yml",
            "config", "--format", "json",
        ],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True, check=False,
    )
    if res.returncode != 0:
        raise RuntimeError(f"docker compose config failed for {stack}:\n{_tail(res.stderr, 20)}")
    return json.loads(res.stdout)


# --------------------------------------------------------------------------- #
# Build steps
# --------------------------------------------------------------------------- #
def build_cache_dir(stack: str) -> Path:
    base = os.environ.get("OCR_BUILD_CACHE") or os.path.expanduser(
        f"~/.cache/yarrow-ocr-build/{stack}"
    )
    return Path(base)


def _build(tag: str, dockerfile: Path, context: Path, extra_contexts: dict, stack: str):
    """docker build, reading and writing a per-stack BuildKit local cache.

    The cache directory survives between invocations, which is what makes the
    from-source aarch64 Paddle build (hours, unbroken) payable: CI persists it
    between runs via actions/cache (see ci-ocr-cluster.yml), and a second run
    on the same host skips unchanged layers.

    OCR_BUILD_BUILDER selects a named buildx builder (CI uses a
    docker-container builder, which -- together with --load -- is the only way
    local cache export/import and image visibility to docker run both work).
    Unset falls back to the default builder.

    Uses a test-specific tag so the build never overwrites the images the
    developer's own stack is running.
    """
    cache = build_cache_dir(stack)
    cache.mkdir(parents=True, exist_ok=True)
    cmd = [
        "docker", "build", "--load",
        "--cache-from", f"type=local,src={cache}",
        "--cache-to", f"type=local,dest={cache},mode=max",
        "-t", tag,
        "-f", str(dockerfile),
    ]
    builder = os.environ.get("OCR_BUILD_BUILDER")
    if builder:
        cmd += ["--builder", builder]
    for name, path in extra_contexts.items():
        cmd += ["--build-context", f"{name}={path}"]
    cmd += [str(context)]
    try:
        _run(cmd, capture_output=True)
        return
    except subprocess.CalledProcessError as exc:
        out = (exc.stderr or "") + (exc.stdout or "")
        # Surface the real docker error before anything else, so a CI failure
        # shows the build output instead of only this function's traceback.
        print(_tail(out, 40), flush=True)
        if "cache export is not supported" not in out:
            raise RuntimeError(
                f"Build of {tag} failed (exit {exc.returncode}):\n{_tail(out, 60)}"
            ) from exc

    # The active builder cannot export a local cache (plain docker driver on
    # older Docker): rebuild without the cache flags rather than fail.
    print(f"[{stack}] local cache export unsupported by this builder; retrying without cache")
    plain, skip = [], False
    for item in cmd:
        if skip:
            skip = False
        elif item in ("--cache-from", "--cache-to"):
            skip = True
        else:
            plain.append(item)
    _run(plain, capture_output=True)


def build_images(stack: str, config: dict):
    paddle_ctx = REPO_ROOT / "ocr_cluster" / stack
    build_paddlex = paddle_ctx / "paddlex.Dockerfile"
    build_hybrid = OCR_SHARED / "hybrid-gateway.Dockerfile"
    if not build_paddlex.exists():
        raise FileNotFoundError(build_paddlex)
    if not build_hybrid.exists():
        raise FileNotFoundError(build_hybrid)

    # One paddlex image serves both paddlex-pipeline and paddleocr-vl-api.
    _build(f"{PADDLEX_TAG}:{stack}", build_paddlex, paddle_ctx, {"shared": OCR_SHARED}, stack)
    _build(f"{HYBRID_TAG}:{stack}", build_hybrid, OCR_SHARED, {}, stack)

    # The gateway uses a pinned prebuilt nginx image; make sure it is present.
    gateway_image = config["services"]["gateway"]["image"].split("@")[0]
    try:
        _run(["docker", "pull", gateway_image], capture_output=True)
    except subprocess.CalledProcessError:
        # Already present locally; pull is only best-effort.
        pass


# --------------------------------------------------------------------------- #
# Run steps
# --------------------------------------------------------------------------- #
def healthcheck_cmd(service: dict) -> list:
    test = (service.get("healthcheck") or {}).get("test")
    if not test:
        # No compose healthcheck (e.g. dgx paddleocr-vl-api): the paddlex
        # serving app always exposes /health.
        return [
            "python3", "-c",
            "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=5)",
        ]
    method = test[0]
    if method == "CMD":
        return list(test[1:])
    if method == "CMD-SHELL":
        return ["sh", "-c", " ".join(test[1:])]
    raise ValueError(f"Unsupported healthcheck method: {method!r}")


def wait_healthy(container: str, cmd: list, timeout: int):
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        res = subprocess.run(
            ["docker", "exec", container, *cmd], capture_output=True, text=True, timeout=30, check=False
        )
        if res.returncode == 0:
            return
        last = (res.stderr or res.stdout or "")
        time.sleep(5)
    logs = subprocess.run(
        ["docker", "logs", "--tail", "60", container], capture_output=True, text=True, check=False
    ).stdout
    raise TimeoutError(f"{container} not healthy within {timeout}s.\n--last--\n{last}\n--logs--\n{logs}")


def container_name(service: str, suffix: str) -> str:
    # Short, unique, safe for `docker run --name`.
    return f"ocrt-{service[:22].replace('-', '_')}-{suffix}"


def start_service(net: str, name: str, service: dict, config: dict, device: str, suffix: str, stack: str):
    cname = container_name(name, suffix)
    cmd = ["docker", "run", "-d", "--name", cname, "--network", net, "--network-alias", name]

    env = dict(service.get("environment") or {})
    if name in ("paddlex-pipeline", "paddleocr-vl-api"):
        env["DEVICE"] = device
    for key, value in env.items():
        cmd += ["-e", f"{key}={value}"]

    # Attach the GPU only where the service reserves one and a GPU exists.
    reservation = (
        (service.get("deploy") or {}).get("resources", {}).get("reservations", {}).get("devices")
    )
    if reservation and device == "gpu" and has_gpu():
        cmd += ["--gpus", "all"]
    image = service.get("image")
    if name in ("paddlex-pipeline", "paddleocr-vl-api"):
        image = f"{PADDLEX_TAG}:{stack}"
    elif name == "hybrid-gateway":
        image = f"{HYBRID_TAG}:{stack}"
    elif name == "gateway":
        # Mount the shared nginx template (the gateway has no build of its own).
        target = service["configs"][0]["target"]
        file_path = config["configs"]["nginx-config"]["file"]
        cmd += ["-v", f"{file_path}:{target}:ro"]
        image = (service.get("image") or "nginx:latest").split("@")[0]

    cmd += [image]
    _run(cmd, capture_output=True)
    return cname


# --------------------------------------------------------------------------- #
# The test
# --------------------------------------------------------------------------- #
def _select_stacks() -> list:
    raw = os.environ.get("OCR_CLUSTER_STACK", "x86")
    return [s.strip() for s in raw.split(",") if s.strip()]


@pytest.mark.parametrize("stack", _select_stacks())
def test_ocr_cluster_builds_and_runs(stack):
    if not os.environ.get("OCR_CLUSTER_TEST"):
        pytest.skip("Set OCR_CLUSTER_TEST=1 to run the OCR cluster build/run test.")
    if not shutil.which("docker"):
        pytest.skip("docker is not available on this host")

    if stack not in ("x86", "dgx"):
        pytest.fail(f"Unknown OCR_CLUSTER_STACK: {stack!r} (expected x86 or dgx)")
    if stack == "dgx" and host_arch() != "arm64":
        pytest.skip("dgx (aarch64) stack requires an aarch64 host")

    config = resolve_config(stack)
    skip_build = bool(os.environ.get("OCR_SKIP_BUILD"))

    suffix = time.strftime("%H%M%S")
    net = f"ocrt-net-{stack}-{suffix}"
    started: list[str] = []

    try:
        print(f"[{stack}] arch={'arm64' if stack == 'dgx' else 'amd64'} "
              f"host_gpu={has_gpu()} skip_build={skip_build}")
        if skip_build:
            print(f"[{stack}] OCR_SKIP_BUILD set; assuming images are already built")
        else:
            build_images(stack, config)
        _run(["docker", "network", "create", net])

        for service in RUN_SERVICES:
            svc = config["services"][service]
            device = service_device(svc)
            cname = start_service(net, service, svc, config, device, suffix, stack)
            started.append(cname)
            timeout = (
                HEALTH_TIMEOUT if service in ("paddlex-pipeline", "paddleocr-vl-api")
                else FAST_HEALTH_TIMEOUT
            )
            print(f"[{stack}] waiting for {service} (device={device}, {cname}) to become healthy...")
            wait_healthy(cname, healthcheck_cmd(svc), timeout)
            print(f"[{stack}] {service} is healthy")

        # Cross-check the edge gateway end-to-end: /healthz is open, an
        # unauthenticated request is rejected with 401.
        gw = container_name("gateway", suffix)
        res = subprocess.run(
            ["docker", "exec", gw, "wget", "-qO-", "http://127.0.0.1:8080/healthz"],
            capture_output=True, text=True, check=False,
        )
        assert res.returncode == 0, f"gateway /healthz failed: {res.stderr}"
        assert "ok" in res.stdout, f"gateway /healthz unexpected body: {res.stdout!r}"

        res = subprocess.run(
            ["docker", "exec", gw, "wget", "-qO-", "http://127.0.0.1:8080/"],
            capture_output=True, text=True, check=False,
        )
        assert res.returncode != 0, "gateway accepted an unauthenticated request"
        assert "401" in (res.stderr + res.stdout), f"gateway returned {res.returncode} (expected 401)"

        print(f"[{stack}] all non-VLM services built, ran, and are healthy")
    finally:
        for cname in started:
            subprocess.run(["docker", "rm", "-f", cname], capture_output=True, check=False)
        subprocess.run(["docker", "network", "rm", net], capture_output=True, check=False)
