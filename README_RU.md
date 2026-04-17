# SmartMonitor HID Edition

Это модифицированный форк `turing-smart-screen-python` с поддержкой 3.5" SmartMonitor, который в Linux определяется как USB HID (`0483:0065`), а не как обычный serial/TTY-дисплей.

## Что умеет проект

- работать с монитором через `hidraw`
- загружать темы в монитор по HID/YMODEM
- передавать live-метрики CPU, GPU, RAM, disk и network
- работать с vendor-темами `.dat`
- конвертировать vendor `UI -> DAT`
- управлять темами через `configure.py`
- редактировать SmartMonitor UI через отдельный редактор с canvas-preview `480x320`

## Основные файлы

- `main.py` — основной запуск проекта
- `configure.py` — GUI-конфигуратор, выбор тем, импорт и конвертация
- `smartmonitor-theme-editor.py` — редактор SmartMonitor UI
- `tools/smartmonitor-theme-manager.py` — CLI-менеджер тем

## Рекомендуемая стартовая тема

Для самого стабильного старта:

- `res/themes/rog03-vendor.dat`

## Быстрый старт

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 configure.py
```

Дальше:

1. выбрать `SmartMonitor HID (experimental)`
2. выбрать тему
3. нажать `Save and run`

## Что изменено относительно оригинала

В форк добавлено:

- HID backend для SmartMonitor
- runtime для live-метрик без framebuffer
- загрузка тем `img.dat`
- конвертация `vendor .ui -> .dat`
- интеграция SmartMonitor в GUI
- отдельный редактор SmartMonitor UI

## Лицензия

Оригинальный проект распространяется под `GNU GPL v3`.

Это означает, что проект можно изменять и публиковать как форк, но:

- лицензию GPL-3.0 нужно сохранить
- notices об авторских правах удалять нельзя
- модифицированная версия должна быть явно помечена как изменённая
- исходный код модификаций при распространении тоже должен оставаться доступным по GPL

См. [LICENSE](./LICENSE).
