# Vinogradov's Digitizer — сборка Windows

Версия приложения: **2.3.0**

Финальная Windows-версия Vinogradov's Digitizer является обычным
настольным приложением.

Конечному пользователю НЕ требуются:

- Python;
- Docker;
- OpenCV;
- PySide6;
- pandas;
- Inno Setup;
- какие-либо дополнительные среды разработки.

Пользователь скачивает готовый установщик:

```text
Vinogradovs_Digitizer_Setup_2.3.0.exe
```

после установки получает ярлык:

```text
Vinogradov's Digitizer
```

и запускает программу обычным двойным щелчком.


---

# 1. Структура Windows-релиза

Основные файлы сборки:

```text
VinogradovsDigitizer.spec

requirements.txt
requirements-build.txt
pyproject.toml

build_windows_exe.bat
build_windows_installer.bat
build_windows_release.bat

windows/
└── version_info.txt

installer/
└── VinogradovsDigitizer.iss

.github/
└── workflows/
    └── build-windows.yml
```

Ресурсы:

```text
assets/
├── app_icon.png
├── VinogradovsDigitizer.ico
└── vinogradovs_digitizer_logo.png
```


---

# 2. Названия продукта

Отображаемое название:

```text
Vinogradov's Digitizer
```

Техническое имя EXE:

```text
VinogradovsDigitizer.exe
```

Установщик:

```text
Vinogradovs_Digitizer_Setup_2.3.0.exe
```

Portable-версия:

```text
Vinogradovs_Digitizer_Portable_2.3.0.zip
```

Версия:

```text
2.3.0
```

Windows file version:

```text
2.3.0.0
```

Windows Application ID:

```text
Vinogradov.VinogradovsDigitizer
```


---

# 3. Что нужно только для ручной сборки

Если приложение собирается вручную на Windows-компьютере,
на машине разработчика нужны:

- Windows 10 или Windows 11 x64;
- Python 3.12 x64;
- Inno Setup 6;
- доступ в интернет для первой установки Python-зависимостей.

Рекомендуемая версия Python:

```text
Python 3.12 x64
```

Python нужен ТОЛЬКО разработчику для сборки.

Конечному пользователю Python не нужен.


---

# 4. Автоматические тесты

Перед созданием EXE обязательно должны пройти тесты:

```bat
python -m pytest tests -q
```

Основные тесты:

```text
tests/test_processing.py
tests/test_ui_smoke.py
tests/test_windows_package.py
```

Если хотя бы один тест завершается ошибкой,
релиз публиковать нельзя.


---

# 5. Сборка EXE вручную

В корне проекта запустить:

```text
build_windows_exe.bat
```

Скрипт:

1. найдёт Python;
2. создаст отдельное окружение `.venv-build`;
3. установит зависимости;
4. запустит тесты;
5. очистит старые `build` и `dist`;
6. запустит PyInstaller;
7. проверит наличие EXE.

Готовое приложение появится здесь:

```text
dist\
└── VinogradovsDigitizer\
    ├── VinogradovsDigitizer.exe
    └── _internal\
```

Используется режим PyInstaller **one-dir**.

Это сделано намеренно.

Для PySide6, OpenCV, pandas и NumPy такой вариант:

- надёжнее;
- быстрее запускается;
- проще диагностируется;
- хорошо упаковывается Inno Setup.

Конечный пользователь всё равно получает один установщик EXE.


---

# 6. Проверка EXE до создания установщика

После сборки желательно сначала запустить:

```text
dist\VinogradovsDigitizer\VinogradovsDigitizer.exe
```

Проверить:

1. появляется заставка с гербом;
2. отображается название `Vinogradov's Digitizer`;
3. главное окно открывается развёрнутым;
4. не появляется окно CMD;
5. кнопка `Открыть фото` вызывает обычный Проводник Windows;
6. можно открыть PNG/JPG/JPEG/BMP;
7. работают H1/H2;
8. работают шкалы;
9. работают кривые;
10. работает экспорт XLSX;
11. работает сохранение проекта;
12. работает повторное открытие проекта;
13. после закрытия главного окна процесс приложения завершается.


---

# 7. Сборка установщика вручную

После успешной проверки EXE запустить:

```text
build_windows_installer.bat
```

Скрипт использует:

```text
installer\VinogradovsDigitizer.iss
```

и Inno Setup 6.

Результат:

```text
release\
└── Vinogradovs_Digitizer_Setup_2.3.0.exe
```

Установщик:

- устанавливает программу для текущего пользователя;
- не требует прав администратора;
- создаёт запись в меню Пуск;
- предлагает создать ярлык на рабочем столе;
- использует герб Vinogradov's Digitizer;
- позволяет сразу запустить программу после установки.


---

# 8. Полная ручная сборка релиза

Для полной сборки можно использовать:

```text
build_windows_release.bat
```

В результате должны появиться:

```text
release\
├── Vinogradovs_Digitizer_Setup_2.3.0.exe
├── Vinogradovs_Digitizer_Portable_2.3.0.zip
└── SHA256SUMS.txt
```

Основной файл для обычных пользователей:

```text
Vinogradovs_Digitizer_Setup_2.3.0.exe
```

Portable ZIP является дополнительным вариантом.


---

# 9. GitHub Actions

Рекомендуемый способ создания Windows-релиза —
собирать программу на GitHub Actions.

Workflow:

```text
.github/workflows/build-windows.yml
```

GitHub использует настоящий Windows runner:

