import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import time


BAUDRATE = 115200
MAX_BYTES = 1000


def refresh_ports():
    ports = serial.tools.list_ports.comports()

    port_box["values"] = [p.device for p in ports]

    if ports:
        port_box.current(0)
        status_label.config(text="Arduino найдена")
    else:
        status_label.config(text="Arduino не найдена")


def send_text():
    port = port_box.get()

    if not port:
        messagebox.showerror(
            "Ошибка",
            "Выбери COM-порт Arduino."
        )
        return

    text = text_box.get("1.0", "end-1c")

    if not text:
        messagebox.showerror(
            "Ошибка",
            "Текст пустой."
        )
        return

    data = text.encode("utf-8")

    if len(data) > MAX_BYTES:
        messagebox.showerror(
            "Ошибка",
            f"Текст слишком большой.\n"
            f"Размер: {len(data)} байт\n"
            f"Максимум: {MAX_BYTES} байт"
        )
        return

    try:
        status_label.config(
            text="Подключение к Arduino..."
        )
        root.update()

        ser = serial.Serial(
            port=port,
            baudrate=BAUDRATE,
            timeout=5,
            write_timeout=5
        )

        # Arduino UNO перезапускается
        # после открытия COM-порта
        time.sleep(2)

        # Очистить входной буфер
        ser.reset_input_buffer()

        # Сначала отправляем длину текста
        command = f"TEXT:{len(data)}\n"

        ser.write(command.encode("ascii"))
        ser.flush()

        time.sleep(0.2)

        # Затем сам текст
        ser.write(data)
        ser.flush()

        status_label.config(
            text="Текст отправлен, ждём Arduino..."
        )
        root.update()

        # Ждём ответ
        response = ser.readline()

        ser.close()

        response = response.decode(
            "utf-8",
            errors="ignore"
        ).strip()

        print("Arduino:", response)

        if "OK: TEXT SAVED" in response:

            status_label.config(
                text="✓ Текст успешно записан!"
            )

            messagebox.showinfo(
                "Готово",
                "Текст записан в Arduino."
            )

        elif response:

            status_label.config(
                text=response
            )

            messagebox.showwarning(
                "Ответ Arduino",
                response
            )

        else:

            status_label.config(
                text="Arduino не ответила"
            )

            messagebox.showwarning(
                "Нет ответа",
                "Arduino не прислала ответ.\n\n"
                "Проверь COM-порт."
            )

    except Exception as e:

        status_label.config(
            text="Ошибка подключения"
        )

        messagebox.showerror(
            "Ошибка",
            str(e)
        )


def update_counter(event=None):

    text = text_box.get(
        "1.0",
        "end-1c"
    )

    size = len(text.encode("utf-8"))

    counter_label.config(
        text=f"Размер: {size} / {MAX_BYTES} байт"
    )


def test_text():

    text_box.delete(
        "1.0",
        "end"
    )

    text_box.insert(
        "1.0",
        """TEST

Привет!

Arduino UNO

Это тестовая шпаргалка.

123 + 456 = 579"""
    )

    update_counter()


# =====================================
# ОКНО
# =====================================

root = tk.Tk()

root.title("Arduino Mini Cheat Sheet")

root.geometry("700x600")


title = tk.Label(
    root,
    text="Arduino Mini Cheat Sheet",
    font=("Arial", 20, "bold")
)

title.pack(pady=15)


# =====================================
# COM PORT
# =====================================

port_frame = tk.Frame(root)

port_frame.pack(pady=5)


tk.Label(
    port_frame,
    text="COM-порт:"
).pack(side="left", padx=5)


port_box = ttk.Combobox(
    port_frame,
    state="readonly",
    width=15
)

port_box.pack(side="left", padx=5)


refresh_button = tk.Button(
    port_frame,
    text="Обновить",
    command=refresh_ports
)

refresh_button.pack(side="left", padx=5)


# =====================================
# TEXT
# =====================================

tk.Label(
    root,
    text="Текст:",
    font=("Arial", 12, "bold")
).pack(
    anchor="w",
    padx=20,
    pady=(15, 5)
)


text_frame = tk.Frame(root)

text_frame.pack(
    fill="both",
    expand=True,
    padx=20
)


scrollbar = tk.Scrollbar(
    text_frame
)

scrollbar.pack(
    side="right",
    fill="y"
)


text_box = tk.Text(
    text_frame,
    wrap="word",
    font=("Arial", 13),
    yscrollcommand=scrollbar.set
)

text_box.pack(
    fill="both",
    expand=True
)


scrollbar.config(
    command=text_box.yview
)


text_box.bind(
    "<KeyRelease>",
    update_counter
)


# =====================================
# COUNTER
# =====================================

counter_label = tk.Label(
    root,
    text="Размер: 0 / 1000 байт"
)

counter_label.pack(pady=5)


# =====================================
# BUTTONS
# =====================================

button_frame = tk.Frame(root)

button_frame.pack(pady=10)


tk.Button(
    button_frame,
    text="Тестовый текст",
    width=18,
    height=2,
    command=test_text
).pack(
    side="left",
    padx=10
)


tk.Button(
    button_frame,
    text="ЗАПИСАТЬ В ARDUINO",
    width=25,
    height=2,
    command=send_text
).pack(
    side="left",
    padx=10
)


# =====================================
# STATUS
# =====================================

status_label = tk.Label(
    root,
    text="Готово"
)

status_label.pack(pady=5)


refresh_ports()

root.mainloop()