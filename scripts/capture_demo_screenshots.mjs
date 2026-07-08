import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const playwrightModule = process.env.PLAYWRIGHT_MODULE
  ? await import(pathToFileURL(process.env.PLAYWRIGHT_MODULE).href)
  : await import("playwright");
const { chromium } = playwrightModule;

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const outDir = path.join(repoRoot, "out");
const shotDir = path.join(outDir, "screenshots", "playwright");

const pages = [
  {
    slug: "01-console-home",
    file: "omija_console_home.html",
    title: "평시 콘솔",
    purpose: "사건이 없을 때 감시 범위, quiet proof, provider readiness, Foundry action evidence를 보여준다.",
    features: [
      { name: "steady-state-top", selector: "body", mode: "viewport", scrollY: 0 },
      { name: "coverage-and-quiet-proof", selector: "section", nth: 0 },
      { name: "provider-posture", selector: "section", nth: 1 },
      { name: "decision-audit", selector: "section", nth: 2 },
      { name: "sensitive-access-boundary", selector: "section", nth: 3 },
    ],
  },
  {
    slug: "02-data-coverage-map",
    file: "data_coverage_map.html",
    title: "데이터 커버리지 맵",
    purpose: "무엇을 어디서 관리하고, 어떤 데이터와 엔진 산출로 감시하는지 한 장으로 설명한다.",
    features: [
      { name: "map-top", selector: "body", mode: "viewport", scrollY: 0 },
      { name: "managed-synthetic", selector: "section", nth: 0 },
      { name: "open-public-context", selector: "section", nth: 1 },
      { name: "engine-live-evidence", selector: "section", nth: 2 },
    ],
  },
  {
    slug: "03-data-evidence-brief",
    file: "data_evidence_brief.html",
    title: "데이터 증거",
    purpose: "공개 OSINT, 승인된 StealthMole lineage, synthetic 사건 데이터를 어떻게 분리해 쓰는지 설명한다.",
    features: [
      { name: "evidence-top", selector: "body", mode: "viewport", scrollY: 0 },
      { name: "public-osint-examples", selector: "section", nth: 0 },
      { name: "ontology-use", selector: "section", nth: 1 },
    ],
  },
  {
    slug: "04-data-lineage-live",
    file: "data_lineage_live.html",
    title: "데이터 계보",
    purpose: "승인된 provider row가 redaction boundary, normalized objects, Foundry measurement로 이어지는 흐름을 보여준다.",
    features: [
      { name: "lineage-top", selector: "body", mode: "viewport", scrollY: 0 },
      { name: "run-summary", selector: "section", nth: 0 },
      { name: "swimlane", selector: "section", nth: 1 },
      { name: "record-lineage", selector: "section", nth: 2 },
      { name: "redaction-proof", selector: "section", nth: 3 },
      { name: "foundry-evidence", selector: "section", nth: 4 },
    ],
  },
  {
    slug: "05-foundry-live-measurement",
    file: "foundry_live_measurement.html",
    title: "Foundry Live Measurement",
    purpose: "sanitized provider rows가 Foundry schema-aware datasets에서 측정됐고 SQL count가 맞는지 보여준다.",
    features: [
      { name: "measurement-top", selector: "body", mode: "viewport", scrollY: 0 },
      { name: "module-counts", selector: "section", nth: 0 },
      { name: "generated-csvs", selector: "section", nth: 1 },
      { name: "upload-readback", selector: "section", nth: 2 },
      { name: "sql-counts", selector: "section", nth: 3 },
    ],
  },
  {
    slug: "06-incident-report",
    file: "omija_demo.html",
    title: "사건 보고서",
    purpose: "synthetic incident scenario에서 active-on-top, of/targets, blast radius, human-reviewed draft를 설명한다.",
    features: [
      { name: "incident-top", selector: "body", mode: "viewport", scrollY: 0 },
      { name: "incident-summary", selector: "section", nth: 0 },
      { name: "triage-and-bands", selector: "section", nth: 1 },
      { name: "comparison-panel", selector: "section", nth: 2 },
      { name: "blast-radius-path", selector: "section", nth: 3 },
      { name: "human-review-draft", selector: "section", nth: 5 },
      { name: "foundry-object-list-capture", selector: "figure.capslot", nth: 0 },
      { name: "foundry-action-types-capture", selector: "figure.capslot", nth: 1 },
      { name: "foundry-osdk-capture", selector: "figure.capslot", nth: 2 },
      { name: "outcome-summary", selector: "section", nth: 7 },
    ],
  },
  {
    slug: "07-program-threat-view",
    file: "program_threat_view.html",
    title: "프로그램 뷰",
    purpose: "프로그램에서 공급망/노출 경로를 역방향으로 보는 Q&A 백업 화면이다.",
    features: [
      { name: "program-top", selector: "body", mode: "viewport", scrollY: 0 },
      { name: "program-sections", selector: "section", nth: 0 },
    ],
  },
];

