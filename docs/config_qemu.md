# The `qemu` option in platform configuration

The `qemu` option in the `platforms` section of `input.yml` enables
automatic provisioning of a local QEMU virtual machine
for building on it.

For the general configuration structure see
[config_instruction.md](./config_instruction.md) and the example
[./input.yml](./input.yml). A full QEMU example is available in
`amphimixis/samples/qemu.yml`.

## Quick overview

```yaml
platforms:
  - id: 1
    arch: riscv
    qemu: true
```

```yaml
platforms:
  - id: 2
    arch: x86
    username: root
    password: root
    port: 3333
    qemu:
      machine: pc
      memory: 4
      smp: 4
      kernel: /path/to/kernel
      initrd: /path/to/initrd
      disk_image: /path/to/disk_image
      keep_alive: true
```

## Value forms

The `qemu` field supports two forms:

| Value               | Meaning                                                        |
| :------------------ | :------------------------------------------------------------- |
| `qemu: true`        | Auto-download the default image for the given architecture     |
| `qemu:` (dictionary)   | Fine tuning: VM files, resources, `keep_alive`, `extra_args`   |

`false` or a missing field means the option is disabled.

## `qemu` fields

| Field        | Type           | Default                              | Description                                |
| :----------- | :------------- | :----------------------------------- | :----------------------------------------- |
| `machine`    | string         | `pc` (`x86`), `virt` (`riscv`)       | QEMU machine type (`-machine`)             |
| `cpu`        | string         | `qemu64` (`x86`), `rv64` (`riscv`)   | CPU model (`-cpu`)                         |
| `memory`     | integer        | `4`                                  | VM memory size in gigabytes (`-m`)         |
| `smp`        | integer        | `4`                                  | Number of virtual CPUs (`-smp`)            |
| `kernel`     | string (path)  | —                                    | Path to the kernel image (`-kernel`)       |
| `initrd`     | string (path)  | —                                    | Path to initrd (`-initrd`)                 |
| `disk_image` | string (path)  | —                                    | Path to the disk image (qcow2)             |
| `keep_alive` | boolean        | `false`                              | Do not stop the VM when the run completes  |
| `extra_args` | list of string | `[]`                                 | Extra QEMU arguments, appended at the end of the command |

Example with extra arguments:

```yaml
platforms:
  - id: 1
    arch: x86
    qemu:
      extra_args:
        - "-enable-kvm"
        - "-display none"
```

Each `extra_args` entry is appended to the resulting `qemu-system-*` command.

## Options always added to the command

Regardless of the `qemu` mapping contents, the `qemu-system-*`
command always includes the following options
(see `_build_qemu_command` in `amphimixis/core/qemu_machine.py`):

| Option | Value / source | Purpose |
| :----- | :------------- | :------ |
| `-machine` | `qemu.machine` or the default (`pc` for `x86`, `virt` for `riscv`) | VM board/machine type |
| `-cpu` | `qemu.cpu` or the default (`qemu64` for `x86`, `rv64` for `riscv`) | CPU model |
| `-m` | `<memory>G`, default `4G` | VM memory size |
| `-smp` | `<smp>`, default `4` | Number of virtual CPUs |
| `-device` + `-netdev` | `virtio-net-pci,netdev=net` (`x86`) or `virtio-net-device,netdev=net` (others) + `user,id=net,hostfwd=tcp:127.0.0.1:<port>-:22` | User-mode networking; the guest SSH port 22 is forwarded to the host `port` (default `2222`), accessed via `127.0.0.1` |
| `-object` | `rng-random,filename=/dev/urandom,id=rng` | Entropy source for the guest |
| `-device` (rng) | `virtio-rng-pci,rng=rng` (`x86`) or `virtio-rng-device,rng=rng` (others) | Random number device in the guest |
| `-nographic` | — | Run without a graphical window, console goes to stdout |

Example of the base command part for `x86` (default values,
host port `2222`):

```text
qemu-system-x86_64 -machine pc -cpu qemu64 -m 4G -smp 4 \
  -device virtio-net-pci,netdev=net \
  -netdev user,id=net,hostfwd=tcp:127.0.0.1:2222-:22 \
  -object rng-random,filename=/dev/urandom,id=rng \
  -device virtio-rng-pci,rng=rng \
  -nographic
```

Only the following conditional options are added on top of that base:

- `-device virtio-blk,drive=hd` + `-drive file=<disk_image>,if=none,id=hd,snapshot=on` —
  only if `disk_image` is set (disk changes are discarded
  thanks to `snapshot=on`);
- `-kernel <kernel>` — only if `kernel` is set;
- `-initrd <initrd>` — only if `initrd` is set;
- `-append "root=/dev/vda3 rootfstype=ext4 console=ttyS0 rw"` —
  only for `arch: riscv` with default (auto-downloaded) files;
- `extra_args` contents — appended at the very end of the command.

## VM files: three valid scenarios

File preparation logic (`kernel`, `initrd`, `disk_image`):

1. **Nothing specified** — default auto-download.
   The archive is downloaded via `wget` and extracted via `tar`
   into `$XDG_DATA_HOME/amphimixis/images/<arch>/`
   (if unset, `~/.local/share/amphimixis/images/<arch>/`),
   subsequent runs reuse the cache.
2. **Only `disk_image`** — a custom disk is used,
   kernel and initrd are not required.
3. **All three files (`kernel` + `initrd` + `disk_image`)** —
   used as is, with existence checks.

Any other combination is considered inconsistent and results
in a configuration error.

> **Note:** with custom files (scenarios 2 and 3) Amphimixis
> does **not** install anything inside the VM — package names
> differ between distributions, so automatic installation cannot
> guess them reliably. Make sure the required tools are
> pre-installed in your image: `bash`, `g++`, `rsync`, `perf`
> (plus `perf archive`), `cmake`, and `make` or `ninja`
> (matching `build_system` / `runner`). Package installation
> runs only for auto-downloaded default images.

For `riscv` with default files the following is added to the command:

```text
-append "root=/dev/vda3 rootfstype=ext4 console=ttyS0 rw"
```

## Related platform fields: `address`, `port`, `username`, `password`

- `address`: with `qemu` enabled the VM is always local.
  If the field is set, only `127.0.0.1`
  or `localhost` are allowed. It can be omitted entirely — Amphimixis
  substitutes `127.0.0.1` itself.
- `port`: the host port forwarded to the guest SSH port 22
  (`hostfwd=tcp:127.0.0.1:<port>-:22`). Default is `2222`.
  Different QEMU platforms must use different ports.
- `username` / `password`: for auto-download, `root` / `root` are used
  and enforced — the default images only support these credentials
  (any provided values are ignored with a warning).
  With custom files (`kernel` / `initrd` / `disk_image`)
  both fields are required — a missing `username` or `password`
  is a configuration error (`ValueError`); provide the login
  and password of your image.

## System requirements

The machine running Amphimixis must have installed:

- `qemu-system-riscv64` — for `arch: riscv`;
- `qemu-system-x86_64` — for `arch: x86`;
- `wget` and `tar` — for image auto-download;
- `sshpass` — for password-based SSH access to the VM.
