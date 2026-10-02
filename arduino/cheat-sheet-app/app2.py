import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import time


BAUDRATE = 115200
MAX_BYTES = 1000


def refresh_ports():
    current = port_box.get()

    ports = [p.device for p in serial.tools.list_ports.comports()]

    port_box["values"] = ports

    # Не менять выбранный порт после обновления
    if current in ports:
        port_box.set(current)
    elif ports:
        port_box.set(ports[0])

    status.config(text=f"Найдено портов: {len(ports)}")


def send_text():

    port = port_box.get()

    if not port:
        messagebox.showerror(
            "Ошибка",
            "Выбери COM-порт."
        )
        return

    text = text_box.get("1.0", "end-1c")

    if not text:
        messagebox.showerror(
            "Ошибка",
            "Введи текст."
        )
        return

    data = text.encode("utf-8")

    if len(data) > MAX_BYTES:
        messagebox.showerror(
            "Ошибка",
            f"Текст слишком большой.\n"
            f"{len(data)} байт из {MAX_BYTES}"
        )
        return

    arduino = None

    try:
        status.config(text="Подключение...")
        root.update()

        arduino = serial.Serial(
            port=port,
            baudrate=115200,
            timeout=10,
            write_timeout=10
        )

        # UNO перезапускается при открытии COM
        time.sleep(2)

        arduino.reset_input_buffer()

        # Отправляем заголовок
        command = f"TEXT:{len(data)}\n"

        arduino.write(command.encode("ascii"))
        arduino.flush()

        status.config(text="Arduino готовится принять текст...")
        root.update()

        # Ждём READY
        response = arduino.readline().decode(
            "utf-8",
            errors="ignore"
        ).strip()

        print("Arduino:", response)

        if response != f"READY:{len(data)}":

            raise Exception(
                f"Arduino ответила: {response}"
            )

        # Теперь отправляем текст
        arduino.write(data)
        arduino.flush()

        status.config(text="Передача текста...")
        root.update()

        # Ждём подтверждение сохранения
        response = arduino.readline().decode(
            "utf-8",
            errors="ignore"
        ).strip()

        print("Arduino:", response)

        arduino.close()
        arduino = None

        if response == "OK:SAVED":

            status.config(
                text="✓ Текст сохранён в Arduino"
            )

            messagebox.showinfo(
                "Готово",
                "Arduino получила и сохранила текст!"
            )

        else:

            raise Exception(
                f"Arduino не подтвердила сохранение.\n"
                f"Ответ: {response}"
            )

    except Exception as e:

        if arduino is not None:
            try:
                arduino.close()
            except:
                pass

        status.config(text="Ошибка передачи")

        messagebox.showerror(
            "Ошибка передачи",
            str(e)
        )


def test_text():

    text_box.delete(
        "1.0",
        "end"
    )

    text_box.insert(
        "1.0",
        """Привет!

Это тестовая шпаргалка.

Закон Ома:

U = I × R

P = U × I

Arduino UNO"""
    )


# ==========================================
# ОКНО
# ==========================================

root = tk.Tk()

root.title("Arduino Mini Cheat Sheet")

root.geometry("700x600")


# Заголовок

tk.Label(
    root,
    text="Arduino Mini Cheat Sheet",
    font=("Arial", 20, "bold")
).pack(pady=15)


# COM

frame = tk.Frame(root)

frame.pack(pady=5)


tk.Label(
    frame,
    text="COM-порт:"
).pack(side="left")


port_box = ttk.Combobox(
    frame,
    width=15,
    state="readonly"
)

port_box.pack(
    side="left",
    padx=10
)


tk.Button(
    frame,
    text="Обновить",
    command=refresh_ports
).pack(side="left")


# Текст

tk.Label(
    root,
    text="Текст шпаргалки:",
    font=("Arial", 12, "bold")
).pack(
    anchor="w",
    padx=20,
    pady=(20, 5)
)


text_box = tk.Text(
    root,
    font=("Arial", 13),
    wrap="word"
)

text_box.pack(
    fill="both",
    expand=True,
    padx=20
)


# Кнопки

buttons = tk.Frame(root)

buttons.pack(pady=15)


tk.Button(
    buttons,
    text="Тестовый текст",
    width=20,
    height=2,
    command=test_text
).pack(
    side="left",
    padx=10
)


tk.Button(
    buttons,
    text="ЗАПИСАТЬ В ARDUINO",
    width=25,
    height=2,
    command=send_text
).pack(
    side="left",
    padx=10
)


# Статус

status = tk.Label(
    root,
    text="Готово",
    font=("Arial", 11)
)

status.pack(pady=5)


refresh_ports()

root.mainloop()