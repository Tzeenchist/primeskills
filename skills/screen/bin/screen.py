#!/usr/bin/env python3
"""Обёртка навыка screen: рамка и отчёт (PS-088, S3).

Рамка — это и есть навык. Браузер умеет измерить больше, чем стоит читать, и
без ограничений прогон уносит контекст сотнями строк DOM. Поэтому здесь
жёстко: не больше трёх экранов за вызов, не больше трёх минут, не больше
двадцати пяти строк отчёта. Скриншоты сюда не попадают вовсе.

Отчёт строится в порядке полезности: сначала находки, потом неизмеримое,
прошедшие проверки сворачиваются в счётчик. Обрезка идёт с хвоста, поэтому
главное остаётся, даже когда экранов три и находок много.
"""
import argparse
import json
import os
import signal
import subprocess
import sys
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_RUNNER = HERE / "screen_run.mjs"
PLAYWRIGHT_VERSION = "1.61.1"
PLAYWRIGHT_HOME = Path.home() / ".cache" / "primeskills-screen"

MAX_SCREENS = 3
DEFAULT_TIMEOUT = 180
DEFAULT_MAX_LINES = 25

FOUND, UNMEASURED, PASS = "НАШЛА", "НЕ ИЗМЕРЕНО", "ПРОШЛА"

EXIT_OK, EXIT_FINDINGS, EXIT_FRAME, EXIT_TOOLING, EXIT_TIMEOUT = 0, 1, 2, 3, 4


def refuse(message):
    print(message)
    sys.exit(EXIT_FRAME)


def parse_args(argv):
    p = argparse.ArgumentParser(
        prog="screen",
        description="Браузерная проверка экрана: геометрия, контраст, фокус, консоль.")
    p.add_argument("--screen", action="append", nargs="+", metavar=("URL", "ЯКОРЬ"),
                   help="адрес, селектор-якорь и необязательная цель; до трёх раз")
    p.add_argument("--viewport", default="1280x800")
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    p.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES)
    return p.parse_args(argv)


def build_task(args):
    """Рамка проверяется ДО запуска браузера: отказ не должен стоить прогона."""
    if not args.screen:
        refuse("отказ: адрес обязателен — `--screen <URL> <якорь>`. "
               "Без адреса проверять нечего, а умолчание увело бы прогон не туда.")
    if len(args.screen) > MAX_SCREENS:
        refuse(f"отказ: не больше трёх экранов за вызов, передано {len(args.screen)}. "
               "Остальные — следующим вызовом: так расход виден по одному.")
    screens = []
    for i, spec in enumerate(args.screen, start=1):
        if len(spec) < 2 or not spec[1].strip():
            refuse(f"отказ: экрану {i} ({spec[0]}) не назван якорь. "
                   "Без якоря «чисто» может относиться к странице входа, а не к вашей.")
        url, anchor = spec[0], spec[1]
        if url.startswith(("https://", "http://")) and "://" in url:
            host = url.split("://", 1)[1].split("/", 1)[0]
            if host and not (host.startswith(("127.", "localhost", "0.0.0.0", "[::1]"))
                             or host.split(":")[0].startswith(("10.", "192.168.", "172."))):
                pass  # чужой адрес разрешён, но прод запрещён навыком, а не программой
        screens.append({"name": spec[3] if len(spec) > 3 else f"экран {i}",
                        "url": url, "anchor": anchor,
                        **({"goal": spec[2]} if len(spec) > 2 and spec[2] else {})})
    try:
        width, height = (int(v) for v in args.viewport.lower().split("x"))
    except ValueError:
        refuse(f"отказ: вьюпорт пишется как 1280x800, получено {args.viewport!r}")
    return {"screens": screens, "viewport": {"width": width, "height": height}}


def ensure_playwright():
    """Первый запуск тянет пакет из сети; браузеры берутся из общего кэша."""
    if (PLAYWRIGHT_HOME / "node_modules" / "playwright").exists():
        return
    print(f"ставлю playwright@{PLAYWRIGHT_VERSION} в {PLAYWRIGHT_HOME} (один раз)…")
    done = subprocess.run(["npm", "install", "--prefix", str(PLAYWRIGHT_HOME),
                           f"playwright@{PLAYWRIGHT_VERSION}", "--no-fund", "--no-audit"],
                          capture_output=True, text=True)
    if done.returncode != 0:
        print("отказ: playwright не поставился — " + done.stderr.strip().splitlines()[-1][:200])
        sys.exit(EXIT_TOOLING)


