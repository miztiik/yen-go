/**
 * Contract test: Validates v4.0 TypeScript types match JSON Schema definitions.
 * Source of truth: config/schemas/view-index.schema.json
 * Spec: 131-frontend-view-schema (T003)
 */
import { describe, it, expect } from "vitest";
import viewSchema from "../../../config/schemas/view-index.schema.json";

// Access $defs directly
const defs = viewSchema.$defs;

describe("View Schema Contract v4.0", () => {
  describe("ViewType enum", () => {
    it("matches TypeScript union ['level', 'tag', 'collection', 'daily']", () => {
      expect(defs.ViewType.enum).toEqual(["level", "tag", "collection", "daily"]);
    });
  });

  describe("Compact entry types", () => {
    it("CompactEntry requires p, l, t, c, x", () => {
      expect(defs.CompactEntry.required).toEqual(["p", "l", "t", "c", "x"]);
      expect(defs.CompactEntry.properties.p.type).toBe("string");
      expect(defs.CompactEntry.properties.l.type).toBe("integer");
      expect(defs.CompactEntry.properties.t.type).toBe("array");
      expect(defs.CompactEntry.properties.c.type).toBe("array");
      expect(defs.CompactEntry.properties.x.type).toBe("array");
      expect(defs.CompactEntry.properties.x.minItems).toBe(4);
      expect(defs.CompactEntry.properties.x.maxItems).toBe(4);
    });

    it("CompactCollectionEntry requires p, l, t, c, x, n", () => {
      expect(defs.CompactCollectionEntry.required).toEqual([
        "p", "l", "t", "c", "x", "n",
      ]);
      expect(defs.CompactCollectionEntry.properties.n.type).toBe("integer");
      expect(defs.CompactCollectionEntry.properties.n.minimum).toBe(1);
    });
  });

  describe("Document types", () => {
    it("PageDocument requires type, name, page, entries", () => {
      expect(defs.PageDocument.required).toEqual([
        "type",
        "name",
        "page",
        "entries",
      ]);
      expect(defs.PageDocument.properties.page.minimum).toBe(1);
    });

    it("DirectoryIndex requires type, name, total_count, page_size, pages", () => {
      expect(defs.DirectoryIndex.required).toEqual([
        "type",
        "name",
        "total_count",
        "page_size",
        "pages",
      ]);
      expect(defs.DirectoryIndex.properties.total_count.minimum).toBe(0);
      expect(defs.DirectoryIndex.properties.page_size.minimum).toBe(1);
      expect(defs.DirectoryIndex.properties.pages.minimum).toBe(1);
    });
  });

  describe("Master index types v2.0", () => {
    it("MasterIndexEntry requires id, name, slug, count, pages", () => {
      expect(defs.MasterIndexEntry.required).toEqual([
        "id",
        "name",
        "slug",
        "count",
        "pages",
      ]);
    });

    it("MasterIndexEntry has optional distributions", () => {
      expect(defs.MasterIndexEntry.properties).toHaveProperty("levels");
      expect(defs.MasterIndexEntry.properties).toHaveProperty("tags");
    });

    it("LevelMasterIndex requires version 2.0, generated_at, levels", () => {
      expect(defs.LevelMasterIndex.required).toEqual([
        "version",
        "generated_at",
        "levels",
      ]);
      expect(defs.LevelMasterIndex.properties.version.const).toBe("2.0");
    });

    it("TagMasterIndex requires version 2.0, generated_at, tags", () => {
      expect(defs.TagMasterIndex.required).toEqual([
        "version",
        "generated_at",
        "tags",
      ]);
      expect(defs.TagMasterIndex.properties.version.const).toBe("2.0");
    });

    it("CollectionMasterIndex requires version 2.0, generated_at, collections", () => {
      expect(defs.CollectionMasterIndex.required).toEqual([
        "version",
        "generated_at",
        "collections",
      ]);
      expect(defs.CollectionMasterIndex.properties.version.const).toBe("2.0");
    });

    it("DailyMasterIndex requires version 2.0, generated_at, dates", () => {
      expect(defs.DailyMasterIndex.required).toEqual([
        "version",
        "generated_at",
        "dates",
      ]);
      expect(defs.DailyMasterIndex.properties.version.const).toBe("2.0");
    });
  });

  describe("Schema has no puzzles field", () => {
    it("PageDocument uses entries not puzzles", () => {
      expect(defs.PageDocument.properties).toHaveProperty("entries");
      expect(defs.PageDocument.properties).not.toHaveProperty("puzzles");
    });
  });
});
