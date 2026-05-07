#!/usr/bin/env python3
"""GUI application for running pytest tests with Kivy (works in .exe)."""

import contextlib
import io
import sys
import threading
from pathlib import Path

import pytest
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import BooleanProperty, ListProperty, ObjectProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.checkbox import CheckBox
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.app import App

# Загружаем kv-файл
kv_path = str(Path(__file__).parent / "test_runner.kv")
Builder.load_file(kv_path)


def get_base_dir() -> Path:
    """Return the root directory of the project (works in .exe)."""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent


class TestSelector(BoxLayout):
    active = BooleanProperty(False)
    test_name = StringProperty("")
    text_color = ListProperty([1, 1, 1, 1])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.checkbox = CheckBox(active=self.active, size_hint_x=0.1)
        self.label = Label(
            text=self.test_name,
            size_hint_x=0.9,
            color=self.text_color,
            halign="left",
            valign="middle",
            markup=True
        )
        self.label.bind(size=self.label.setter("text_size"))
        self.add_widget(self.checkbox)
        self.add_widget(self.label)
        self.bind(text_color=self._update_label_color)

    def _update_label_color(self, instance, value):
        self.label.color = value


class TestRunnerRoot(BoxLayout):
    available_markers = ListProperty(["all", "slow", "fast", "integration"])

    test_scroll = ObjectProperty(None)
    tests_container = ObjectProperty(None)
    search_input = ObjectProperty(None)
    marker_spinner = ObjectProperty(None)
    run_btn = ObjectProperty(None)
    stop_btn = ObjectProperty(None)
    progress_bar = ObjectProperty(None)
    log_text = ObjectProperty(None)
    log_scroll = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        self.base_dir = get_base_dir()
        if str(self.base_dir) not in sys.path:
            sys.path.insert(0, str(self.base_dir))

        self.all_tests = []
        self.test_selectors = {}
        self.running = False
        self.current_marker = "all"

        Clock.schedule_once(lambda dt: self.discover_tests(), 0)

    def discover_tests(self):
        tests_dir = self.base_dir / "tests"
        if not tests_dir.exists():
            self.all_tests = []
            self._refresh_test_list()
            return

        capture = io.StringIO()
        with contextlib.redirect_stdout(capture), contextlib.redirect_stderr(capture):
            pytest.main([str(tests_dir), "--collect-only", "-q"])

        output = capture.getvalue()
        test_names = set()
        for line in output.splitlines():
            if "::" not in line:
                continue
            if "[" in line:
                line = line.split("[")[0]
            parts = line.split("::")
            if len(parts) >= 2:
                module_file = parts[0]
                test_func = parts[1]
                module_name = Path(module_file).stem
                full_name = f"{module_name}.{test_func}"
                test_names.add(full_name)

        self.all_tests = [(name, self._get_markers_for_test(name)) for name in sorted(test_names)]
        self._refresh_test_list()

    def _get_markers_for_test(self, test_name):
        lower_name = test_name.lower()
        if "slow" in lower_name:
            return ["slow"]
        if "fast" in lower_name:
            return ["fast"]
        if "integration" in lower_name:
            return ["integration"]
        return ["fast"]

    def _refresh_test_list(self):
        marker = self.current_marker
        search_text = self.search_input.text.strip().lower() if self.search_input else ""

        if marker == "all":
            filtered = self.all_tests
        else:
            filtered = [item for item in self.all_tests if marker in item[1]]

        if search_text:
            filtered = [item for item in filtered if search_text in item[0].lower()]

        if self.tests_container:
            self.tests_container.clear_widgets()
            self.test_selectors.clear()
            for name, _ in filtered:
                selector = TestSelector(active=True, test_name=name)
                self.test_selectors[name] = selector
                self.tests_container.add_widget(selector)

    def get_selected_tests(self):
        return [name for name, selector in self.test_selectors.items() if selector.checkbox.active]

    def on_marker_change(self, marker):
        self.current_marker = marker
        self._refresh_test_list()

    def on_search_change(self, text):
        self._refresh_test_list()

    def run_selected_tests(self):
        selected = self.get_selected_tests()
        if not selected:
            self._show_popup("Нет тестов", "Не выбрано ни одного теста.")
            return
        self._run_tests(selected)

    def run_single_test(self, test_name):
        self._run_tests([test_name])

    def _run_tests(self, test_names):
        if self.running:
            return

        self.running = True
        self.run_btn.disabled = True
        self.stop_btn.disabled = False
        if self.progress_bar:
            self.progress_bar.value = 0
        self.log_text.text = ""

        thread = threading.Thread(target=self._run_tests_thread, args=(test_names,))
        thread.daemon = True
        thread.start()

    def _run_tests_thread(self, test_names):
        tests_dir = self.base_dir / "tests"
        args = []
        for full_name in test_names:
            module_name, func_name = full_name.split(".", 1)
            module_path = tests_dir / f"{module_name}.py"
            if module_path.exists():
                args.append(f"{module_path}::{func_name}")

        args += ["-v", "--durations=0"]

        capture = io.StringIO()
        with contextlib.redirect_stdout(capture), contextlib.redirect_stderr(capture):
            exit_code = pytest.main(args)

        output = capture.getvalue()
        for line in output.splitlines():
            if not self.running:
                break
            line = line.rstrip()
            if (line.startswith("=") or line.startswith("-") or
                line.startswith("platform") or "test session starts" in line or
                line.startswith("rootdir") or line.startswith("collected") or
                line.startswith("plugins") or line.strip() == ""):
                continue
            Clock.schedule_once(lambda dt, l=line: self._append_log_line(l))

        Clock.schedule_once(lambda dt: self._tests_finished())

    def stop_tests(self):
        if self.running:
            self.running = False
            self._append_log_line("Тесты остановлены пользователем.")

    def _append_log_line(self, line):
        if "PASSED" in line:
            colored = f"[color=00ff00]{line}[/color]"
        elif "FAILED" in line or "ERROR" in line:
            colored = f"[color=ff0000]{line}[/color]"
        elif "seconds" in line and "durations" not in line:
            colored = f"[color=0000ff]{line}[/color]"
        else:
            colored = line
        self.log_text.text += colored + "\n"
        self.log_text.scroll_y = 0

    def _tests_finished(self):
        if self.progress_bar:
            self.progress_bar.value = 100
        self.running = False
        self.run_btn.disabled = False
        self.stop_btn.disabled = True

    def save_log(self):
        content = BoxLayout(orientation="vertical")
        file_chooser = FileChooserListView()
        save_btn = BoxLayout(size_hint_y=0.1)

        def on_save(instance):
            selection = file_chooser.selection
            if selection:
                file_path = selection[0]
                clean_text = self.log_text.text
                clean_text = clean_text.replace("[color=00ff00]", "").replace("[color=ff0000]", "").replace("[color=0000ff]", "").replace("[/color]", "")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(clean_text)
                popup.dismiss()
                self._show_popup("Успех", f"Лог сохранён в {file_path}")
            else:
                popup.dismiss()

        cancel_btn = Button(text="Отмена", size_hint_x=0.3)
        cancel_btn.bind(on_release=lambda x: popup.dismiss())
        save_btn.add_widget(Label())
        save_btn.add_widget(Button(text="Сохранить", size_hint_x=0.3, on_release=on_save))
        save_btn.add_widget(cancel_btn)
        content.add_widget(file_chooser)
        content.add_widget(save_btn)

        popup = Popup(title="Сохранить лог", content=content, size_hint=(0.9, 0.9))
        popup.open()

    def _show_popup(self, title, message):
        popup = Popup(title=title, content=Label(text=message), size_hint=(0.6, 0.4))
        popup.open()


class TestRunnerApp(App):
    theme_style = StringProperty("Dark")

    def build(self):
        self.title = "Test Runner"
        return TestRunnerRoot()


if __name__ == "__main__":
    TestRunnerApp().run()