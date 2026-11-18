---
name: manage-fleet
description: Use when the user says "promulgate this", "/manage-fleet", "on all my machines", "on every computer", "across the fleet"
---

# Manage Fleet

Do the requested task on **all three** machines unless the user names a subset.

| Alias | Hostname | User | OS |
|---|---|---|---|
| `mac` | niils-m5-pro | `n.ohlin` | macOS (arm64, Homebrew) |
| `omarchy` | niils-omarchy | `niilohlin` | Omarchy (Arch Linux, pacman/yay) |
| `dellbox` | dellburk | `niilohlin` | Omarchy (Arch Linux, pacman/yay) |

This skill may run on **any** of the three. First find out which one you're on (`hostname`): run that one's part locally and `ssh <alias>` to the other two. Every machine has all three aliases in `~/.ssh/config` and the same `id_rsa` key, so any machine can reach any other.

Passwordless `sudo -n` works on the Linux boxes.

## Rules

1. Use normal `ssh` via the aliases `mac` / `omarchy` / `dellbox` in `~/.ssh/config` (Linux: OpenSSH on port 2222, port 22 on the tailnet IP is Tailscale SSH; Mac: Remote Login on port 22). Hostnames resolve via Tailscale MagicDNS, so Tailscale must be connected on the machine you're on. Only if plain ssh fails, fall back to `tailscale ssh niilohlin@niils-omarchy` / `niilohlin@dellburk` and tell the user. If a box's `~/.ssh/config` lacks an alias, add the block from the table above.
2. Always pass `-o BatchMode=yes -o ConnectTimeout=5` so nothing hangs on a prompt.
3. Translate the task per OS: Homebrew on the Mac, `pacman`/`yay` on the Linux boxes. Same intent, native command.
4. Run the remote machines in parallel and the local one directly.
5. For non-interactive package installs use `sudo -n pacman -S --needed --noconfirm <pkg>` / `yay -S --needed --noconfirm <pkg>`.
6. Before anything destructive (deleting data, reboots, changing sshd/firewall/tailscale settings), confirm with the user. Never disable `sshd`, Tailscale SSH (`tailscale set --ssh=false`), or the `tailscale0` ufw rules for ports 22/2222: they are the access paths (OpenSSH primary, Tailscale SSH backup).
7. If a box is unreachable, say so and continue with the others; don't silently skip it.

## Template

```sh
case "$(hostname -s)" in niils-m5-pro|Mac) me=mac;; niils-omarchy) me=omarchy;; dellburk) me=dellbox;; esac
for h in mac omarchy dellbox; do
  [ "$h" = mac ] && cmd='<mac command>' || cmd='<linux command>'
  echo "== $h"
  if [ "$h" = "$me" ]; then sh -c "$cmd"; else ssh -o BatchMode=yes -o ConnectTimeout=5 "$h" "$cmd"; fi 2>&1
done
```

## Report

Give a per-machine result (ok / failed + why / unreachable), e.g. a short table.
