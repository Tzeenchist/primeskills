#!/usr/bin/env python3
"""Рамка навыка screen без браузера (PS-088, S4).

Рамка — это и есть навык: три экрана, три минуты, двадцать пять строк. Её
нельзя проверять живым прогоном, потому что живой прогон требует поднятого
приложения, а гейт набора его не поднимает. Поэтому здесь прогонщик подменён
поддельным: обёртка получает готовые строки NDJSON и обязана вести себя с
ними ровно так, как обещает навык.

Отдельная проверка — сироты: таймаут обязан убивать группу процессов, иначе
chromium переживёт обёртку (G7). Поддельный прогонщик пишет свой pid в файл,
а тест после таймаута спрашивает систему, жив ли он.
"""
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WRAPPER = ROOT / "skills" / "screen" / "bin" / "screen.py"


def run(args, runner=None, timeout=60):
    env = dict(os.environ)
    if runner:
        env["SCREEN_RUNNER"] = str(runner)
    return subprocess.run([sys.executable, str(WRAPPER)] + args,
                          capture_output=True, text=True, env=env, timeout=timeout)


def fake_runner(body, path):
    """Поддельный прогонщик: node не нужен, нужен только stdout нужной формы."""
    path.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
    path.chmod(0o755)
    return path


def screen_line(name, checks, status="ok"):
    return json.dumps({"screen": {"name": name, "url": f"http://x/{name}",
                                  "url_final": f"http://x/{name}",
                                  "status": status, "checks": checks}},
                      ensure_ascii=False)


def main():
    failures = []
    tmp = Path(tempfile.mkdtemp(prefix="screen-frame-"))

    # 1. Адрес обязателен: без экрана браузер не поднимается вовсе.
    out = run([])
    if out.returncode == 0 or "адрес" not in (out.stdout + out.stderr):
        failures.append(f"без адреса: ожидался отказ про адрес, получено {out.returncode} {out.stdout[:80]}")

    # 2. Якорь обязателен: без него «чисто» может относиться к чужой странице.
    out = run(["--screen", "http://x/a"])
    if out.returncode == 0 or "якор" not in (out.stdout + out.stderr):
        failures.append(f"без якоря: ожидался отказ про якорь, получено {out.returncode} {out.stdout[:80]}")

    # 3. Четвёртый экран отвергается ДО запуска прогонщика.
    args = []
    for i in range(4):
        args += ["--screen", f"http://x/{i}", "#app"]
    out = run(args, runner=tmp / "never")
    if out.returncode == 0 or "трёх" not in (out.stdout + out.stderr):
        failures.append(f"четвёртый экран: ожидался отказ, получено {out.returncode} {out.stdout[:80]}")

    # 4. Обрезка: сорок находок ужимаются до 25 строк, срез назван числом.
    many = [{"id": f"c{i}", "verdict": "НАШЛА", "detail": f"находка {i}"} for i in range(40)]
    body = ("import sys\nprint(%r)\n" % screen_line("много", many))
    out = run(["--screen", "http://x/m", "#app"], runner=fake_runner(body, tmp / "many.py"))
    lines = [l for l in out.stdout.splitlines() if l.strip()]
    if len(lines) > 25:
        failures.append(f"обрезка: {len(lines)} строк вместо 25")
    if "срезано" not in out.stdout:
        failures.append("обрезка: в отчёте не сказано, сколько срезано")

    # 5. Порядок: НАШЛА выше НЕ ИЗМЕРЕНО, ПРОШЛА свёрнута в счётчик.
    mixed = [
        {"id": "console", "verdict": "ПРОШЛА", "detail": ""},
        {"id": "focus", "verdict": "НЕ ИЗМЕРЕНО", "detail": "узла нет"},
        {"id": "overlap", "verdict": "НАШЛА", "detail": "перекрытие"},
        {"id": "viewport", "verdict": "ПРОШЛА", "detail": ""},
    ]
    body = ("import sys\nprint(%r)\n" % screen_line("смесь", mixed))
    out = run(["--screen", "http://x/s", "#app"], runner=fake_runner(body, tmp / "mixed.py"))
    text = out.stdout
    if not (text.find("НАШЛА") < text.find("НЕ ИЗМЕРЕНО")):
        failures.append("порядок: НЕ ИЗМЕРЕНО встало выше НАШЛА")
    if "ПРОШЛА: 2" not in text:
        failures.append(f"порядок: прошедшие не свёрнуты в счётчик — {text[:120]}")

    # 6. Таймаут: частичное сохраняется, а группа процессов умирает целиком.
    pidfile = tmp / "pid"
    body = (f"import os, sys, time\n"
            f"open({str(pidfile)!r}, 'w').write(str(os.getpid()))\n"
            f"print({screen_line('первый', [{'id': 'overlap', 'verdict': 'НАШЛА', 'detail': 'есть'}])!r}, flush=True)\n"
            f"time.sleep(120)\n")
    out = run(["--screen", "http://x/t", "#app", "--timeout", "3"],
              runner=fake_runner(body, tmp / "hang.py"), timeout=60)
    if "первый" not in out.stdout:
        failures.append(f"таймаут: частичный результат потерян — {out.stdout[:120]}")
    if "не уложил" not in out.stdout and "таймаут" not in out.stdout.lower():
        failures.append("таймаут: отчёт не говорит, что прогон не уложился")
    time.sleep(0.5)
    if pidfile.exists():
        pid = int(pidfile.read_text())
        alive = True
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            alive = False
        except PermissionError:
            alive = True
        if alive:
            failures.append(f"таймаут: процесс {pid} пережил обёртку — группа не убита")
    else:
        failures.append("таймаут: поддельный прогонщик не записал pid, проверка сирот не состоялась")

    for line in failures:
        print(line)
    print(f"6 checks, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
