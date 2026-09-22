#!/usr/bin/env python3
"""Живой прогон screen по стенду (PS-088, S5).

Браузер здесь настоящий, страница — `tests/fixtures/screen/page.html` по
`file://`: гейту не нужен поднятый сервер, а пять дефектов стенда заранее
известны. Тест различает два отказа браузера разными текстами — «браузера
нет вовсе» и «ревизион не тот»: в calcuta пустой `~/.cache/ms-playwright`
уже красил гейт, и сообщение про отсутствие файла читалось как поломка кода.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "skills" / "screen" / "bin" / "screen_run.mjs"
FIXTURES = ROOT / "tests" / "fixtures" / "screen"
CACHE = Path.home() / ".cache" / "ms-playwright"

EXPECTED = {"overlap", "viewport", "contrast", "focus", "console"}


def browser_missing():
    """Пусто или нет каталога — браузера нет. Что ревизион не тот, скажет сам
    прогон: его текст отличается от «нет кэша» и должен доехать до отчёта."""
    return not CACHE.exists() or not any(CACHE.glob("chromium-*"))


def run(task):
    proc = subprocess.run(["node", str(RUNNER)], input=json.dumps(task),
                          capture_output=True, text=True, timeout=180)
    return proc


def main():
    if browser_missing():
        print(f"skipped: браузера нет в {CACHE} — установить "
              f"`npx -y playwright@1.61.1 install chromium`")
        return 0
    failures = []

    page = run({"screens": [{"name": "стенд",
                             "url": (FIXTURES / "page.html").as_uri(),
                             "anchor": "#app"}]})
    if page.returncode != 0:
        print(f"прогонщик упал: {page.stderr.strip()[:400]}")
        return 1
    result = json.loads(page.stdout)
    screen = result["screens"][0]
    if screen["status"] != "ok":
        failures.append(f"стенд не открылся: {screen}")
    found = {c["id"] for c in screen.get("checks", []) if c["verdict"] == "НАШЛА"}
    if found != EXPECTED:
        failures.append(f"стенд: ожидались находки {sorted(EXPECTED)}, "
                        f"получены {sorted(found)}")

    login = run({"screens": [{"name": "вход",
                              "url": (FIXTURES / "login.html").as_uri(),
                              "anchor": "#app"}]})
    if login.returncode != 0:
        failures.append(f"страница входа уронила прогонщик: {login.stderr[:200]}")
    else:
        got = json.loads(login.stdout)["screens"][0]
        if got["status"] != "not_run":
            failures.append(f"вход: ожидался not_run, получено {got['status']}")
        if "url_final" not in got:
            failures.append("вход: в ответе нет фактического URL")

    for line in failures:
        print(line)
    print(f"2 checks, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
