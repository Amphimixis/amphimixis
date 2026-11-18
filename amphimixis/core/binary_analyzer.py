"""Analyze binary for platform-specific vector instructions."""

import argparse
import os
import shutil
import subprocess
import sys
from os import path

from amphimixis.core.general.general import Arch
from amphimixis.core.logger import setup_logger

_logger = setup_logger("BINARY_ANALYZER")

VECTOR_INSTRUCTIONS_BY_ARCH: dict[str, list[str]] = {
    "x86": [
        "addps",
        "addpd",
        "subps",
        "subpd",
        "mulps",
        "mulpd",
        "divps",
        "divpd",
        "sqrtps",
        "sqrtpd",
        "movaps",
        "movapd",
        "movups",
        "movupd",
        "andps",
        "andpd",
        "orps",
        "orpd",
        "xorps",
        "xorpd",
        "shufps",
        "shufpd",
        "unpcklps",
        "unpckhps",
        "paddb",
        "paddw",
        "paddd",
        "paddq",
        "psubb",
        "psubw",
        "psubd",
        "psubq",
        "pmullw",
        "pmulld",
        "pmulhw",
        "maxpd",
        "minps",
        "cmpp",
        "pcmpeqb",
        "cvttps2dq",
        "cvtdq2ps",
        "psllw",
        "psrlw",
        "psraw",
        "vfmadd213ps",
    ],
    "avx": [
        "vaddps",
        "vaddpd",
        "vsubps",
        "vsubpd",
        "vmulps",
        "vmulpd",
        "vdivps",
        "vdivpd",
        "vsqrtps",
        "vsqrtpd",
        "vmovaps",
        "vmovapd",
        "vmovups",
        "vmovupd",
        "vandps",
        "vandpd",
        "vorps",
        "vorpd",
        "vxorps",
        "vxorpd",
        "vshufps",
        "vshufpd",
        "vpaddb",
        "vpaddw",
        "vpaddd",
        "vpaddq",
        "vpsubb",
        "vpsubw",
        "vpsubd",
        "vpsubq",
        "vppmul",
        "vfmadd",
        "vfnmadd",
        "vcvtdq2ps",
        "vcvtps2pd",
        "vcmpps",
        "vcmppd",
        "vhaddps",
        "vhsubps",
        "vpermd",
        "vpermpd",
        "vinsertf128",
        "vextractf128",
        "vpsll",
        "vpsraw",
        "vpsrad",
    ],
    "avx512": [
        "vaddps",
        "vaddpd",
        "vmulps",
        "vmulpd",
        "vmovaps",
        "vmovapd",
        "vpaddd",
        "vpaddq",
        "vpsubd",
        "vpsubq",
        "vpmulld",
        "vpmullq",
        "vfmadd132",
        "vfmadd213",
        "vfmadd231",
        "vcompress",
        "vexpand",
        "vperm",
        "vpconflict",
        "vplzcnt",
        "vpternlogd",
        "vpternlogq",
        "vpcmp",
        "vpdpbusd",
        "vpshld",
        "vpshrd",
        "vpopcntd",
        "vpopcntq",
        "vpinsrd",
        "vpinsrq",
        "vbroadcastss",
        "vbroadcastsd",
    ],
    "neon": [
        "vadd",
        "vsub",
        "vmul",
        "vdiv",
        "vld1",
        "vst1",
        "vld2",
        "vst2",
        "vmla",
        "vmls",
        "vfma",
        "vfms",
        "vabs",
        "vneg",
        "vsqrt",
        "vmax",
        "vmin",
        "vpadd",
        "vzip",
        "vuzp",
        "vtrn",
        "vrev",
        "vext",
        "vtbl",
        "vand",
        "vbic",
        "veor",
        "vorn",
        "vshl",
        "vshr",
        "vsri",
        "vsli",
        "vqshl",
        "vqadd",
        "vtbx",
        "vdup",
        "vclz",
        "vcnt",
        "vceq",
        "vcgt",
        "vcge",
    ],
    "rvv": [
        "vsetvli",
        "vsetvl",
        "vle8",
        "vle16",
        "vle32",
        "vle64",
        "vse8",
        "vse16",
        "vse32",
        "vse64",
        "vadd",
        "vsub",
        "vmul",
        "vdiv",
        "vfmul",
        "vfadd",
        "vfsub",
        "vfdiv",
        "vslideup",
        "vslidedown",
        "vrgather",
        "vcompress",
        "vpopc",
        "vfirst",
        "vmv",
    ],
}

ARCH_TO_VECTOR_MAP: dict[Arch, list[str]] = {
    Arch.X86: ["x86", "avx", "avx512"],
    Arch.ARM: ["neon"],
    Arch.RISCV: ["rvv"],
}

OBJDUMP_BY_ARCH: dict[Arch, str] = {
    Arch.X86: "objdump",
    Arch.ARM: "arm-linux-gnueabihf-objdump",
    Arch.RISCV: "riscv64-linux-gnu-objdump",
}