function safeText(text) {
  return text.replace(/\s+/g, " ").trim().slice(0, 240);
}

async function visible(locator) {
  try {
    return (await locator.count()) > 0 && (await locator.first().isVisible());
  } catch {
    return false;
  }
}

async function captureLocator(page, locator, outputPath) {
  await locator.scrollIntoViewIfNeeded();
  await page.waitForTimeout(120);
  await locator.screenshot({ path: outputPath, animations: "disabled" });
}

await mkdir(shotDir, { recursive: true });

const browser = await chromium.launch();
const manifest = {
  generated_at: new Date().toISOString(),
  tool: "npx -p playwright node scripts/capture_demo_screenshots.mjs",
  note: "Captured locally with Chromium. Playwright MCP namespace was not exposed in this Codex session.",
  viewport: { desktop: "1366x900", mobile: "390x844" },
  pages: [],
};

for (const entry of pages) {
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 }, deviceScaleFactor: 1 });
  const target = pathToFileURL(path.join(outDir, entry.file)).href;
  await page.goto(target, { waitUntil: "networkidle" });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.waitForTimeout(250);

  const pageRecord = {
    slug: entry.slug,
    title: entry.title,
    file: `out/${entry.file}`,
    purpose: entry.purpose,
    screenshots: [],
    features: [],
  };

  const fullName = `${entry.slug}--desktop-full.png`;
  await page.screenshot({ path: path.join(shotDir, fullName), fullPage: true, animations: "disabled" });
  pageRecord.screenshots.push({
    kind: "desktop-full-page",
    path: `out/screenshots/playwright/${fullName}`,
  });

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, deviceScaleFactor: 1 });
  await mobile.goto(target, { waitUntil: "networkidle" });
  await mobile.emulateMedia({ reducedMotion: "reduce" });
  await mobile.waitForTimeout(250);
  const mobileName = `${entry.slug}--mobile-top.png`;
  await mobile.screenshot({ path: path.join(shotDir, mobileName), fullPage: false, animations: "disabled" });
  pageRecord.screenshots.push({
    kind: "mobile-top-viewport",
    path: `out/screenshots/playwright/${mobileName}`,
  });
  await mobile.close();

  for (const feature of entry.features) {
    let locator = page.locator(feature.selector);
    if (typeof feature.nth === "number") {
      locator = locator.nth(feature.nth);
    } else {
      locator = locator.first();
    }

    if (feature.mode === "viewport") {
      await page.evaluate((scrollY) => window.scrollTo(0, scrollY), feature.scrollY ?? 0);
      await page.waitForTimeout(120);
      const name = `${entry.slug}--feature-${feature.name}.png`;
      await page.screenshot({ path: path.join(shotDir, name), fullPage: false, animations: "disabled" });
      pageRecord.features.push({
        name: feature.name,
        selector: feature.selector,
        screenshot: `out/screenshots/playwright/${name}`,
        excerpt: safeText(await page.locator("body").innerText()),
      });
      continue;
    }

    if (!(await visible(locator))) {
      pageRecord.features.push({
        name: feature.name,
        selector: `${feature.selector}${typeof feature.nth === "number" ? `[${feature.nth}]` : ""}`,
        screenshot: null,
        warning: "locator not visible",
      });
      continue;
    }

    const name = `${entry.slug}--feature-${feature.name}.png`;
    await captureLocator(page, locator, path.join(shotDir, name));
    pageRecord.features.push({
      name: feature.name,
      selector: `${feature.selector}${typeof feature.nth === "number" ? `[${feature.nth}]` : ""}`,
      screenshot: `out/screenshots/playwright/${name}`,
      excerpt: safeText(await locator.innerText()),
    });
  }

  manifest.pages.push(pageRecord);
  await page.close();
}

await browser.close();
await writeFile(path.join(shotDir, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n");
console.log(`Captured ${manifest.pages.length} pages into ${path.relative(repoRoot, shotDir)}`);
