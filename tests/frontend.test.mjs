import test from "node:test";
import assert from "node:assert/strict";
import { rollingMonths, monthKey, isInRollingWindow } from "../public/date-utils.js";

test("rolling months cross a year boundary", () => {
  assert.deepEqual(rollingMonths(new Date(2026, 10, 15)).map(monthKey), ["2026-11", "2026-12", "2027-01"]);
});
test("window includes only the displayed months", () => {
  const now = new Date(2026, 8, 3);
  assert.equal(isInRollingWindow("2026-11-30", now), true);
  assert.equal(isInRollingWindow("2026-12-01", now), false);
});
