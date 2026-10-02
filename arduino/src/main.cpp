#include <Arduino.h>
#include <Wire.h>
#include <EEPROM.h>
#include <U8g2lib.h>

// ===============================
// НАСТРОЙКИ
// ===============================

#define BTN_UP      3
#define BTN_DOWN    4
#define BTN_SCREEN  5

#define EEPROM_LENGTH_ADDR 0
#define EEPROM_TEXT_ADDR   2

// Arduino UNO имеет 1024 байта EEPROM.
// Оставляем 2 байта под длину.
#define MAX_TEXT_SIZE 1000

#define LINES_ON_SCREEN 6

// SSD1306 128x64 I2C
// _1_ = page buffer, экономит RAM Arduino UNO
U8G2_SSD1306_128X64_NONAME_1_HW_I2C u8g2(
    U8G2_R0,
    U8X8_PIN_NONE
);

// ===============================
// ПЕРЕМЕННЫЕ
// ===============================

uint16_t textLength = 0;

int firstLine = 0;

bool screenOn = true;

bool lastUpState = HIGH;
bool lastDownState = HIGH;
bool lastScreenState = HIGH;

unsigned long lastButtonTime = 0;

const unsigned long debounceTime = 180;


// ===============================
// ЧТЕНИЕ ДЛИНЫ ТЕКСТА
// ===============================

void loadTextInfo()
{
    EEPROM.get(EEPROM_LENGTH_ADDR, textLength);

    if (textLength > MAX_TEXT_SIZE)
    {
        textLength = 0;
    }
}


// ===============================
// КОЛИЧЕСТВО СТРОК
// ===============================

int getTotalLines()
{
    if (textLength == 0)
    {
        return 0;
    }

    int lines = 1;

    for (uint16_t i = 0; i < textLength; i++)
    {
        char c = EEPROM.read(EEPROM_TEXT_ADDR + i);

        if (c == '\n')
        {
            lines++;
        }
    }

    return lines;
}


// ===============================
// НАЙТИ НАЧАЛО НУЖНОЙ СТРОКИ
// ===============================

uint16_t findLineStart(int wantedLine)
{
    if (wantedLine <= 0)
    {
        return 0;
    }

    int currentLine = 0;

    for (uint16_t i = 0; i < textLength; i++)
    {
        char c = EEPROM.read(EEPROM_TEXT_ADDR + i);

        if (c == '\n')
        {
            currentLine++;

            if (currentLine == wantedLine)
            {
                return i + 1;
            }
        }
    }

    return textLength;
}


// ===============================
// ПЕЧАТЬ ОДНОЙ СТРОКИ
// ===============================

uint16_t printLine(uint16_t position, int y)
{
    char line[64];
    int index = 0;

    while (position < textLength && index < 63)
    {
        char c = EEPROM.read(EEPROM_TEXT_ADDR + position);

        position++;

        if (c == '\n')
        {
            break;
        }

        if (c == '\r')
        {
            continue;
        }

        line[index++] = c;
    }

    line[index] = '\0';

    u8g2.setCursor(0, y);
    u8g2.print(line);

    return position;
}


// ===============================
// ОТРИСОВКА ЭКРАНА
// ===============================

void drawScreen()
{
    if (!screenOn)
    {
        return;
    }

    int totalLines = getTotalLines();

    u8g2.firstPage();

    do
    {
        u8g2.setFont(u8g2_font_6x13_t_cyrillic);

        if (textLength == 0)
        {
            u8g2.setCursor(0, 25);
            u8g2.print("Нет текста.");

            u8g2.setCursor(0, 42);
            u8g2.print("Передайте текст");
        }
        else
        {
            uint16_t position = findLineStart(firstLine);

            for (int i = 0; i < LINES_ON_SCREEN; i++)
            {
                if (position >= textLength)
                {
                    break;
                }

                position = printLine(
                    position,
                    10 + i * 10
                );
            }
        }

    } while (u8g2.nextPage());
}


// ===============================
// СОХРАНЕНИЕ ТЕКСТА
// ===============================