```text
windows-latest
```

и Python:

```text
Python 3.12 x64
```


---

# 10. Первая тестовая сборка через GitHub

После загрузки проекта в GitHub:

```text
GitHub
→ Actions
→ Build Windows release
→ Run workflow
```

При ручном запуске workflow официальный Release НЕ публикуется.

GitHub только создаёт Artifact:

```text
Vinogradovs-Digitizer-Windows-2.3.0
```

Внутри должны находиться:

```text
Vinogradovs_Digitizer_Setup_2.3.0.exe
Vinogradovs_Digitizer_Portable_2.3.0.zip
SHA256SUMS.txt
```

Этот Artifact нужно скачать и проверить на настоящем Windows-компьютере.


---

# 11. Что проверить на чистом Windows

Желательно тестировать на компьютере, где НЕ установлены:

- Python;
- Docker;
- PySide6;
- OpenCV;
- Visual Studio;
- среда разработки проекта.

Проверить установщик:

```text
Vinogradovs_Digitizer_Setup_2.3.0.exe
```

После установки проверить:

1. в меню Пуск есть `Vinogradov's Digitizer`;
2. на рабочем столе есть ярлык, если он был выбран;
3. ярлык имеет правильный герб;
4. двойной щелчок запускает приложение;
5. не появляется CMD;
6. показывается splash screen;
7. открывается главное окно;
8. правая панель имеет фиксированную ширину;
9. открытие файлов работает через Проводник Windows;
10. поддерживаются пути с кириллицей;
11. XLSX можно сохранить в любую папку;
12. проект можно сохранить и открыть;
13. программа полностью закрывается по крестику;
14. приложение работает без установленного Python.


---

# 12. Публикация GitHub Release

Официальный Release создаётся только после успешного тестирования.

В корне Git-репозитория:

```bash
git tag v2.3.0
git push origin v2.3.0
```

Push тега:

```text
v2.3.0
```

автоматически запускает Windows workflow.

После успешной сборки GitHub создаёт:

```text
Releases
└── Vinogradov's Digitizer 2.3.0
```

с файлами:

```text
Vinogradovs_Digitizer_Setup_2.3.0.exe
Vinogradovs_Digitizer_Portable_2.3.0.zip
SHA256SUMS.txt
```


---

# 13. Что давать обычному пользователю

Для обычного пользователя рекомендуется только:

```text
Vinogradovs_Digitizer_Setup_2.3.0.exe
```

Последовательность:

```text
Скачать
    ↓
Запустить установщик
    ↓
Установить
    ↓
Ярлык Vinogradov's Digitizer
    ↓
Двойной щелчок
    ↓
Работа
    ↓
Закрыть окно программы
```


---

# 14. Portable-версия

Файл:

```text
Vinogradovs_Digitizer_Portable_2.3.0.zip
```

предназначен для случаев, когда пользователь не хочет устанавливать программу.

Нужно:

1. распаковать ZIP;
2. открыть папку;
3. запустить:

```text
VinogradovsDigitizer.exe
```

Удалять `_internal` нельзя.

Все файлы portable-сборки должны оставаться вместе.


---

# 15. SHA-256

Файл:

```text
SHA256SUMS.txt
```

содержит контрольные суммы релизных файлов.

На Windows контрольную сумму можно проверить командой:

```powershell
Get-FileHash `
    Vinogradovs_Digitizer_Setup_2.3.0.exe `
    -Algorithm SHA256
```

Полученный SHA-256 должен совпадать со значением из:

```text
SHA256SUMS.txt
```


---

# 16. Windows SmartScreen

На текущем этапе приложение может быть выпущено без цифровой подписи.

В таком случае Microsoft SmartScreen на некоторых компьютерах
может показать предупреждение о неизвестном издателе.

Это НЕ означает, что приложению требуется Python или Docker.

Причина — отсутствие коммерческого сертификата Code Signing
и репутации у нового EXE-файла.

Для публичного массового распространения рекомендуется позже
добавить цифровую подпись Windows Code Signing.

Система сборки должна быть подготовлена так, чтобы подпись можно
было добавить без изменения основного приложения.


---

# 17. Docker

Docker НЕ является частью Windows-релиза.

Docker используется только для:

- разработки на macOS;
- тестирования;
- запуска текущей Linux/noVNC среды.

Конечному пользователю Windows Docker не нужен.


---

# 18. Обновление версии в будущем

При выпуске новой версии, например:

```text
2.3.1
```

необходимо синхронно изменить версию в:

```text
digitizer/resources.py
pyproject.toml
windows/version_info.txt
installer/VinogradovsDigitizer.iss
.github/workflows/build-windows.yml
```

и при необходимости в документации.

После этого создать новый Git tag:

```bash
git tag v2.3.1
git push origin v2.3.1
```

Windows Application ID:

```text
Vinogradov.VinogradovsDigitizer
```

при обновлении версии НЕ менять.


---

# 19. Итоговая схема

```text
Исходный код
       ↓
pytest
       ↓
PyInstaller
       ↓
VinogradovsDigitizer.exe
       ↓
Inno Setup
       ↓
Vinogradovs_Digitizer_Setup_2.3.0.exe
       ↓
GitHub Release
       ↓
Скачивание пользователем
       ↓
Установка
       ↓
Ярлык Vinogradov's Digitizer
       ↓
Запуск приложения
```

---

Vinogradov's Digitizer  
Version 2.3.0
