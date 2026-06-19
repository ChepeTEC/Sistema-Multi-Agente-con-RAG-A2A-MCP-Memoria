import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.observability.langfuse_client import LangfuseTracer


class RaisingContextManager:
    def __enter__(self):
        raise RuntimeError("trace unavailable")

    def __exit__(self, exc_type, exc, tb):
        return None


class RaisingClient:
    def auth_check(self):
        return True

    def start_as_current_observation(self, as_type: str, name: str):
        return RaisingContextManager()

    def flush(self):
        raise RuntimeError("flush unavailable")


class FailingAuthClient:
    def auth_check(self):
        raise RuntimeError("auth unavailable")


class LangfuseClientTests(unittest.TestCase):
    def test_disabled_when_env_flag_is_false(self):
        with patch.dict("os.environ", {"LANGFUSE_ENABLED": "false"}, clear=True):
            tracer = LangfuseTracer()

        self.assertFalse(tracer.enabled)
        self.assertIsNone(tracer.client)
        self.assertIsNone(tracer.create_trace("test", {}))

    def test_initialization_failure_disables_observability(self):
        fake_module = SimpleNamespace(get_client=lambda: FailingAuthClient())

        with patch.dict(
            "os.environ",
            {
                "LANGFUSE_ENABLED": "true",
                "LANGFUSE_PUBLIC_KEY": "public",
                "LANGFUSE_SECRET_KEY": "secret",
            },
            clear=True,
        ), patch.dict(sys.modules, {"langfuse": fake_module}):
            tracer = LangfuseTracer()

        self.assertFalse(tracer.enabled)
        self.assertIsNone(tracer.client)
        self.assertIn("auth unavailable", tracer.disabled_reason)

    def test_trace_errors_return_none_instead_of_raising(self):
        fake_module = SimpleNamespace(get_client=lambda: RaisingClient())

        with patch.dict(
            "os.environ",
            {
                "LANGFUSE_ENABLED": "true",
                "LANGFUSE_PUBLIC_KEY": "public",
                "LANGFUSE_SECRET_KEY": "secret",
            },
            clear=True,
        ), patch.dict(sys.modules, {"langfuse": fake_module}):
            tracer = LangfuseTracer()

        self.assertTrue(tracer.enabled)
        self.assertIsNone(tracer.create_trace("test", {"question": "hola"}))
        self.assertIsNone(tracer.create_span({"closed": False}, "span"))
        self.assertIsNone(tracer.create_generation({"closed": False}, "gen", "m", "p", "r"))
        tracer.flush()

    def test_close_trace_errors_do_not_raise(self):
        tracer = LangfuseTracer()
        trace = {
            "closed": False,
            "context_manager": SimpleNamespace(
                __exit__=lambda *args: (_ for _ in ()).throw(RuntimeError("close failed"))
            ),
        }

        tracer.close_trace(trace)


if __name__ == "__main__":
    unittest.main()
