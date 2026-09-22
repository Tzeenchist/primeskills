/**
 * Прогонщик экрана для навыка screen (PS-088, S2).
 *
 * Постоянный файл набора: код проверок не генерируется на каждый вызов и в
 * контекст агента не попадает — туда уходит только отчёт обёртки.
 *
 * Вход — JSON на stdin: {"screens":[{"name","url","anchor","goal"?}],
 * "viewport"?:{"width","height"}}. Выход — NDJSON на stdout: по строке
 * {"screen":…} на КАЖДЫЙ пройденный экран, сразу, и {"done":true} в конце.
 * Построчно — чтобы таймаут обёртки не уносил уже измеренное: один общий
 * JSON в конце означал бы, что убитый прогон не оставил ничего.
 * Рамку (сколько экранов, сколько времени, сколько строк) держит обёртка
 * `screen.py`; здесь гоняется ровно то, что передали.
 *
 * У каждой проверки три исхода: ПРОШЛА, НАШЛА, НЕ ИЗМЕРЕНО с причиной.
 * Третий — не вежливость: контраст поверх картинки или градиента не
 * вычисляется, и «прошла» на этом месте было бы враньём.
 */
const PASS = "ПРОШЛА";
const FOUND = "НАШЛА";
const UNMEASURED = "НЕ ИЗМЕРЕНО";

const PLAYWRIGHT_VERSION = "1.61.1";
const ANCHOR_TIMEOUT_MS = 5000;

async function loadPlaywright() {
  const homes = [process.env.SCREEN_PLAYWRIGHT_HOME, `${process.env.HOME}/.cache/primeskills-screen`]
    .filter(Boolean)
    .map(home => `${home}/node_modules/playwright/index.mjs`);
  for (const path of ["playwright", ...homes]) {
    try {
      return await import(path);
    } catch (err) {
      if (!/Cannot find (module|package)|ERR_MODULE_NOT_FOUND/.test(String(err))) throw err;
    }
  }
  const home = process.env.SCREEN_PLAYWRIGHT_HOME || `${process.env.HOME}/.cache/primeskills-screen`;
  throw new Error(
    `playwright не найден. Поставить: npm install --prefix ${home} ` +
    `playwright@${PLAYWRIGHT_VERSION} && npx -y playwright@${PLAYWRIGHT_VERSION} install chromium`);
}

function readStdin() {
  return new Promise((resolve, reject) => {
    let raw = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", chunk => { raw += chunk; });
    process.stdin.on("end", () => resolve(raw));
    process.stdin.on("error", reject);
  });
}

/** Ошибки консоли считаем только со своих скриптов: чужие расширения и
 *  сторонние виджеты шумят, и проверку с таким шумом отключают первой. */
function sameOrigin(pageUrl, sourceUrl) {
  if (!sourceUrl) return true;               // инлайновый скрипт самой страницы
  if (pageUrl.startsWith("file://")) {
    const dir = pageUrl.slice(0, pageUrl.lastIndexOf("/") + 1);
    return sourceUrl.startsWith(dir);
  }
  try {
    return new URL(sourceUrl).origin === new URL(pageUrl).origin;
  } catch {
    return false;
  }
}

/** Проверки живут в странице: DOM в node не передаётся, а пересылать его
 *  наружу значило бы платить за то, чего никто не читает. */
