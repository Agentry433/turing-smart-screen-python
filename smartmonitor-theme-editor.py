#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from pathlib import Path
import sys

from library.pythoncheck import check_python_version

check_python_version()

try:
    import tkinter.ttk as ttk
    from tkinter import *
    from tkinter import filedialog, messagebox
    from PIL import Image, ImageTk
except Exception as exc:
    raise SystemExit(f"Tkinter import failed: {exc}") from exc

from library.smartmonitor_ui import (
    FontSpec,
    Geometry,
    SensorSpec,
    SmartMonitorTheme,
    Widget,
    WidgetParent,
    parse_ui_file,
    write_theme_file,
    _hex_to_int,
)


def _safe_int(value: str, default: int = 0) -> int:
    try:
        return int(value.strip())
    except Exception:
        return default


class SmartMonitorThemeEditor:
    def __init__(self, ui_path: str):
        self.ui_path = Path(ui_path).expanduser().resolve()
        self.theme: SmartMonitorTheme = parse_ui_file(self.ui_path)
        self.window = Tk()
        self.window.title(f"SmartMonitor Theme Editor - {self.ui_path.name}")
        self.window.geometry("1520x700")
        self.selection = None
        self.canvas_item_map = {}
        self.canvas_background_image = None
        self.canvas_widget_images = []
        self.drag_start = None

        self.items_list = Listbox(self.window, exportselection=False)
        self.items_list.place(x=10, y=10, width=260, height=560)
        self.items_list.bind("<<ListboxSelect>>", self.on_select)

        self.path_label = ttk.Label(self.window, text=str(self.ui_path))
        self.path_label.place(x=280, y=10)

        self.name_var = StringVar()
        self.type_var = StringVar()
        self.x_var = StringVar()
        self.y_var = StringVar()
        self.w_var = StringVar()
        self.h_var = StringVar()
        self.text_var = StringVar()
        self.font_name_var = StringVar()
        self.font_size_var = StringVar()
        self.font_color_var = StringVar()
        self.datetime_var = StringVar()
        self.sensor_fast_var = StringVar()
        self.sensor_type_var = StringVar()
        self.sensor_name_var = StringVar()
        self.sensor_reading_var = StringVar()
        self.bg_image_var = StringVar()
        self.image_path_var = StringVar()
        self.bg_color_var = StringVar()

        self._entry("Object name", self.name_var, 280, 50)
        self._entry("Type", self.type_var, 280, 85, readonly=True)
        self._entry("X", self.x_var, 280, 120, width=55)
        self._entry("Y", self.y_var, 370, 120, width=55)
        self._entry("Width", self.w_var, 560, 120, width=45)
        self._entry("Height", self.h_var, 760, 120, width=45)
        self._entry("Text", self.text_var, 280, 160, width=360)
        self._entry("Font name", self.font_name_var, 280, 195, width=140)
        self._entry("Size", self.font_size_var, 570, 195, width=40)
        self._entry("Color", self.font_color_var, 760, 195, width=90)
        self._entry("Date/time fmt", self.datetime_var, 280, 230, width=180)
        self._entry("Fast sensor", self.sensor_fast_var, 280, 265, width=60)
        self._entry("Sensor type", self.sensor_type_var, 450, 265, width=100)
        self._entry("Sensor name", self.sensor_name_var, 670, 265, width=150)
        self._entry("Reading", self.sensor_reading_var, 280, 300, width=430)
        self._entry("Background image", self.bg_image_var, 280, 335, width=430)
        ttk.Button(self.window, text="Browse BG", command=self.on_pick_background_image).place(x=825, y=332, width=95, height=28)
        self._entry("Image path", self.image_path_var, 280, 370, width=430)
        ttk.Button(self.window, text="Browse Img", command=self.on_pick_widget_image).place(x=825, y=367, width=95, height=28)
        self._entry("Background color", self.bg_color_var, 280, 405, width=140)

        ttk.Button(self.window, text="Apply", command=self.on_apply).place(x=280, y=450, width=90, height=36)
        ttk.Button(self.window, text="Save UI", command=self.on_save).place(x=380, y=450, width=90, height=36)
        ttk.Button(self.window, text="Save As", command=self.on_save_as).place(x=480, y=450, width=90, height=36)
        ttk.Button(self.window, text="Add Number", command=self.on_add_number).place(x=580, y=450, width=100, height=36)
        ttk.Button(self.window, text="Add DateTime", command=self.on_add_datetime).place(x=280, y=495, width=120, height=36)
        ttk.Button(self.window, text="Delete", command=self.on_delete).place(x=410, y=495, width=90, height=36)

        self.canvas = Canvas(self.window, width=480, height=320, bg="#111827", highlightthickness=1, highlightbackground="#64748b")
        self.canvas.place(x=1000, y=50)
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)

        self.canvas_hint = ttk.Label(
            self.window,
            text="Canvas preview 480x320. Drag widgets with the mouse; coordinates update live.",
        )
        self.canvas_hint.place(x=1000, y=380)

        note = (
            "Minimal editor: geometry, text, font, basic sensor fields, background, add/delete number and datetime widgets.\n"
            "After saving .ui, go back to configure.py and use 'Convert UI->DAT'."
        )
        ttk.Label(self.window, text=note).place(x=280, y=550)

        self.refresh_items()
        if self.items_list.size():
            self.items_list.selection_set(0)
            self.on_select()

    def _entry(self, label: str, var: StringVar, x: int, y: int, width: int = 160, readonly: bool = False):
        ttk.Label(self.window, text=label).place(x=x, y=y)
        state = "readonly" if readonly else "normal"
        ttk.Entry(self.window, textvariable=var, state=state).place(x=x + 110, y=y, width=width)

    def refresh_items(self):
        self.items_list.delete(0, END)
        for index, parent in enumerate(self.theme.widget_parents):
            self.items_list.insert(END, f"BG {index}: {parent.object_name}")
        for index, widget in enumerate(self.theme.widgets):
            self.items_list.insert(END, f"W {index}: {widget.object_name} (type {widget.widget_type})")
        self.render_canvas()

    def _selected_obj(self):
        if self.selection is None:
            return None
        kind, index = self.selection
        if kind == "parent":
            return self.theme.widget_parents[index]
        return self.theme.widgets[index]

    def _selection_to_list_index(self):
        if self.selection is None:
            return None
        kind, index = self.selection
        if kind == "parent":
            return index
        return len(self.theme.widget_parents) + index

    def _set_selection(self, kind: str, index: int):
        self.selection = (kind, index)
        list_index = self._selection_to_list_index()
        if list_index is not None:
            self.items_list.selection_clear(0, END)
            self.items_list.selection_set(list_index)
            self.items_list.activate(list_index)
        self._populate_form_from_selection()
        self.render_canvas()

    def _theme_base_dir(self) -> Path:
        return self.ui_path.parent

    def _resolve_asset_path(self, raw_path: str) -> Path:
        path = Path(raw_path)
        if path.is_absolute():
            return path
        raw = raw_path[2:] if raw_path.startswith("./") else raw_path
        return self._theme_base_dir() / raw

    def _relative_asset_path(self, path: Path) -> str:
        try:
            relative = path.resolve().relative_to(self._theme_base_dir().resolve())
            return "./" + relative.as_posix()
        except Exception:
            return str(path.resolve())

    def _populate_form_from_selection(self):
        obj = self._selected_obj()
        if obj is None:
            return
        if isinstance(obj, WidgetParent):
            self.name_var.set(obj.object_name)
            self.type_var.set("background")
            self.x_var.set(str(obj.geometry.x))
            self.y_var.set(str(obj.geometry.y))
            self.w_var.set(str(obj.geometry.width))
            self.h_var.set(str(obj.geometry.height))
            self.text_var.set("")
            self.font_name_var.set("")
            self.font_size_var.set("")
            self.font_color_var.set("")
            self.datetime_var.set("")
            self.sensor_fast_var.set("")
            self.sensor_type_var.set("")
            self.sensor_name_var.set("")
            self.sensor_reading_var.set("")
            self.bg_image_var.set(obj.background_image_path)
            self.image_path_var.set("")
            self.bg_color_var.set(obj.background_color_raw)
            return

        self.name_var.set(obj.object_name)
        self.type_var.set(str(obj.widget_type))
        self.x_var.set(str(obj.geometry.x))
        self.y_var.set(str(obj.geometry.y))
        self.w_var.set(str(obj.geometry.width))
        self.h_var.set(str(obj.geometry.height))
        self.text_var.set(obj.font.text if obj.font else "")
        self.font_name_var.set(obj.font.name if obj.font else "")
        self.font_size_var.set(str(obj.font.size if obj.font else 0))
        self.font_color_var.set(obj.font.color_raw if obj.font else "")
        self.datetime_var.set(obj.datetime_format)
        self.sensor_fast_var.set(str(obj.sensor.fast_sensor if obj.sensor else -1))
        self.sensor_type_var.set(obj.sensor.sensor_type_name if obj.sensor else "")
        self.sensor_name_var.set(obj.sensor.sensor_name if obj.sensor else "")
        self.sensor_reading_var.set(obj.sensor.reading_name if obj.sensor else "")
        self.bg_image_var.set("")
        self.image_path_var.set(str(obj.raw_fields.get("imagePath", "")))
        self.bg_color_var.set("")

    def render_canvas(self):
        self.canvas.delete("all")
        self.canvas_item_map = {}
        self.canvas_widget_images = []

        background = self.theme.widget_parents[0] if self.theme.widget_parents else None
        if background is not None:
            if background.background_image_path:
                try:
                    image_path = self._resolve_asset_path(background.background_image_path)
                    image = Image.open(image_path).convert("RGB")
                    if image.size != (480, 320):
                        image = image.resize((480, 320), Image.Resampling.LANCZOS)
                    self.canvas_background_image = ImageTk.PhotoImage(image)
                    self.canvas.create_image(0, 0, anchor=NW, image=self.canvas_background_image)
                except Exception:
                    self.canvas_background_image = None
                    self.canvas.create_rectangle(0, 0, 480, 320, fill="#0f1720", outline="")
            else:
                self.canvas_background_image = None
                fill = background.background_color_raw if background.background_color_raw else "#0f1720"
                self.canvas.create_rectangle(0, 0, 480, 320, fill=fill, outline="")

        selected = self.selection
        for index, widget in enumerate(self.theme.widgets):
            x1 = widget.geometry.x
            y1 = widget.geometry.y
            x2 = x1 + widget.geometry.width
            y2 = y1 + widget.geometry.height
            outline = "#22c55e"
            fill = ""
            width = 2
            if selected == ("widget", index):
                outline = "#f59e0b"
                width = 3
            if widget.widget_type == 4 and widget.raw_fields.get("imagePath"):
                try:
                    image_path = self._resolve_asset_path(str(widget.raw_fields.get("imagePath", "")))
                    image = Image.open(image_path)
                    if image.size != (widget.geometry.width, widget.geometry.height):
                        image = image.resize((widget.geometry.width, widget.geometry.height), Image.Resampling.LANCZOS)
                    tk_image = ImageTk.PhotoImage(image)
                    self.canvas_widget_images.append(tk_image)
                    image_id = self.canvas.create_image(x1, y1, anchor=NW, image=tk_image)
                    self.canvas_item_map[image_id] = ("widget", index)
                except Exception:
                    pass
            rect_id = self.canvas.create_rectangle(x1, y1, x2, y2, outline=outline, width=width, fill=fill)
            label = widget.object_name or f"type {widget.widget_type}"
            text = self.canvas.create_text(x1 + 4, y1 + 4, anchor=NW, text=label, fill=outline, font=("Arial", 9, "bold"))
            self.canvas_item_map[rect_id] = ("widget", index)
            self.canvas_item_map[text] = ("widget", index)

    def _canvas_select_current(self, selection):
        if selection is None:
            return
        kind, index = selection
        self._set_selection(kind, index)

    def on_select(self, _event=None):
        selection = self.items_list.curselection()
        if not selection:
            return
        index = selection[0]
        if index < len(self.theme.widget_parents):
            self._set_selection("parent", index)
        else:
            widget_index = index - len(self.theme.widget_parents)
            self._set_selection("widget", widget_index)

    def on_apply(self):
        obj = self._selected_obj()
        if obj is None:
            return

        obj.object_name = self.name_var.get().strip() or obj.object_name
        obj.geometry = Geometry(
            x=_safe_int(self.x_var.get(), obj.geometry.x),
            y=_safe_int(self.y_var.get(), obj.geometry.y),
            width=_safe_int(self.w_var.get(), obj.geometry.width),
            height=_safe_int(self.h_var.get(), obj.geometry.height),
        )

        if isinstance(obj, WidgetParent):
            obj.background_image_path = self.bg_image_var.get().strip()
            obj.background_color_raw = self.bg_color_var.get().strip() or obj.background_color_raw
            obj.background_color = _hex_to_int(obj.background_color_raw, obj.background_color)
        else:
            if obj.font is None:
                obj.font = FontSpec()
            obj.font.text = self.text_var.get()
            obj.font.name = self.font_name_var.get().strip() or obj.font.name
            obj.font.size = _safe_int(self.font_size_var.get(), obj.font.size)
            obj.font.color_raw = self.font_color_var.get().strip() or obj.font.color_raw
            obj.font.color = _hex_to_int(obj.font.color_raw, obj.font.color)
            obj.datetime_format = self.datetime_var.get().strip()
            image_path = self.image_path_var.get().strip()
            if image_path:
                obj.raw_fields["imagePath"] = image_path
            elif "imagePath" in obj.raw_fields:
                del obj.raw_fields["imagePath"]

            sensor_fast = self.sensor_fast_var.get().strip()
            if sensor_fast or self.sensor_type_var.get().strip() or self.sensor_name_var.get().strip() or self.sensor_reading_var.get().strip():
                obj.sensor = SensorSpec(
                    fast_sensor=_safe_int(sensor_fast, obj.sensor.fast_sensor if obj.sensor else -1),
                    sensor_type_name=self.sensor_type_var.get().strip(),
                    sensor_name=self.sensor_name_var.get().strip(),
                    reading_name=self.sensor_reading_var.get().strip(),
                    is_div_1204=bool(obj.sensor.is_div_1204) if obj.sensor else False,
                )
            else:
                obj.sensor = None

        self.refresh_items()
        self._populate_form_from_selection()

    def _next_ids(self, widget_type: int) -> tuple[int, int]:
        global_id = max([widget.global_id for widget in self.theme.widgets] + [-1]) + 1
        same_type_id = sum(1 for widget in self.theme.widgets if widget.widget_type == widget_type)
        return global_id, same_type_id

    def on_add_number(self):
        global_id, same_type_id = self._next_ids(5)
        widget = Widget(
            global_id=global_id,
            same_type_id=same_type_id,
            parent_name="background",
            object_name=f"Number {same_type_id}",
            widget_type=5,
            geometry=Geometry(40, 40, 100, 40),
            font=FontSpec(text="42", name="Arial", color_raw="0xffffffff", color=0xFFFFFFFF, size=20, bold_value=1, italic_value=0, bold=True, italic=False),
            sensor=SensorSpec(fast_sensor=1, sensor_type_name="Temperature", sensor_name="CPU", reading_name="CPU Package"),
            raw_fields={"hAlign": "1"},
        )
        self.theme.widgets.append(widget)
        self.refresh_items()
        self._set_selection("widget", len(self.theme.widgets) - 1)

    def on_add_datetime(self):
        global_id, same_type_id = self._next_ids(6)
        widget = Widget(
            global_id=global_id,
            same_type_id=same_type_id,
            parent_name="background",
            object_name=f"DateTime {same_type_id}",
            widget_type=6,
            geometry=Geometry(40, 40, 160, 30),
            font=FontSpec(text="12:00:00", name="Arial", color_raw="0xffffffff", color=0xFFFFFFFF, size=18, bold_value=1, italic_value=0, bold=True, italic=False),
            datetime_format="hh:nn:ss",
            raw_fields={"hAlign": "1"},
        )
        self.theme.widgets.append(widget)
        self.refresh_items()
        self._set_selection("widget", len(self.theme.widgets) - 1)

    def on_delete(self):
        if self.selection is None:
            return
        kind, index = self.selection
        if kind == "parent":
            messagebox.showwarning("Delete blocked", "Background root cannot be deleted.", parent=self.window)
            return
        del self.theme.widgets[index]
        self.selection = None
        self.refresh_items()

    def on_pick_background_image(self):
        obj = self._selected_obj()
        if not isinstance(obj, WidgetParent):
            messagebox.showinfo(
                "Select background",
                "Choose the background item in the list first, then pick an image.",
                parent=self.window,
            )
            return

        initial_dir = str((self._theme_base_dir() / "images").resolve())
        image_path = filedialog.askopenfilename(
            parent=self.window,
            title="Choose background image",
            initialdir=initial_dir if Path(initial_dir).is_dir() else str(self._theme_base_dir()),
            filetypes=(
                ("Images", "*.png *.jpg *.jpeg *.bmp"),
                ("All files", "*.*"),
            ),
        )
        if not image_path:
            return

        raw_path = self._relative_asset_path(Path(image_path))
        self.bg_image_var.set(raw_path)
        obj.background_image_path = raw_path
        self.render_canvas()

    def on_pick_widget_image(self):
        obj = self._selected_obj()
        if not isinstance(obj, Widget) or obj.widget_type != 4:
            messagebox.showinfo(
                "Select image widget",
                "Choose an image widget in the list or on the canvas first, then pick an image.",
                parent=self.window,
            )
            return

        initial_dir = str((self._theme_base_dir() / "images").resolve())
        image_path = filedialog.askopenfilename(
            parent=self.window,
            title="Choose widget image",
            initialdir=initial_dir if Path(initial_dir).is_dir() else str(self._theme_base_dir()),
            filetypes=(
                ("Images", "*.png *.jpg *.jpeg *.bmp"),
                ("All files", "*.*"),
            ),
        )
        if not image_path:
            return

        raw_path = self._relative_asset_path(Path(image_path))
        self.image_path_var.set(raw_path)
        obj.raw_fields["imagePath"] = raw_path
        self.render_canvas()

    def on_canvas_press(self, event):
        canvas_item = self.canvas.find_closest(event.x, event.y)
        if not canvas_item:
            return
        selection = self.canvas_item_map.get(canvas_item[0])
        if selection is None:
            if self.theme.widget_parents:
                self._set_selection("parent", 0)
            return
        self._canvas_select_current(selection)
        obj = self._selected_obj()
        if isinstance(obj, Widget):
            self.drag_start = (event.x, event.y, obj.geometry.x, obj.geometry.y)

    def on_canvas_drag(self, event):
        if self.drag_start is None or self.selection is None:
            return
        obj = self._selected_obj()
        if not isinstance(obj, Widget):
            return
        start_x, start_y, base_x, base_y = self.drag_start
        delta_x = event.x - start_x
        delta_y = event.y - start_y
        obj.geometry.x = max(0, min(480 - obj.geometry.width, base_x + delta_x))
        obj.geometry.y = max(0, min(320 - obj.geometry.height, base_y + delta_y))
        self.x_var.set(str(obj.geometry.x))
        self.y_var.set(str(obj.geometry.y))
        self.render_canvas()

    def on_canvas_release(self, _event):
        self.drag_start = None

    def on_save(self):
        self.on_apply()
        write_theme_file(self.ui_path, self.theme)
        messagebox.showinfo("Saved", f"Saved UI source:\n{self.ui_path}", parent=self.window)

    def on_save_as(self):
        self.on_apply()
        target = filedialog.asksaveasfilename(
            parent=self.window,
            title="Save SmartMonitor UI As",
            defaultextension=".ui",
            filetypes=(("Vendor UI", "*.ui"), ("All files", "*.*")),
            initialfile=self.ui_path.name,
        )
        if not target:
            return
        self.ui_path = Path(target).expanduser().resolve()
        write_theme_file(self.ui_path, self.theme)
        self.path_label.config(text=str(self.ui_path))
        messagebox.showinfo("Saved", f"Saved UI source:\n{self.ui_path}", parent=self.window)

    def run(self):
        self.window.mainloop()


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: smartmonitor-theme-editor.py <path-to-ui>")
    editor = SmartMonitorThemeEditor(sys.argv[1])
    editor.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
