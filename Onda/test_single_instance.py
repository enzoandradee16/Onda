import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch
import uuid

from single_instance import SingleInstance, run_single_instance


@unittest.skipUnless(os.name == "nt", "Windows named kernel objects")
class SingleInstanceTests(unittest.TestCase):
    def setUp(self):
        self.name = "Local\\Onda.Test." + uuid.uuid4().hex

    def child(self, code):
        prefix = f"import sys; sys.path.insert(0, {str(Path(__file__).parent)!r}); from single_instance import SingleInstance; "
        return subprocess.run(
            [sys.executable, "-s", "-c", prefix + code],
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_second_process_is_rejected_and_reopening_is_allowed_after_close(self):
        with SingleInstance(self.name) as primary:
            self.assertTrue(primary.primary)
            child = self.child(
                f"g=SingleInstance({self.name!r}); print(g.primary); g.notify(); g.close()"
            )
            self.assertEqual(child.returncode, 0, child.stderr)
            self.assertEqual(child.stdout.strip(), "False")
            self.assertTrue(primary.activation_requested())
            self.assertFalse(primary.activation_requested())
        child = self.child(
            f"g=SingleInstance({self.name!r}); print(g.primary); g.close()"
        )
        self.assertEqual(child.stdout.strip(), "True")

    def test_duplicate_warns_without_creating_a_tk_app(self):
        with SingleInstance(self.name) as primary:
            second = SingleInstance(self.name)
            factory = Mock(side_effect=AssertionError("Duplicate app created"))
            with (
                patch("single_instance.SingleInstance", return_value=second),
                patch("single_instance.already_open_message") as warning,
            ):
                self.assertEqual(run_single_instance(factory), 0)
            warning.assert_called_once_with()
            factory.assert_not_called()
            self.assertTrue(primary.activation_requested())

    def test_crashed_process_does_not_leave_a_stale_lock(self):
        code = f"import sys; sys.path.insert(0, {str(Path(__file__).parent)!r}); from single_instance import SingleInstance; g=SingleInstance({self.name!r}); print(g.primary, flush=True); input()"
        process = subprocess.Popen(
            [sys.executable, "-s", "-c", code],
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            self.assertEqual(process.stdout.readline().strip(), "True")
            with SingleInstance(self.name) as second:
                self.assertFalse(second.primary)
            process.terminate()
            process.wait(timeout=10)
            with SingleInstance(self.name) as reopened:
                self.assertTrue(reopened.primary)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)
            process.communicate(timeout=10)

    def test_duplicate_warning_does_not_keep_lock_after_original_closes(self):
        primary = SingleInstance(self.name)
        second = SingleInstance(self.name)
        try:
            self.assertFalse(second.primary)
            primary.close()
            with SingleInstance(self.name) as reopened:
                self.assertTrue(reopened.primary)
        finally:
            primary.close()
            second.close()

    def test_failed_startup_releases_guard(self):
        guard = SingleInstance(self.name)
        with patch("single_instance.SingleInstance", return_value=guard):
            with self.assertRaisesRegex(RuntimeError, "startup"):
                run_single_instance(Mock(side_effect=RuntimeError("startup")))
        with SingleInstance(self.name) as reopened:
            self.assertTrue(reopened.primary)

    @unittest.skipUnless(os.environ.get("ONDA_UI_TESTS"), "Tk integration")
    def test_notification_restores_existing_window(self):
        import tkinter as tk

        root = tk.Tk()
        root.geometry("400x240")
        try:
            root.update()
            root.iconify()
            root.update()
            with (
                SingleInstance(self.name) as primary,
                SingleInstance(self.name) as second,
            ):
                primary.watch(root)
                second.notify()
                root.after(300, root.quit)
                root.mainloop()
                root.update()
                self.assertEqual(root.state(), "normal")
                self.assertTrue(root.winfo_viewable())
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