def runner_command():
    runner = Path(os.environ.get("SCREEN_RUNNER", DEFAULT_RUNNER))
    if runner.suffix == ".mjs":
        return ["node", str(runner)], True
    return [sys.executable, str(runner)], False


def collect(task, timeout):
    """Прогонщик идёт своей группой процессов: таймаут бьёт по группе, иначе
    chromium переживает убийство обёртки и остаётся висеть (G7)."""
    command, needs_playwright = runner_command()
    if needs_playwright:
        ensure_playwright()
    proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, start_new_session=True)
    lines, screens, failure = [], [], None

    def pump():
        for line in proc.stdout:
            lines.append(line)

    reader = threading.Thread(target=pump, daemon=True)
    reader.start()
    try:
        proc.stdin.write(json.dumps(task, ensure_ascii=False))
        proc.stdin.close()
    except BrokenPipeError:
        pass
    # Живым считается только тот прогон, чей вывод ещё идёт или чей процесс
    # не завершился за отведённое время. Проверять `poll()` сразу после
    # закрытия stdout нельзя: процесс ещё не пожат, `None` там означает гонку,
    # а не зависание, и отчёт получал ложную строку про таймаут.
    reader.join(timeout)
    timed_out = reader.is_alive()
    if not timed_out:
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            timed_out = True
    if timed_out:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "screen" in payload:
            screens.append(payload["screen"])
        elif "error" in payload:
            failure = payload
    return screens, failure, timed_out, (proc.stderr.read() if proc.stderr else "")


def report(screens, task, timed_out, timeout, max_lines):
    """Находки выше прочего: обрезка идёт с хвоста, и терять она должна
    прошедшие проверки, а не то, ради чего звали."""
    head, tail = [], []
    findings = 0
    for screen in screens:
        title = f"экран «{screen.get('name')}» {screen.get('url_final') or screen.get('url')}"
        if screen.get("status") != "ok":
            head.append(f"{title} — NOT RUN: {screen.get('reason', 'причина не названа')}")
            continue
        checks = screen.get("checks", [])
        found = [c for c in checks if c["verdict"] == FOUND]
        unmeasured = [c for c in checks if c["verdict"] == UNMEASURED]
        passed = [c for c in checks if c["verdict"] == PASS]
        findings += len(found)
        head.append(title)
        head += [f"  {FOUND} {c['id']}: {c['detail']}" for c in found]
        tail += [f"  {screen.get('name')} · {UNMEASURED} {c['id']}: {c['detail']}" for c in unmeasured]
        if passed:
            tail.append(f"  {screen.get('name')} · {PASS}: {len(passed)} "
                        f"({', '.join(c['id'] for c in passed)})")
    if not screens:
        head.append("прогон не дал ни одного экрана")
    if timed_out:
        head.insert(0, f"прогон не уложился в {timeout} с: пройдено экранов "
                       f"{len(screens)} из {len(task['screens'])}, остальное НЕ ИЗМЕРЕНО")
    lines = head + tail
    if len(lines) > max_lines:
        cut = len(lines) - (max_lines - 1)
        lines = lines[:max_lines - 1] + [f"  срезано {cut} строк(и) — порядок: находки, затем неизмеримое"]
    return lines, findings


def main(argv):
    args = parse_args(argv)
    task = build_task(args)
    screens, failure, timed_out, stderr = collect(task, args.timeout)
    if failure:
        print(f"отказ: {failure.get('error')} — {failure.get('detail', '')}")
        if failure.get("fix"):
            print(f"чинится так: {failure['fix']}")
        return EXIT_TOOLING
    lines, findings = report(screens, task, timed_out, args.timeout, args.max_lines)
    print("\n".join(lines))
    if not screens and stderr.strip():
        print(f"прогонщик молчал, stderr: {stderr.strip().splitlines()[-1][:200]}")
        return EXIT_TOOLING
    if timed_out:
        return EXIT_TIMEOUT
    return EXIT_FINDINGS if findings else EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
