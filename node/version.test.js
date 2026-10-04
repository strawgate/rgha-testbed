import { test } from "node:test";
import assert from "node:assert/strict";
import semver from "semver";

test("semver from the npm registry works", () => {
  assert.ok(semver.gt("1.2.3", "1.2.2"));
});

test("runner has a sane Node", () => {
  assert.ok(semver.gte(process.versions.node, "20.0.0"));
});
