import unittest
from unittest.mock import MagicMock, patch

import app


class AppStartupTests(unittest.TestCase):
    def test_start_backend_reuses_existing_port(self):
        with patch("app.is_port_open", return_value=True), patch("app.subprocess.Popen") as popen:
            process = app.start_backend()

        self.assertIsNone(process)
        popen.assert_not_called()

    def test_start_backend_respects_langfuse_environment(self):
        fake_process = MagicMock()
        fake_process.terminate = MagicMock()

        with patch.dict("app.os.environ", {"LANGFUSE_ENABLED": "true"}), patch(
            "app.is_port_open",
            return_value=False,
        ), patch(
            "app.wait_for_port",
            return_value=True,
        ), patch("app.subprocess.Popen", return_value=fake_process) as popen:
            process = app.start_backend()

        self.assertIs(process, fake_process)
        kwargs = popen.call_args.kwargs
        self.assertEqual(kwargs["env"]["LANGFUSE_ENABLED"], "true")
        self.assertIn("uvicorn", popen.call_args.args[0])
        self.assertIn("src.api.server:app", popen.call_args.args[0])

    def test_start_frontend_sets_backend_url_and_strict_port(self):
        fake_process = MagicMock()

        with patch("app.is_port_open", return_value=False), patch(
            "app.wait_for_port",
            return_value=True,
        ), patch("app.npm_command", return_value="npm.cmd"), patch(
            "app.subprocess.Popen",
            return_value=fake_process,
        ) as popen:
            process = app.start_frontend()

        self.assertIs(process, fake_process)
        command = popen.call_args.args[0]
        kwargs = popen.call_args.kwargs
        self.assertEqual(command[0], "npm.cmd")
        self.assertIn("--strictPort", command)
        self.assertEqual(
            kwargs["env"]["VITE_API_BACKEND_URL"],
            f"http://{app.BACKEND_HOST}:{app.BACKEND_PORT}",
        )

    def test_stop_processes_only_stops_running_processes(self):
        running = MagicMock()
        running.poll.return_value = None
        stopped = MagicMock()
        stopped.poll.return_value = 0

        with patch("app.terminate_process_tree") as terminate_process_tree:
            app.stop_processes([None, running, stopped])

        terminate_process_tree.assert_called_once_with(running)
        running.wait.assert_called_once_with(timeout=10)
        self.assertNotIn(stopped, [call.args[0] for call in terminate_process_tree.call_args_list])

    def test_terminate_process_tree_uses_taskkill_on_windows(self):
        process = MagicMock()
        process.pid = 1234

        with patch("app.os.name", "nt"), patch("app.subprocess.run") as run:
            app.terminate_process_tree(process)

        self.assertEqual(run.call_args.args[0], ["taskkill", "/PID", "1234", "/T", "/F"])

    def test_ensure_docker_services_uses_compose_detached_build(self):
        with patch("app.subprocess.run") as run:
            app.ensure_docker_services()

        command = run.call_args.args[0]
        self.assertEqual(command, ["docker", "compose", "up", "-d", "--build"])
        self.assertTrue(run.call_args.kwargs["check"])

    def test_request_shutdown_marks_shutdown_requested(self):
        app.SHUTDOWN_REQUESTED = False

        app.request_shutdown(0, None)

        self.assertTrue(app.SHUTDOWN_REQUESTED)

    def test_install_signal_handlers_registers_shutdown_handler(self):
        with patch("app.signal.signal") as signal_handler:
            app.install_signal_handlers()

        registered_handlers = [call.args[1] for call in signal_handler.call_args_list]
        self.assertIn(app.request_shutdown, registered_handlers)


if __name__ == "__main__":
    unittest.main()
