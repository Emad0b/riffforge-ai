import { test, expect } from "@playwright/test";
test("real riff: upload, inference, audio sync, correction and exports", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Hear it. Forge it." }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Transcribe reference riff" }),
  ).toBeEnabled();
  await page.screenshot({
    path: "../../docs/studio-empty.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Transcribe reference riff" }).click();
  await expect(
    page.getByRole("img", { name: "Interactive six-string guitar tablature" }),
  ).toBeVisible({ timeout: 90000 });
  await expect(page.getByText("14 notes", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Play audio", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Pause audio", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".time")).not.toHaveText("0.0 / 15.0s");
  await page.getByRole("button", { name: "Pause audio", exact: true }).click();
  await page.getByRole("button", { name: "Loop full clip" }).click();
  await expect(
    page.getByRole("button", { name: "Loop full clip" }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.getByLabel("Playback speed").selectOption("0.75");
  await page.locator(".tab-note").first().click();
  await expect(page.getByRole("dialog")).toBeVisible();
  const old = Number(
    await page.getByLabel("Fret", { exact: true }).inputValue(),
  );
  await page
    .getByLabel("Fret", { exact: true })
    .fill(String(old === 24 ? 23 : old + 1));
  await page.getByRole("button", { name: "Save correction" }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  const jsonDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "JSON", exact: true }).click();
  const json = await jsonDownload;
  expect(json.suggestedFilename()).toBe("riffforge.json");
  const midiDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "MIDI", exact: true }).click();
  expect((await midiDownload).suggestedFilename()).toBe("riffforge.mid");
  await page.screenshot({ path: "../../docs/studio.png", fullPage: true });
  expect(errors).toEqual([]);
});
test("mobile layout and invalid upload", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Choose audio file" }),
  ).toBeEnabled();
  await page
    .getByLabel("Upload audio")
    .setInputFiles({
      name: "fake.wav",
      mimeType: "audio/wav",
      buffer: Buffer.from("not audio"),
    });
  await expect(page.locator('.error[role="alert"]')).toContainText(
    "Unsupported audio signature",
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
});