const IN_PAGE = () => {
  const visible = el => {
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden"
      && style.display !== "none" && Number(style.opacity) > 0.05;
  };
  const ownText = el => Array.from(el.childNodes)
    .filter(n => n.nodeType === 3 && n.textContent.trim())
    .map(n => n.textContent.trim()).join(" ");
  const where = el => {
    if (el.id) return `#${el.id}`;
    const cls = (el.className || "").toString().trim().split(/\s+/).filter(Boolean)[0];
    return cls ? `${el.tagName.toLowerCase()}.${cls}` : el.tagName.toLowerCase();
  };
  const textNodes = Array.from(document.querySelectorAll("body *"))
    .filter(el => ownText(el) && visible(el)).slice(0, 400);

  // 1. Перекрытие: два видимых текста лежат друг на друге.
  const overlap = [];
  for (let i = 0; i < textNodes.length; i += 1) {
    for (let j = i + 1; j < textNodes.length; j += 1) {
      const a = textNodes[i], b = textNodes[j];
      if (a.contains(b) || b.contains(a)) continue;
      const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
      const w = Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left);
      const h = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top);
      if (w > 2 && h > 2) overlap.push(`${where(a)} и ${where(b)} перекрыты на ${Math.round(w)}×${Math.round(h)} px`);
    }
  }

  // 2. Выход за правую границу окна.
  const viewport = [];
  const limit = window.innerWidth + 1;
  if (document.documentElement.scrollWidth > limit) {
    for (const el of Array.from(document.querySelectorAll("body *")).slice(0, 600)) {
      if (!visible(el)) continue;
      const rect = el.getBoundingClientRect();
      if (rect.right > limit && rect.width > 0) {
        viewport.push(`${where(el)} выходит за окно на ${Math.round(rect.right - window.innerWidth)} px`);
      }
    }
  }

  // 3. Контраст. Фон-картинка или градиент — НЕ ИЗМЕРЕНО, а не «прошла».
  const parse = value => (value.match(/[\d.]+/g) || []).map(Number);
  const lum = ([r, g, b]) => {
    const f = c => { c /= 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
  };
  const contrast = [], unmeasured = [];
  for (const el of textNodes) {
    const style = getComputedStyle(el);
    let node = el, bg = null, blocked = false;
    while (node) {
      const s = getComputedStyle(node);
      if (s.backgroundImage && s.backgroundImage !== "none") { blocked = true; break; }
      const rgba = parse(s.backgroundColor);
      if (rgba.length >= 3 && (rgba[3] === undefined || rgba[3] >= 0.95)) { bg = rgba; break; }
      node = node.parentElement;
    }
    if (blocked || !bg) {
      unmeasured.push(`${where(el)}: ${blocked ? "фон — изображение или градиент" : "непрозрачного фона не нашлось"}`);
      continue;
    }
    const fg = parse(style.color);
    if (fg.length < 3) { unmeasured.push(`${where(el)}: цвет текста не разобран`); continue; }
    const l1 = lum(fg), l2 = lum(bg);
    const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
    const size = parseFloat(style.fontSize);
    const bold = Number(style.fontWeight) >= 700;
    const need = size >= 24 || (bold && size >= 18.66) ? 3 : 4.5;
    if (ratio < need) {
      contrast.push(`${where(el)}: ${ratio.toFixed(2)}:1 при пороге ${need}`);
    }
  }
  return { overlap, viewport, contrast, contrastUnmeasured: unmeasured };
};

/** Фокус проверяем действием, а не чтением стилей: правило может быть
 *  объявлено и перекрыто, а видно это только после реального фокуса. */
const FOCUS_IN_PAGE = () => {
  const snapshot = el => {
    const s = getComputedStyle(el);
    return [s.outlineStyle, s.outlineWidth, s.outlineColor, s.boxShadow, s.border, s.backgroundColor].join("|");
  };
  const where = el => {
    if (el.id) return `#${el.id}`;
    const cls = (el.className || "").toString().trim().split(/\s+/).filter(Boolean)[0];
    return cls ? `${el.tagName.toLowerCase()}.${cls}` : el.tagName.toLowerCase();
  };
  const selector = "a[href], button, input, select, textarea, [tabindex]:not([tabindex='-1'])";
  const invisible = [];
  for (const el of Array.from(document.querySelectorAll(selector)).slice(0, 60)) {
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) continue;
    const before = snapshot(el);
    el.focus();
    const after = snapshot(el);
    el.blur();
    if (before === after) invisible.push(`${where(el)}: фокус ничего не меняет`);
  }
  return invisible;
};

