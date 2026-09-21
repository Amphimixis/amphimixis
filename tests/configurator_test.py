"""Configurator tests"""

import os
import tempfile
from shutil import rmtree
from unittest.mock import MagicMock, patch

import pytest

import amphimixis.core.configurator as configurator
from amphimixis.core.general import Arch, Project


@pytest.mark.unit
class TestConfiguratorWithTestData:
    """Tests for configurator using input_configurator_test.yaml"""

    TEST_CONFIG_FILE = os.path.join(
        os.path.dirname(__file__), "integration/input_configurator_test.yaml"
    )

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary directory for the project"""
        temp_dir = tempfile.mkdtemp(prefix="test_project_")
        original_cwd = os.getcwd()
        os.chdir(temp_dir)
        yield temp_dir
        os.chdir(original_cwd)
        rmtree(temp_dir, ignore_errors=True)
        for f in os.listdir(original_cwd):
            if f.endswith(".project"):
                os.remove(os.path.join(original_cwd, f))

    @pytest.fixture
    def mock_shell_remote(self):
        """Mock Shell.connect for remote machines to avoid connection errors"""
        mock_shell = MagicMock()
        mock_shell.run.return_value = (0, [["riscv64"]], [])
        mock_shell.connect.return_value = mock_shell

        with patch("amphimixis.core.configurator.Shell") as mock_shell_class:
            mock_shell_class.return_value.connect.return_value = mock_shell
            mock_shell_class.return_value.run.return_value = (0, [["x86_64"]], [])
            yield mock_shell_class

    def test_parse_config_with_test_data(self, temp_project_dir, mock_shell_remote):
        """Test parsing configuration file with test data
        Expect: Configuration successful with correct builds created"""
        project = Project(temp_project_dir)

        result = configurator.parse_config(project, self.TEST_CONFIG_FILE)

        assert result is True
        assert len(project.builds) == 2

        build1 = project.builds[0]
        assert build1.build_machine.arch == Arch.X86
        assert build1.run_machine.arch == Arch.X86
        assert "test/run-tests" in build1.executables

        build2 = project.builds[1]
        assert build2.build_machine.arch == Arch.X86
        assert build2.run_machine.arch == Arch.RISCV

    def test_parse_config_build_machine_info(self, temp_project_dir, mock_shell_remote):
        """Test that build_machine info is correctly resolved
        Expect: Build machine has correct architecture"""
        project = Project(temp_project_dir)

        configurator.parse_config(project, self.TEST_CONFIG_FILE)

        build1 = project.builds[0]
        assert build1.build_machine.arch == Arch.X86

    def test_parse_config_run_machine_local(self, temp_project_dir, mock_shell_remote):
        """Test that local run_machine (x86) is correctly resolved
        Expect: Run machine has correct architecture and no address"""
        project = Project(temp_project_dir)

        configurator.parse_config(project, self.TEST_CONFIG_FILE)

        build1 = project.builds[0]
        assert build1.run_machine.arch == Arch.X86
        assert build1.run_machine.address is None

    def test_parse_config_run_machine_remote(self, temp_project_dir, mock_shell_remote):
        """Test that remote run_machine (riscv) is correctly resolved
        Expect: Run machine has correct architecture and address"""
        project = Project(temp_project_dir)

        configurator.parse_config(project, self.TEST_CONFIG_FILE)

        build2 = project.builds[1]
        assert build2.run_machine.auth is not None
        assert build2.run_machine.arch == Arch.RISCV
        assert build2.run_machine.address == "10.0.40.2"
        assert build2.run_machine.auth.username == "root"
        assert build2.run_machine.auth.password == "password"

    def test_parse_config_recipe_config_flags(
        self, temp_project_dir, mock_shell_remote
    ):
        """Test that recipe config_flags are correctly parsed
        Expect: Build has correct config_flags"""
        project = Project(temp_project_dir)

        configurator.parse_config(project, self.TEST_CONFIG_FILE)

        build1 = project.builds[0]
        assert build1.config_flags is not None
        assert "-DCMAKE_BUILD_TYPE=RelWithDebInfo" in build1.config_flags

        build2 = project.builds[1]
        assert build2.config_flags is not None
        assert "-DCMAKE_BUILD_TYPE=RelWithDebInfo" in build2.config_flags
        assert (
            "-DCMAKE_TOOLCHAIN_FILE=/opt/toolchains/riscv.cmake" in build2.config_flags
        )

    def test_parse_config_recipe_jobs(self, temp_project_dir, mock_shell_remote):
        """Test that recipe jobs are correctly parsed
        Expect: Build has correct jobs value"""
        project = Project(temp_project_dir)

        configurator.parse_config(project, self.TEST_CONFIG_FILE)

        build1 = project.builds[0]
        assert build1.jobs == 3

    def test_parse_config_executables(self, temp_project_dir, mock_shell_remote):
        """Test that executables are correctly parsed
        Expect: Builds have correct executables list"""
        project = Project(temp_project_dir)

        configurator.parse_config(project, self.TEST_CONFIG_FILE)

        for build in project.builds:
            assert "test/run-tests" in build.executables

    def test_parse_config_build_system(self, temp_project_dir, mock_shell_remote):
        """Test that build system is correctly set from config
        Expect: Project has CMake build system"""
        project = Project(temp_project_dir)

        configurator.parse_config(project, self.TEST_CONFIG_FILE)

        assert project.build_system is not None

    def test_parse_config_invalid_project_path(self):
        """Test parse_config with invalid project path
        Expect: Returns False"""
        project = Project("/nonexistent/project/path")

        result = configurator.parse_config(project, self.TEST_CONFIG_FILE)

        assert result is False

    def test_parse_config_invalid_config_file(self, temp_project_dir):
        """Test parse_config with invalid config file path
        Expect: Returns False"""
        project = Project(temp_project_dir)

        result = configurator.parse_config(project, "nonexistent_config.yaml")

        assert result is False
        assert result is False


@pytest.mark.unit
class TestQemuProvisioning:
    """Tests for QEMU machine provisioning and create_machine"""

    @pytest.fixture(autouse=True)
    def clear_provisioners(self):
        """Reset the module-level provisioner registry between tests."""
        configurator._qemu_provisioners.clear()
        yield
        configurator._qemu_provisioners.clear()

    def test_provision_failure_rolls_back_started_machines(self):
        """When provisioning a platform fails, started VMs must be stopped.

        Expect: Returns False and stops the already-provisioned machines."""
        input_config = {
            "platforms": [
                {"id": 1, "arch": "x86", "qemu": True},
                {"id": 2, "arch": "riscv", "qemu": True},
            ]
        }

        first = MagicMock()
        first.is_default_image = True
        second = MagicMock()
        second.start.side_effect = RuntimeError("SSH not available")

        with patch(
            "amphimixis.core.configurator.QemuMachineProvisioner",
            side_effect=[first, second],
        ):
            result = configurator.provision_qemu_machines(input_config)

        assert result is False
        first.stop.assert_called_once()
        second.stop.assert_called_once()
        assert configurator._qemu_provisioners == {}

    def test_provision_success_stores_provisioners(self):
        """Successful provisioning stores provisioners and returns True."""
        input_config = {"platforms": [{"id": 1, "arch": "riscv", "qemu": True}]}

        provisioner = MagicMock()
        provisioner.is_default_image = False
        provisioner.uses_default_files = True

        with patch(
            "amphimixis.core.configurator.QemuMachineProvisioner",
            return_value=provisioner,
        ):
            result = configurator.provision_qemu_machines(input_config)

        assert result is True
        assert 1 in configurator._qemu_provisioners

    def test_provision_default_files_installs_packages(self):
        """Auto-downloaded images get required packages installed."""
        input_config = {"platforms": [{"id": 1, "arch": "x86", "qemu": True}]}

        provisioner = MagicMock()
        provisioner.is_default_image = True
        provisioner.uses_default_files = True

        with patch(
            "amphimixis.core.configurator.QemuMachineProvisioner",
            return_value=provisioner,
        ):
            result = configurator.provision_qemu_machines(input_config)

        assert result is True
        provisioner.install_packages.assert_called_once()

    def test_provision_custom_files_skips_package_installation(self):
        """Custom VM files skip package installation, provisioning succeeds."""
        input_config = {
            "platforms": [
                {
                    "id": 1,
                    "arch": "x86",
                    "qemu": {"disk_image": "/tmp/image.qcow2"},
                    "username": "user",
                    "password": "pass",
                }
            ]
        }

        provisioner = MagicMock()
        provisioner.is_default_image = False
        provisioner.uses_default_files = False

        with patch(
            "amphimixis.core.configurator.QemuMachineProvisioner",
            return_value=provisioner,
        ):
            result = configurator.provision_qemu_machines(input_config)

        assert result is True
        assert 1 in configurator._qemu_provisioners
        provisioner.install_packages.assert_not_called()

    def test_create_machine_qemu_auto_download_default_credentials(self):
        """Auto-download qemu platforms default to root/root credentials.

        Expect: MachineInfo has 127.0.0.1 address and root/root auth."""
        machine = configurator.create_machine({"id": 1, "arch": "x86", "qemu": True})

        assert machine.arch == Arch.X86
        assert machine.address == "127.0.0.1"
        assert machine.auth is not None
        assert machine.auth.username == "root"
        assert machine.auth.password == "root"

    def test_create_machine_qemu_auto_download_forces_root_credentials(self):
        """Auto-download forces root/root even if others are provided."""
        machine = configurator.create_machine(
            {
                "id": 1,
                "arch": "riscv",
                "qemu": True,
                "username": "user",
                "password": "pass",
            }
        )

        assert machine.auth is not None
        assert machine.auth.username == "root"
        assert machine.auth.password == "root"

    def test_create_machine_qemu_custom_files_requires_credentials(self):
        """Custom files require explicit username and password."""
        with pytest.raises(ValueError):
            configurator.create_machine(
                {
                    "id": 1,
                    "arch": "x86",
                    "qemu": {"disk_image": "/tmp/image.qcow2"},
                }
            )

    def test_create_machine_qemu_custom_files_missing_password_raises(self):
        """Custom files without password raise ValueError."""
        with pytest.raises(ValueError):
            configurator.create_machine(
                {
                    "id": 1,
                    "arch": "x86",
                    "qemu": {"disk_image": "/tmp/image.qcow2"},
                    "username": "user",
                }
            )

    def test_create_machine_qemu_custom_files_with_credentials(self):
        """Custom files with credentials produce correct auth."""
        machine = configurator.create_machine(
            {
                "id": 1,
                "arch": "arm",
                "qemu": {"disk_image": "/tmp/image.qcow2"},
                "username": "user",
                "password": "pass",
            }
        )

        assert machine.arch == Arch.ARM
        assert machine.auth is not None
        assert machine.auth.username == "user"
        assert machine.auth.password == "pass"

    def test_create_machine_qemu_invalid_value_raises(self):
        """Non-bool non-dict qemu value raises ValueError."""
        with pytest.raises(ValueError):
            configurator.create_machine({"id": 1, "arch": "x86", "qemu": "yes"})

    def test_provision_skips_platforms_without_id_or_qemu(self):
        """Platforms without id or without qemu are skipped."""
        input_config = {
            "platforms": [
                {"arch": "x86", "qemu": True},
                {"id": 2, "arch": "x86"},
            ]
        }

        with patch(
            "amphimixis.core.configurator.QemuMachineProvisioner"
        ) as mock_provisioner:
            result = configurator.provision_qemu_machines(input_config)

        assert result is True
        mock_provisioner.assert_not_called()
        assert configurator._qemu_provisioners == {}

    def test_cleanup_qemu_machines_respects_keep_alive(self):
        """Cleanup stops regular VMs but keeps keep_alive ones."""
        regular = MagicMock()
        regular.keep_alive = False
        kept = MagicMock()
        kept.keep_alive = True
        configurator._qemu_provisioners[1] = regular
        configurator._qemu_provisioners[2] = kept

        configurator.cleanup_qemu_machines()

        regular.stop.assert_called_once()
        kept.stop.assert_not_called()
        assert configurator._qemu_provisioners == {}


@pytest.mark.unit
class TestGetRequiredPackages:
    """Tests for _get_required_packages package name selection."""

    def test_default_image_packages(self):
        """Default images use apk package names."""
        packages = configurator._get_required_packages(True, "cmake", "make")

        assert "perf" in packages
        assert "util-linux" in packages
        assert "cmake" in packages
        assert "make" in packages

    def test_debian_packages(self):
        """Custom (non-default) images use apt package names."""
        packages = configurator._get_required_packages(False, "cmake", "make")

        assert "linux-perf" in packages
        assert "time" in packages
        assert "cmake" in packages
        assert "make" in packages

    def test_ninja_runner(self):
        """Ninja runner adds ninja-build instead of make."""
        packages = configurator._get_required_packages(False, "cmake", "ninja")

        assert "ninja-build" in packages
        assert "make" not in packages

    def test_no_build_system_packages(self):
        """Unknown build system adds no build packages."""
        packages = configurator._get_required_packages(False, "unknown", "unknown")

        assert "cmake" not in packages
        assert "make" not in packages
        assert "bash" in packages


@pytest.mark.unit
class TestCreateQemuConfig:
    """Tests for create_qemu_config field mapping."""

    def test_maps_all_fields(self):
        """Every qemu dict field maps to QemuConfig, including memory."""
        qemu = configurator.create_qemu_config(
            {
                "machine": "virt",
                "cpu": "rv64",
                "memory": 8,
                "smp": 2,
                "kernel": "/tmp/kernel",
                "initrd": "/tmp/initrd",
                "disk_image": "/tmp/image.qcow2",
                "keep_alive": True,
                "extra_args": ["-enable-kvm"],
            }
        )

        assert qemu.machine == "virt"
        assert qemu.cpu == "rv64"
        assert qemu.memory == 8
        assert qemu.smp == 2
        assert str(qemu.kernel) == "/tmp/kernel"
        assert str(qemu.initrd) == "/tmp/initrd"
        assert str(qemu.disk_image) == "/tmp/image.qcow2"
        assert qemu.keep_alive is True
        assert qemu.extra_args == ["-enable-kvm"]

    def test_defaults(self):
        """Missing fields fall back to defaults."""
        qemu = configurator.create_qemu_config({})

        assert qemu.machine is None
        assert qemu.cpu is None
        assert qemu.memory == 4
        assert qemu.smp == 4
        assert qemu.keep_alive is False
        assert qemu.extra_args == []

    def test_extra_args_not_list_raises(self):
        """Non-list extra_args raises ValueError."""
        with pytest.raises(ValueError):
            configurator.create_qemu_config({"extra_args": "-enable-kvm"})


@pytest.mark.unit
class TestHasValidArch:
    """Tests for _has_valid_arch qemu/remote/local branching."""

    def _qemu_machine(self):
        """QEMU machine with loopback address and QemuConfig."""
        return configurator.create_machine(
            {
                "id": 1,
                "arch": "riscv",
                "qemu": True,
                "username": "root",
                "password": "root",
            }
        )

    def test_qemu_machine_uses_remote_check(self):
        """QEMU machine is checked via SSH, not as a local machine."""
        project = Project("/tmp/amphimixis")
        shell = MagicMock()
        shell.run.return_value = (0, [["riscv"]], "")
        with patch(
            "amphimixis.core.configurator.Shell", return_value=shell
        ) as mock_shell_class:
            shell.connect.return_value = shell
            assert configurator._has_valid_arch(project, self._qemu_machine()) is True

        mock_shell_class.assert_called_once()

    def test_qemu_machine_arch_mismatch(self):
        """QEMU machine with wrong arch fails the check."""
        project = Project("/tmp/amphimixis")
        shell = MagicMock()
        shell.run.return_value = (0, [["x86_64"]], "")
        with patch("amphimixis.core.configurator.Shell", return_value=shell):
            shell.connect.return_value = shell
            assert configurator._has_valid_arch(project, self._qemu_machine()) is False

    def test_local_machine_matching_arch_skips_shell(self):
        """Local machine with matching arch passes without SSH."""
        project = Project("/tmp/amphimixis")
        machine = configurator.create_machine({"id": 1, "arch": "x86"})
        with (
            patch("amphimixis.core.configurator.local_arch", return_value="x86_64"),
            patch("amphimixis.core.configurator.Shell") as mock_shell_class,
        ):
            assert configurator._has_valid_arch(project, machine) is True

        mock_shell_class.assert_not_called()
