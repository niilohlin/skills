---
name: manage-fleet
description: Run a task on every machine in the user's fleet (this Mac, niils-omarchy, dellburk/dellbox) over plain OpenSSH. Use when the user says "manage fleet", "/manage-fleet", "on all my machines", "on every computer", "across the fleet", or asks to install/update/check/configure something everywhere.
---

# Manage Fleet

Do the requested task on **all three** machines unless the user names a subset.

| Machine | How to reach it | OS |
|---|---|---|
| this Mac (`niils-m5-pro`) | run locally | macOS (arm64, Homebrew) |
| `omarchy` (niils-omarchy) | `ssh omarchy` | Omarchy (Arch Linux, pacman/yay) |
| `dellbox` (dellburk) | `ssh dellbox` | Omarchy (Arch Linux, pacman/yay) |

User on both Linux boxes is `niilohlin`; passwordless `sudo -n` works.

## Rules

1. Use normal `ssh` (aliases in `~/.ssh/config`). Never `tailscale ssh`. Hostnames resolve via Tailscale MagicDNS, so Tailscale must be connected on the Mac.
2. Always pass `-o BatchMode=yes -o ConnectTimeout=5` so nothing hangs on a prompt.
3. Translate the task per OS: Homebrew on the Mac, `pacman`/`yay` on the Linux boxes. Same intent, native command.
4. Run the two Linux boxes in parallel (`for h in omarchy dellbox; do ...; done` or parallel tool calls), and the Mac locally.
5. For non-interactive package installs use `sudo -n pacman -S --needed --noconfirm <pkg>` / `yay -S --needed --noconfirm <pkg>`.
6. Before anything destructive (deleting data, reboots, changing sshd/firewall/tailscale settings), confirm with the user. Never run `tailscale set --ssh=true` or disable `sshd`/the `tailscale0` port-22 ufw rule: that cuts off access.
7. If a box is unreachable, say so and continue with the others; don't silently skip it.

## Template

```sh
for h in omarchy dellbox; do
  echo "== $h"
  ssh -o BatchMode=yes -o ConnectTimeout=5 "$h" '<linux command>' 2>&1
done
echo "== mac"; <mac command>
```

## Report

Give a per-machine result (ok / failed + why / unreachable), e.g. a short table.
