const { test, expect } = require("@playwright/test");

async function login(page) {
  await page.goto("/");
  await page.locator("#username").fill("student1");
  await page.locator("#password").fill("student123");
  await page.locator("#login-form button[type=submit]").click();
  await expect(page.locator("#app-view")).toBeVisible();
  await expect(page.locator("#review-status-text")).not.toHaveText("載入中");
}

async function completeAllLessons(page) {
  await page.evaluate(async () => {
    const token = localStorage.getItem("pet_token");
    const headers = {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };
    const lessonResponse = await fetch("/api/lessons", { headers });
    if (!lessonResponse.ok) throw new Error("Unable to load lessons");
    const { lessons } = await lessonResponse.json();

    for (const lesson of lessons) {
      const response = await fetch(`/api/lessons/${lesson.id}/complete`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          checkpoint_correct_count: 0,
          checkpoint_total_count: 0,
        }),
      });
      if (!response.ok) throw new Error(`Unable to complete lesson ${lesson.id}`);
    }
  });
}

function collectBrowserErrors(page, errors) {
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));
}

test("總複習可解鎖、完成 20 題並支援手機版", async ({ page, browser }, testInfo) => {
  const browserErrors = [];
  collectBrowserErrors(page, browserErrors);

  await login(page);
  await expect(page.locator("#runner-input-panel")).toBeHidden();
  await expect(page.locator("#lessons-nav")).toBeHidden();
  await expect(page.locator("#start-review")).toBeDisabled();
  await expect(page.locator("#review-status-text")).toContainText("尚有 32 節課程未完成");

  await page.locator("#projects-nav").click();
  await expect(page.locator("#page-title")).toHaveText("實作區");
  await expect(page.locator("#project-list .project-card")).toHaveCount(5);
  await page.locator("#project-list .project-card").first().locator(".project-open").click();
  await expect(page.locator("#project-example-code")).toContainText('print("小明")');
  await expect(page.locator("#project-example-output")).toHaveText("小明");
  await expect(page.locator("#project-code")).toHaveValue("");
  await expect(page.locator("#project-code")).not.toHaveAttribute("readonly", "");
  await expect(page.locator("#project-input-panel")).toBeHidden();
  await expect(page.locator("#project-run")).toHaveText("試跑我的程式");
  await expect(page.locator("#project-test")).toBeHidden();
  await expect(page.locator("#project-complete")).toBeHidden();
  await page.locator("#lessons-nav").click();
  await expect(page.locator("#page-title")).toHaveText("今日課程");

  await page.locator('[data-lesson-id="lesson-08-builtins-and-custom-functions"]').click();
  await expect(page.locator("#lesson-title")).toHaveText("內建函式與自訂函式");
  await expect(page.locator("#lesson-body .token.builtin").first()).toBeVisible();
  await expect(page.locator("#lesson-body .token.function:not(.builtin)").first()).toBeVisible();
  await expect(page.locator("#lesson-body .token.builtin-method").first()).toBeVisible();
  await expect(page.locator("#lesson-body .inline-code").first()).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("syntax-highlighting-desktop.png"), fullPage: true });

  await completeAllLessons(page);
  await page.reload();
  await expect(page.locator("#app-view")).toBeVisible();
  await expect(page.locator("#review-status-text")).toContainText("已解鎖");
  await expect(page.locator("#start-review")).toBeEnabled();

  await page.locator("#start-review").click();
  await expect(page.locator("#page-title")).toHaveText("總複習");
  await expect(page.locator("#lessons-nav")).toBeVisible();
  await expect(page.locator("#review-progress")).toHaveText("總複習 1 / 20");
  await expect(page.locator("#next-question")).toBeDisabled();
  await page.locator("input[name=answer]").first().check();
  await page.locator("#submit-answer").click();
  await expect(page.locator("#feedback")).toBeVisible();
  await expect(page.locator("#submit-answer")).toBeDisabled();
  await expect(page.locator("#next-question")).toBeEnabled();
  const reviewLessonLink = page.locator(".review-lesson").first();
  if (await reviewLessonLink.count()) {
    await reviewLessonLink.click();
    await expect(page.locator("#lesson-panel")).toBeVisible();
    await expect(page.locator("#review-nav")).toBeVisible();
    await expect(page.locator("#lessons-nav")).toBeHidden();
    await expect(page.locator("#projects-nav")).toBeHidden();
    await page.locator("#review-nav").click();
    await expect(page.locator("#page-title")).toHaveText("總複習");
    await expect(page.locator("#question-panel")).toBeVisible();
    await expect(page.locator("#feedback")).toBeVisible();
    await expect(page.locator("#lessons-nav")).toBeVisible();
  }
  await page.screenshot({ path: testInfo.outputPath("review-desktop.png"), fullPage: true });

  const desktopOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(desktopOverflow).toBe(false);

  const mobileContext = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const mobilePage = await mobileContext.newPage();
  collectBrowserErrors(mobilePage, browserErrors);
  await login(mobilePage);
  await expect(mobilePage.locator("#review-status-text")).toContainText("已解鎖");
  await mobilePage.locator("#start-review").click();

  for (let number = 1; number <= 20; number += 1) {
    await expect(mobilePage.locator("#review-progress")).toHaveText(`總複習 ${number} / 20`);
    await mobilePage.locator("input[name=answer]").first().check();
    await mobilePage.locator("#submit-answer").click();
    await expect(mobilePage.locator("#submit-answer")).toBeDisabled();
    if (number === 20) {
      await expect(mobilePage.locator("#next-question")).toHaveText("查看本輪結果");
    }
    await mobilePage.locator("#next-question").click();
  }

  await expect(mobilePage.locator("#review-summary-panel")).toBeVisible();
  await expect(mobilePage.locator("#review-round-correct")).toContainText("/ 20");
  await expect(mobilePage.locator("#restart-review")).toBeVisible();
  await expect(mobilePage.locator("#leave-review")).toBeVisible();
  await expect(mobilePage.locator("#lessons-nav")).toBeHidden();
  await mobilePage.screenshot({ path: testInfo.outputPath("review-mobile-summary.png"), fullPage: true });

  const mobileOverflow = await mobilePage.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(mobileOverflow).toBe(false);
  expect(browserErrors).toEqual([]);
  await mobileContext.close();
});