function verdict(id, findings, unmeasured) {
  if (findings.length) {
    const tail = unmeasured && unmeasured.length ? ` (не измерено: ${unmeasured.length})` : "";
    return { id, verdict: FOUND, detail: findings.slice(0, 5).join("; ") + tail };
  }
  if (unmeasured && unmeasured.length) {
    return { id, verdict: UNMEASURED, detail: unmeasured.slice(0, 3).join("; ") };
  }
  return { id, verdict: PASS, detail: "" };
}

async function runScreen(browser, spec, viewport) {
  const context = await browser.newContext({ viewport });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", msg => {
    if (msg.type() !== "error") return;
    if (sameOrigin(page.url(), msg.location()?.url)) consoleErrors.push(msg.text());
  });
  page.on("pageerror", err => consoleErrors.push(String(err.message || err)));

  const out = { name: spec.name || spec.url, url: spec.url };
  try {
    await page.goto(spec.url, { waitUntil: "load", timeout: 30000 });
  } catch (err) {
    out.status = "not_run";
    out.url_final = page.url();
    out.reason = `страница не открылась: ${String(err.message || err).split("\n")[0]}`;
    await context.close();
    return out;
  }
  out.url_final = page.url();

  if (!spec.anchor) {
    out.status = "not_run";
    out.reason = "якорь экрана не назван: без него «чисто» может относиться к чужой странице";
    await context.close();
    return out;
  }
  try {
    await page.waitForSelector(spec.anchor, { state: "attached", timeout: ANCHOR_TIMEOUT_MS });
  } catch {
    out.status = "not_run";
    out.reason = `якорь ${spec.anchor} не найден — это не тот экран`;
    await context.close();
    return out;
  }

  const measured = await page.evaluate(IN_PAGE);
  const focus = await page.evaluate(FOCUS_IN_PAGE);
  out.status = "ok";
  out.checks = [
    verdict("overlap", measured.overlap),
    verdict("viewport", measured.viewport),
    verdict("contrast", measured.contrast, measured.contrastUnmeasured),
    verdict("focus", focus),
    verdict("console", consoleErrors),
  ];
  if (spec.goal) {
    try {
      const hit = await page.locator(spec.goal).count();
      out.checks.push(hit
        ? { id: "goal", verdict: PASS, detail: `${spec.goal}: найдено ${hit}` }
        : { id: "goal", verdict: FOUND, detail: `${spec.goal}: не найдено` });
    } catch (err) {
      out.checks.push({ id: "goal", verdict: UNMEASURED, detail: String(err.message || err).split("\n")[0] });
    }
  }
  await context.close();
  return out;
}

async function main() {
  const raw = await readStdin();
  let task;
  try {
    task = JSON.parse(raw);
  } catch (err) {
    process.stdout.write(JSON.stringify({ error: "bad_json", detail: String(err.message || err) }) + "\n");
    return 2;
  }
  const screens = Array.isArray(task.screens) ? task.screens : [];
  if (!screens.length) {
    process.stdout.write(JSON.stringify({ error: "no_screens", detail: "в задании нет ни одного экрана" }) + "\n");
    return 2;
  }
  const { chromium } = await loadPlaywright();
  const viewport = task.viewport || { width: 1280, height: 800 };
  let browser;
  try {
    browser = await chromium.launch({ headless: true });
  } catch (err) {
    const detail = String(err.message || err).split("\n")[0];
    process.stdout.write(JSON.stringify({
      error: "browser_unusable",
      detail,
      fix: `npx -y playwright@${PLAYWRIGHT_VERSION} install chromium`,
    }) + "\n");
    return 3;
  }
  try {
    for (const spec of screens) {
      const screen = await runScreen(browser, spec, viewport);
      process.stdout.write(JSON.stringify({ screen }) + "\n");
    }
  } finally {
    await browser.close();
  }
  process.stdout.write(JSON.stringify({ done: true, playwright: PLAYWRIGHT_VERSION, viewport }) + "\n");
  return 0;
}

main().then(code => process.exit(code)).catch(err => {
  process.stderr.write(String(err.stack || err) + "\n");
  process.exit(1);
});