def _find_objdump(arch: Arch) -> str:
    candidates: list[str] = []

    primary = OBJDUMP_BY_ARCH.get(arch)
    if primary:
        candidates.append(primary)

    if arch == Arch.RISCV:
        candidates.extend(
            [
                "riscv64-unknown-elf-objdump",
                "riscv64-elf-objdump",
                "riscv32-linux-gnu-objdump",
                "riscv32-unknown-elf-objdump",
            ]
        )
    elif arch == Arch.ARM:
        candidates.extend(
            [
                "aarch64-linux-gnu-objdump",
                "arm-none-eabi-objdump",
                "aarch64-none-elf-objdump",
            ]
        )
    elif arch == Arch.X86:
        candidates.extend(["x86_64-linux-gnu-objdump", "i686-linux-gnu-objdump"])

    for name in candidates:
        found = shutil.which(name)
        if found and os.access(found, os.X_OK):
            return found

    search_roots = ["/usr/bin", "/usr/local/bin", "/usr", "/opt"]
    for root in search_roots:
        if not path.exists(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            if dirpath.count(os.sep) - root.count(os.sep) > 4:
                dirnames.clear()
                continue

            for fname in filenames:
                fl = fname.lower()
                if "objdump" not in fl:
                    continue
                if arch == Arch.RISCV and "riscv" not in fl:
                    continue
                if arch == Arch.ARM and not ("arm" in fl or "aarch" in fl):
                    continue
                if arch == Arch.X86 and ("riscv" in fl or "arm" in fl or "aarch" in fl):
                    continue

                full = path.join(dirpath, fname)
                if os.access(full, os.X_OK):
                    return full

    raise FileNotFoundError(
        f"objdump for {arch} not found. Tried PATH and common toolchain directories."
    )


def analyze_vectorization(
    binary_path: str, arch: Arch, objdump_path: str | None = None
) -> tuple[int, int, list[tuple[str, int]]]:
    """Analyze a binary for platform-specific vector instructions.

    :param str binary_path: Path to the built executable or object file
    :param Arch arch: Target architecture
    :param str | None objdump_path: Explicit path to objdump binary
    :return: (unique_count, total_count, sorted_list) where sorted_list is
        [(instruction, count), ...] sorted descending by count
    :rtype: tuple[int, int, list[tuple[str, int]]]
    :raises FileNotFoundError: If binary_path does not exist
    :raises RuntimeError: If objdump fails or is not found
    :raises ValueError: If arch is unknown
    """
    if not path.exists(binary_path):
        raise FileNotFoundError(f"Binary not found: {binary_path}")

    if objdump_path:
        objdump = objdump_path
    else:
        objdump = OBJDUMP_BY_ARCH.get(arch)
        if objdump is None:
            raise ValueError(f"Unknown architecture: {arch}")

    try:
        proc = subprocess.run(
            [objdump, "-d", binary_path],
            capture_output=True,
            text=True,
            check=True,
        )
        objdump_output = proc.stdout
    except FileNotFoundError as e:
        if not objdump_path:
            try:
                objdump = _find_objdump(arch)
                proc = subprocess.run(
                    [objdump, "-d", binary_path],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                objdump_output = proc.stdout
            except FileNotFoundError as fallback_e:
                raise RuntimeError(
                    "Fallback objdump not found. Please install matching binutils or pass an explicit path."
                ) from fallback_e
        else:
            raise RuntimeError(
                f"{objdump} not found. Please install matching binutils or pass an explicit path."
            ) from e

    except subprocess.CalledProcessError as e:
        err_msg = e.stderr.strip() if e.stderr else str(e)
        err_msg_lower = err_msg.lower()

        if not objdump_path and (
            "can't disassemble" in err_msg_lower
            or "unknown architecture" in err_msg_lower
            or "bfd" in err_msg_lower
        ):
            try:
                objdump = _find_objdump(arch)
                proc = subprocess.run(
                    [objdump, "-d", binary_path],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                objdump_output = proc.stdout
            except FileNotFoundError as fallback_e:
                raise RuntimeError(
                    "Fallback objdump not found after architecture mismatch. Please install matching binutils."
                ) from fallback_e
            except subprocess.CalledProcessError as fallback_e:
                fallback_err = (
                    fallback_e.stderr.strip() if fallback_e.stderr else str(fallback_e)
                )
                raise RuntimeError(
                    f"Error running fallback {objdump}: {fallback_err}"
                ) from fallback_e
        else:
            raise RuntimeError(f"Error running {objdump}: {err_msg}") from e

    lines = objdump_output.split("\n")
    instruction_sets = ARCH_TO_VECTOR_MAP.get(arch)

    if not instruction_sets:
        raise ValueError(f"Unknown architecture: {arch}")

    all_instructions: list[str] = []
    for iset in instruction_sets:
        all_instructions.extend(VECTOR_INSTRUCTIONS_BY_ARCH.get(iset, []))

    found: list[tuple[str, int]] = []
    for inst in all_instructions:
        count = sum(1 for line in lines if inst in line)
        if count > 0:
            found.append((inst, count))

    found.sort(key=lambda x: x[1], reverse=True)
    total_count = sum(f[1] for f in found)
    return len(found), total_count, found


def _format_result(
    binary_path: str,
    arch: Arch,
    unique: int,
    total: int,
    found: list[tuple[str, int]],
) -> str:
    lines: list[str] = [
        "=== Vector instruction analysis ===",
        f"  Binary: {binary_path}",
        "",
        f"{binary_path} --- {arch.value.upper()} --- {unique} unique / {total} total",
    ]
    if found:
        for inst, count in found:
            lines.append(f"  {inst}: {count}")
    else:
        lines.append("  No vector instructions detected.")
    lines.append("")
    return "\n".join(lines)


def _main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze a binary for platform-specific vector instructions."
    )
    parser.add_argument(
        "--binary",
        required=True,
        help="Path to the built executable or object file",
    )
    parser.add_argument(
        "--arch",
        choices=["x86", "riscv", "arm"],
        default="x86",
        help="Target architecture (default: x86)",
    )
    args = parser.parse_args()

    arch = getattr(Arch, str(args.arch).lower(), None)
    if not arch:
        print(f"ERROR: unknown architecture {args.arch}.")
        return 1
    unique, total, found = analyze_vectorization(args.binary, arch)
    print(_format_result(args.binary, arch, unique, total, found))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
