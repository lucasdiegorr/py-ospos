import "@testing-library/jest-dom/vitest";

if (typeof navigator === "undefined") {
  Object.defineProperty(global, "navigator", {
    value: { clipboard: { writeText: () => {} } },
    writable: true,
    configurable: true,
  });
}
