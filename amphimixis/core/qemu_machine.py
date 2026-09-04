"""QEMU virtual machine provisioning for remote architectures."""

import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

from amphimixis.core.general import IUI, MachineInfo, NullUI
from amphimixis.core.logger import setup_logger

_logger = setup_logger("qemu_provisioner")

IMAGES_REPO_URL = (
    "https://media.githubusercontent.com/media/mariemrmr/amphimixis_images/main"
)
RISCV_ARCHIVE = "alpine-riscv-vm.tar.gz"
X86_ARCHIVE = "alpine-x86-64-vm.tar.gz"


class QemuMachineProvisioner:
    """Manages QEMU virtual machine lifecycle for performance profiling.

    This class handles starting, stopping, and communicating with QEMU VMs
    that provide access to foreign architectures.
    """

    def __init__(
        self,
        machine: MachineInfo,
        ui: IUI = NullUI(),
    ):
        if machine.qemu is None:
            raise ValueError("Machine must have QemuConfig to be provisioned")
        if machine.auth is None:
            raise ValueError(
                "Machine must have auth (MachineAuthenticationInfo) for QEMU SSH access"
            )
        self._machine = machine
        self._config = machine.qemu
        self._ui = ui
        self._process: Optional[subprocess.Popen] = None
        self._alpine_image: bool = False
        self._uses_default_files: bool = False

    @property
    def keep_alive(self) -> bool:
        """Check if VM should be kept alive after cleanup."""
        return self._config.keep_alive

    def start(self, timeout: int = 500) -> None:
        """Start the QEMU virtual machine and wait for SSH to be ready.

        :param int timeout: Maximum time to wait for VM to become ready.
        """
        if self._process is not None:
            _logger.warning(
                "VM already running on port %d",
                self._machine.auth.port if self._machine.auth else 2222,
            )
            return

        self._prepare_files()

        self._ui.update_message(
            "QEMU",
            f"Starting VM on port {self._machine.auth.port if self._machine.auth else 2222}...",
        )

        qemu_cmd = self._build_qemu_command()
        _logger.info("Starting QEMU: %s", " ".join(qemu_cmd))

        # pylint: disable = R1732
        self._process = subprocess.Popen(
            qemu_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )

        self._wait_for_ssh(timeout)
        self._ui.update_message("QEMU", "VM started successfully")

    def stop(self) -> None:
        """Stop the QEMU virtual machine."""
        if self._process is None:
            return

        self._ui.update_message("QEMU", "Stopping VM...")
        self._process.terminate()
        try:
            self._process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait()
        self._process = None
        self._ui.update_message("QEMU", "VM stopped")

    def get_ssh_command(self, command: str) -> list[str]:
        """Build an SSH command to execute inside the VM.

        :param str command: Command to execute inside the VM.
        :return: List of command arguments for subprocess.
        """
        assert self._machine.auth is not None
        auth = self._machine.auth
        return [
            "sshpass",
            "-p",
            auth.password or "",
            "ssh",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "StrictHostKeyChecking=no",
            "-p",
            str(auth.port),
            f"{auth.username}@127.0.0.1",
            command,
        ]

    def run_cmd_via_ssh(
        self, command: str, timeout: int = 300
    ) -> subprocess.CompletedProcess:
        """Execute a command inside the VM via SSH.

        :param str command: Command to execute inside the VM.
        :param int timeout: Command timeout in seconds.
        :return: CompletedProcess with return code, stdout, stderr.
        """
        return subprocess.run(
            self.get_ssh_command(command),
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def install_packages(self, packages: list[str]) -> None:
        """Install packages inside the VM.

        :param list[str] packages: List of package names to install.
        """
        self._ui.update_message("QEMU", "Installing packages...")

        if self._alpine_image:
            update_cmd = "apk update"
            install_cmd = f"apk add {' '.join(packages)}"
        else:
            update_cmd = "apt-get update"
            install_cmd = f"apt-get install -y {' '.join(packages)}"

        result = self.run_cmd_via_ssh(update_cmd)
        if result.returncode != 0:
            _logger.error("Failed to update package lists: %s", result.stderr)
            raise RuntimeError("Failed to update package lists")

        result = self.run_cmd_via_ssh(install_cmd)
        if result.returncode != 0:
            _logger.error("Failed to install packages: %s", result.stderr)
            raise RuntimeError(f"Failed to install packages: {' '.join(packages)}")

        self._ui.update_message("QEMU", "Packages installed")

    def get_provisioned_machine(self) -> MachineInfo:
        """Get machine info with address updated to localhost for the provisioned VM.

        :return: MachineInfo with address pointing to the running VM.
        """
        return MachineInfo(
            arch=self._machine.arch,
            address=self._machine.address,
            auth=self._machine.auth,
            qemu=self._machine.qemu,
        )

    def _build_qemu_command(self) -> list[str]:
        """Build the QEMU command line arguments.

        :return: List of command arguments.
        """
        if self._machine.arch.lower() == "x86":
            return self._build_alpine_qemu_command()

        cpu = self._config.cpu if self._config.cpu else self._get_default_cpu()

        cmd = [
            "qemu-system-" + self._get_qemu_arch(),
            "-machine",
            self._config.machine,
            "-cpu",
            cpu,
            "-m",
            f"{self._config.memory}G",
            "-smp",
            str(self._config.smp),
        ]

        if self._config.disk_image:
            if not self._config.disk_image.exists():
                raise FileNotFoundError(
                    f"Disk image not found: {self._config.disk_image}"
                )
            cmd.extend(
                [
                    "-device",
                    "virtio-blk-device,drive=hd",
                    "-drive",
                    f"file={self._config.disk_image},if=none,id=hd,snapshot=on",
                ]
            )

        if self._config.kernel:
            if not self._config.kernel.exists():
                raise FileNotFoundError(f"Kernel not found: {self._config.kernel}")
            cmd.extend(["-kernel", str(self._config.kernel)])

            if self._config.initrd:
                if not self._config.initrd.exists():
                    raise FileNotFoundError(f"Initrd not found: {self._config.initrd}")
                cmd.extend(["-initrd", str(self._config.initrd)])

        port = self._machine.auth.port if self._machine.auth else 2222

        cmd.extend(
            [
                "-device",
                "virtio-net-device,netdev=net",
                "-netdev",
                f"user,id=net,hostfwd=tcp:127.0.0.1:{port}-:22",
            ]
        )

        cmd.extend(
            [
                "-object",
                "rng-random,filename=/dev/urandom,id=rng",
                "-device",
                "virtio-rng-device,rng=rng",
                "-nographic",
                "-append",
                self._get_kernel_append(),
            ]
        )

        return cmd

    def _build_alpine_qemu_command(self) -> list[str]:
        """Build QEMU command for Alpine x86_64 VM.

        :return: List of command arguments.
        """
        cmd = [
            "qemu-system-x86_64",
            "-machine",
            "pc",
            "-cpu",
            "qemu64",
            "-m",
            f"{self._config.memory}G",
            "-smp",
            str(self._config.smp),
        ]

        if self._kvm_available():
            cmd.append("-enable-kvm")

        if self._config.disk_image:
            if not self._config.disk_image.exists():
                raise FileNotFoundError(
                    f"Disk image not found: {self._config.disk_image}"
                )
            cmd.extend(
                [
                    "-drive",
                    f"file={self._config.disk_image},format=qcow2,if=virtio",
                ]
            )

        port = self._machine.auth.port if self._machine.auth else 2222

        cmd.extend(
            [
                "-netdev",
                f"user,id=net0,hostfwd=tcp:127.0.0.1:{port}-:22",
                "-device",
                "virtio-net-pci,netdev=net0",
                "-object",
                "rng-random,filename=/dev/urandom,id=rng",
                "-device",
                "virtio-rng-pci,rng=rng",
                "-nographic",
            ]
        )

        return cmd

    def _kvm_available(self) -> bool:
        """Check whether KVM acceleration is available on this host.

        :return: True if the KVM device is present.
        :rtype: bool
        """
        return Path("/dev/kvm").exists()

    def _get_kernel_append(self) -> str:
        """Get the kernel command line append string for the current architecture.

        :return: Kernel append string.
        :rtype: str
        """
        return {
            "riscv": "root=/dev/vda3 rootfstype=ext4 console=ttyS0 rw",
        }.get(self._machine.arch.lower(), "root=LABEL=rootfs console=ttyS0")

    def _prepare_files(self) -> None:
        """Prepare kernel, initrd, and disk image files based on configuration.

        Handles 3 scenarios:
        1. All 3 files specified - validate they exist and use as-is
        2. Only disk_image specified
        3. No files specified - download all defaults for arch

        Raises ValueError if configuration is inconsistent (e.g., only kernel+initrd).
        """
        has_kernel = self._config.kernel is not None
        has_initrd = self._config.initrd is not None
        has_disk = self._config.disk_image is not None
        self._uses_default_files = not (has_kernel or has_initrd or has_disk)

        # Scenario 1: All 3 files specified
        if has_kernel and has_initrd and has_disk:
            self._validate_files_exist()
            return

        # Scenario 2: Only disk_image specified
        if has_disk and not has_kernel and not has_initrd:
            return

        # Scenario 3: No files specified
        if self._uses_default_files:
            _logger.info(
                "No files specified, downloading defaults for %s", self._machine.arch
            )
            self._download_default_files()
            return

        # Inconsistent configuration
        kernel_str = str(self._config.kernel) if self._config.kernel else "None"
        initrd_str = str(self._config.initrd) if self._config.initrd else "None"
        disk_str = str(self._config.disk_image) if self._config.disk_image else "None"
        raise ValueError(
            f"Inconsistent file configuration: kernel={kernel_str}, "
            f"initrd={initrd_str}, disk_image={disk_str}. "
            "Specify all 3 files, only disk_image, or none (for auto-download)."
        )

    def _validate_files_exist(self) -> None:
        """Validate that specified kernel, initrd, and disk_image files exist."""
        if self._config.kernel and not self._config.kernel.exists():
            raise FileNotFoundError(f"Kernel not found: {self._config.kernel}")
        if self._config.initrd and not self._config.initrd.exists():
            raise FileNotFoundError(f"Initrd not found: {self._config.initrd}")
        if self._config.disk_image and not self._config.disk_image.exists():
            raise FileNotFoundError(f"Disk image not found: {self._config.disk_image}")

    def _download_default_files(self) -> None:
        """Download default kernel, initrd, and disk image for the current architecture.

        Raises NotImplementedError for unsupported architectures.
        """

        arch = self._machine.arch.lower()
        if arch == "x86":
            workdir = Path("/tmp/image_x86")
        else:
            workdir = Path(tempfile.gettempdir()) / f"amixis_{arch}_vm"
        workdir.mkdir(parents=True, exist_ok=True)

        if arch == "riscv":
            self._download_riscv_defaults(workdir)
        elif arch == "x86":
            self._download_x86_defaults(workdir)
        else:
            raise NotImplementedError(
                f"Default file preparation not implemented for architecture: {arch}. "
                "Please specify kernel, initrd, and disk_image manually."
            )

    def _download_riscv_defaults(self, workdir: Path) -> None:
        """Download and prepare RISC-V VM files (kernel, initrd, disk image).

        :param Path workdir: Working directory for downloaded files.
        """
        qcow2_file = self._download_and_extract(
            workdir, RISCV_ARCHIVE, "alpine-riscv.qcow2"
        )
        kernel = self._find_extracted(workdir, "vmlinux-riscv64")
        initrd = self._find_extracted(workdir, "initramfs-riscv64")

        if kernel is None or initrd is None:
            raise FileNotFoundError(
                "Kernel or initrd not found after extraction of RISC-V VM files"
            )

        self._alpine_image = True

        # Set paths in config (only if not already set by user)
        if self._config.disk_image is None:
            self._config.disk_image = qcow2_file
        if self._config.kernel is None:
            self._config.kernel = kernel
        if self._config.initrd is None:
            self._config.initrd = initrd

    def _download_x86_defaults(self, workdir: Path) -> None:
        """Download and prepare x86_64 VM files.

        :param Path workdir: Working directory for downloaded files.
        """
        qcow2_file = self._download_and_extract(
            workdir, X86_ARCHIVE, "alpine-x86.qcow2"
        )
        self._alpine_image = True

        if self._config.disk_image is None:
            self._config.disk_image = qcow2_file

    def _download_and_extract(
        self, workdir: Path, archive_name: str, disk_name: str
    ) -> Path:
        """Download and extract a VM archive, returning the disk image path.

        Skips downloading and extraction if the disk image is already present.

        :param Path workdir: Working directory for the archive and extracted files.
        :param str archive_name: Archive file name inside the images repo.
        :param str disk_name: Name of the disk image file inside the archive.
        :return: Path to the extracted disk image.
        :rtype: Path
        """
        disk_file = self._find_extracted(workdir, disk_name)
        if disk_file is not None:
            _logger.info("Using cached VM files from %s", disk_file.parent)
            return disk_file

        archive_path = workdir / archive_name
        if not archive_path.exists():
            _logger.info("Downloading %s...", archive_name)
            result = subprocess.run(
                [
                    "wget",
                    "-q",
                    "--show-progress",
                    "-O",
                    str(archive_path),
                    f"{IMAGES_REPO_URL}/{archive_name}",
                ],
                check=False,
                stdout=subprocess.DEVNULL,
            )
            if result.returncode != 0:
                _logger.error("Failed to download %s", archive_name)
                raise RuntimeError(f"Failed to download {archive_name}")
        _logger.info("Extracting %s...", archive_name)
        extract_result = subprocess.run(
            ["tar", "-xzf", str(archive_path), "-C", str(workdir)],
            capture_output=True,
            text=True,
            check=False,
        )
        if extract_result.returncode != 0:
            _logger.error(
                "Failed to extract %s: %s",
                archive_name,
                extract_result.stderr.strip(),
            )
            raise RuntimeError(f"Failed to extract {archive_name}")

        disk_file = self._find_extracted(workdir, disk_name)
        if disk_file is None:
            raise FileNotFoundError(
                f"Disk image not found after extraction: {disk_name}"
            )
        return disk_file

    def _find_extracted(self, workdir: Path, name: str) -> Optional[Path]:
        """Find an extracted file by name inside the working directory.

        :param Path workdir: Working directory to search.
        :param str name: File name to search for.
        :return: Path to the matching file or None if not found.
        """
        matches = list(workdir.rglob(name))
        if not matches:
            return None
        return matches[0]

    def _get_qemu_arch(self) -> str:
        """Map architecture to QEMU binary name.

        :return: QEMU binary suffix (e.g., "riscv64").
        """
        arch_map = {
            "riscv": "riscv64",
            "x86": "x86_64",
        }
        return arch_map.get(self._machine.arch.lower(), self._machine.arch.lower())

    def _get_default_cpu(self) -> str:
        """Get default CPU model for the architecture.

        :return: CPU model string.
        """
        cpu_map = {
            "riscv": "rv64",
            "x86": "x86_64",
        }
        return cpu_map.get(self._machine.arch.lower(), "qemu64")

    def _wait_for_ssh(self, timeout: int) -> None:
        """Wait for SSH to become available on the VM.

        :param int timeout: Maximum time to wait in seconds.
        """
        assert self._machine.auth is not None
        auth = self._machine.auth
        max_retries = timeout // 5
        for attempt in range(max_retries):
            result = subprocess.run(
                [
                    "sshpass",
                    "-p",
                    auth.password or "",
                    "ssh",
                    "-o",
                    "UserKnownHostsFile=/dev/null",
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "ConnectTimeout=5",
                    "-p",
                    str(auth.port),
                    f"{auth.username}@127.0.0.1",
                    "echo SSH ready",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0 and "SSH ready" in result.stdout:
                _logger.info("SSH available after %d attempts", attempt + 1)
                return

            if attempt < max_retries - 1:
                time.sleep(5)

        raise RuntimeError(f"SSH not available after {timeout}s on port {auth.port}")
