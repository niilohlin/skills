#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shellwords import commands, head  # noqa: E402

MSG = """Blocked: `{seg}` relies on the current kube context. Always name the cluster explicitly:
- kubectl --context <ctx> ...
- helm --kube-context <ctx> ...
List contexts with `kubectl config get-contexts`. Never switch the default (`kubectl config use-context`)."""

KUBECTL_LOCAL = {"kustomize", "completion", "help", "plugin"}
KUBECTL_CONFIG_OK = {"get-contexts", "current-context", "view", "get-clusters", "get-users"}
HELM_LOCAL = {
    "template", "repo", "version", "lint", "dependency", "dep", "show", "inspect",
    "search", "pull", "fetch", "package", "plugin", "env", "completion", "help",
    "create", "verify", "registry",
}


def subcommand(args):
    skip = False
    for a in args:
        if skip:
            skip = False
            continue
        if a.startswith("-"):
            skip = "=" not in a and a in {"-n", "--namespace", "--kubeconfig", "-o", "--output"}
            continue
        return a
    return None


def has_flag(args, flag):
    return any(a == flag or a.startswith(flag + "=") for a in args)


def offending(command):
    for w in commands(command):
        i = head(w)
        seg = " ".join(w[i:])
        for tok in w[i:i + 1]:
            name = tok.rsplit("/", 1)[-1]
            if name not in ("kubectl", "helm"):
                continue
            args = w[i + 1:]
            sub = subcommand(args)
            if name == "kubectl":
                if sub in KUBECTL_LOCAL or (sub == "version" and "--client" in args):
                    break
                if sub == "config":
                    rest = args[args.index("config") + 1:]
                    if rest and rest[0] in KUBECTL_CONFIG_OK:
                        break
                    return seg
                if not has_flag(args, "--context"):
                    return seg
            else:
                if sub in HELM_LOCAL or sub is None:
                    break
                if not has_flag(args, "--kube-context"):
                    return seg
            break
    return None


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    if data.get("tool_name") != "Bash":
        return 0
    hit = offending((data.get("tool_input") or {}).get("command") or "")
    if hit:
        print(MSG.format(seg=hit), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--test"]:
        bad = [
            "kubectl get pods -n online",
            "kubectl -n online logs deploy/api | head",
            "cd x && kubectl rollout status deploy/visa",
            "echo $(kubectl get ns)",
            "helm upgrade visa ./chart",
            "kubectl config use-context gke_volumental-staging",
            "/usr/bin/kubectl get pods",
            "timeout 30s kubectl get pods",
            "KUBECONFIG=x kubectl get pods",
        ]
        good = [
            "kubectl --context gke_staging get pods -n online",
            "kubectl get pods --context=gke_staging",
            "kubectl config get-contexts",
            "kubectl kustomize apps/flex",
            "kubectl version --client",
            "helm template visa ./chart",
            'git commit -m "fix; kubectl get pods" && git push',
            "helm --kube-context gke_staging list -A",
            "echo kubectl is great",
            "grep kubectl README.md",
        ]
        for c in bad:
            assert offending(c), c
        for c in good:
            assert not offending(c), c
        print("ok")
        sys.exit(0)
    sys.exit(main())