void saveText(uint16_t length)
{
    if (length > MAX_TEXT_SIZE)
    {
        Serial.println("ERROR: TEXT TOO LONG");
        return;
    }

    // Записываем длину
    EEPROM.put(EEPROM_LENGTH_ADDR, length);

    // Получаем данные уже после заголовка
    for (uint16_t i = 0; i < length; i++)
    {
        while (!Serial.available())
        {
            // ждём следующий байт
        }

        byte b = Serial.read();

        EEPROM.update(
            EEPROM_TEXT_ADDR + i,
            b
        );
    }

    textLength = length;

    firstLine = 0;

    Serial.println("OK: TEXT SAVED");

    drawScreen();
}


// ===============================
// ПОЛУЧЕНИЕ ТЕКСТА ПО USB
// ===============================

void serialReceive()
{
    if (!Serial.available())
        return;

    String command = Serial.readStringUntil('\n');
    command.trim();

    if (!command.startsWith("TEXT:"))
        return;

    int receivedLength = command.substring(5).toInt();

    if (receivedLength <= 0 || receivedLength > MAX_TEXT_SIZE)
    {
        Serial.println("ERROR:LENGTH");
        return;
    }

    Serial.print("READY:");
    Serial.println(receivedLength);

    uint16_t received = 0;
    unsigned long lastData = millis();

    while (received < receivedLength)
    {
        if (Serial.available())
        {
            byte b = Serial.read();

            EEPROM.update(
                EEPROM_TEXT_ADDR + received,
                b
            );

            received++;
            lastData = millis();
        }

        // Если данные перестали приходить
        if (millis() - lastData > 5000)
        {
            Serial.println("ERROR:TIMEOUT");
            return;
        }
    }

    textLength = received;

    EEPROM.put(
        EEPROM_LENGTH_ADDR,
        textLength
    );

    firstLine = 0;

    Serial.println("OK:SAVED");

    drawScreen();
}


// ===============================
// КНОПКИ
// ===============================

void checkButtons()
{
    bool upState = digitalRead(BTN_UP);
    bool downState = digitalRead(BTN_DOWN);
    bool screenState = digitalRead(BTN_SCREEN);

    unsigned long now = millis();

    if (now - lastButtonTime > debounceTime)
    {
        // -----------------------
        // КНОПКА ВВЕРХ
        // -----------------------

        if (lastUpState == HIGH && upState == LOW)
        {
            if (firstLine > 0)
            {
                firstLine--;
                drawScreen();
            }

            lastButtonTime = now;
        }


        // -----------------------
        // КНОПКА ВНИЗ
        // -----------------------

        if (lastDownState == HIGH && downState == LOW)
        {
            int totalLines = getTotalLines();

            int maxFirstLine =
                totalLines - LINES_ON_SCREEN;

            if (maxFirstLine < 0)
            {
                maxFirstLine = 0;
            }

            if (firstLine < maxFirstLine)
            {
                firstLine++;
                drawScreen();
            }

            lastButtonTime = now;
        }


        // -----------------------
        // ЭКРАН ВКЛ/ВЫКЛ
        // -----------------------

        if (lastScreenState == HIGH && screenState == LOW)
        {
            screenOn = !screenOn;

            if (screenOn)
            {
                u8g2.setPowerSave(0);
                drawScreen();
            }
            else
            {
                u8g2.setPowerSave(1);
            }

            lastButtonTime = now;
        }
    }

    lastUpState = upState;
    lastDownState = downState;
    lastScreenState = screenState;
}


// ===============================
// SETUP
// ===============================

void setup()
{
    Serial.begin(115200);

    // Кнопки подключены к GND
    pinMode(BTN_UP, INPUT_PULLUP);
    pinMode(BTN_DOWN, INPUT_PULLUP);
    pinMode(BTN_SCREEN, INPUT_PULLUP);

    u8g2.begin();

    // Разрешаем UTF-8
    u8g2.enableUTF8Print();

    loadTextInfo();

    Serial.println();
    Serial.println("CHEAT SHEET READY");
    Serial.print("Stored bytes: ");
    Serial.println(textLength);

    drawScreen();
}


// ===============================
// LOOP
// ===============================

void loop()
{
    checkButtons();
    serialReceive();
}