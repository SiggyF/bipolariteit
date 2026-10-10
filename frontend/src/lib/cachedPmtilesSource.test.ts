import { describe, expect, it, vi } from "vitest";
import type { RangeResponse, Source } from "pmtiles";
import { CachedPmtilesSource, type ByteStore, type CacheAccess } from "./cachedPmtilesSource";

function memoryStore(): ByteStore & { map: Map<string, ArrayBuffer> } {
	const map = new Map<string, ArrayBuffer>();
	return {
		map,
		get: async (key) => map.get(key),
		set: async (key, data) => void map.set(key, data),
		deleteExceptPrefix: async (prefix) => {
			for (const key of [...map.keys()]) if (!key.startsWith(prefix)) map.delete(key);
		},
	};
}

function innerSource(etag: string | undefined, bytes = 4): Source & { calls: number } {
	const source = {
		calls: 0,
		getKey: () => "https://example.test/a.pmtiles",
		getBytes: async (): Promise<RangeResponse> => {
			source.calls += 1;
			return { data: new Uint8Array(bytes).fill(7).buffer, etag };
		},
	};
	return source;
}

const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

describe("CachedPmtilesSource", () => {
	it("haalt de eerste keer op en serveert daarna uit de opslag", async () => {
		const store = memoryStore();
		const inner = innerSource('"abc"');
		const accesses: CacheAccess[] = [];
		const source = new CachedPmtilesSource(inner, store, (a) => accesses.push(a));

		await source.getBytes(100, 4, undefined, '"abc"');
		await flush();
		const second = await source.getBytes(100, 4, undefined, '"abc"');

		expect(inner.calls).toBe(1);
		expect(new Uint8Array(second.data)).toEqual(new Uint8Array([7, 7, 7, 7]));
		expect(accesses.map((a) => a.hit)).toEqual([false, true]);
	});

	it("gaat zonder etag altijd naar het netwerk (de header-aanroep)", async () => {
		const store = memoryStore();
		const inner = innerSource('"abc"');
		const source = new CachedPmtilesSource(inner, store);
		await source.getBytes(0, 16384);
		await flush();
		await source.getBytes(0, 16384);
		expect(inner.calls).toBe(2);
	});

	it("negeert opgeslagen bytes van een andere etag en ruimt ze op", async () => {
		const store = memoryStore();
		store.map.set('"old"/100-4', new ArrayBuffer(4));
		const inner = innerSource('"new"');
		const source = new CachedPmtilesSource(inner, store);

		await source.getBytes(100, 4, undefined, '"new"');
		await flush();

		expect(inner.calls).toBe(1);
		expect([...store.map.keys()]).toEqual(['"new"/100-4']);
	});

	it("werkt zonder opslag gewoon door", async () => {
		const inner = innerSource('"abc"');
		const source = new CachedPmtilesSource(inner, null);
		const response = await source.getBytes(100, 4, undefined, '"abc"');
		expect(response.data.byteLength).toBe(4);
		expect(inner.calls).toBe(1);
	});

	it("laat een kapotte opslag de kaart niet breken", async () => {
		vi.spyOn(console, "warn").mockImplementation(() => {});
		const broken: ByteStore = {
			get: async () => {
				throw new Error("quota");
			},
			set: async () => {
				throw new Error("quota");
			},
			deleteExceptPrefix: async () => {},
		};
		const inner = innerSource('"abc"');
		const source = new CachedPmtilesSource(inner, broken);
		const response = await source.getBytes(100, 4, undefined, '"abc"');
		await flush();
		expect(response.data.byteLength).toBe(4);
	});
});
