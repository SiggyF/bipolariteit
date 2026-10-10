// Tegelcache voor een pmtiles-archief in de browser (issue #390).
//
// Waarom: Hugging Face (resolve/main/...) antwoordt met een 302 met
// `cache-control: no-store`, en de CDN-respons erachter heeft wel een ETag maar
// geen Cache-Control of Last-Modified. De browser-HTTP-cache hergebruikt zulke
// range-responses daardoor niet, en de pmtiles-bibliotheek bewaart zelf alleen
// header en directories. Elke herlaad haalde dus alle tegelbytes opnieuw op.
//
// Aanpak: een `Source`-wrapper die range-responses in IndexedDB bewaart,
// gesleuteld op de ETag van het archief. De ETag komt uit de allereerste
// header-aanroep (offset 0, die gaat altijd naar het netwerk); alle volgende
// aanroepen krijgen hem van de PMTiles-instantie mee. Wijzigt het archief
// (nieuwe ETag), dan zijn de oude entries onbereikbaar en worden ze opgeruimd.
// IndexedDB i.p.v. Cache Storage omdat dat ook in niet-secure contexts werkt
// (bv. een dev-server op een LAN-adres).

import type { RangeResponse, Source } from "pmtiles";

/** Minimale key-value-opslag voor bytes; in de browser IndexedDB, in tests een Map. */
export interface ByteStore {
	get(key: string): Promise<ArrayBuffer | undefined>;
	set(key: string, data: ArrayBuffer): Promise<void>;
	/** Verwijder alle entries waarvan de sleutel niet met `prefix` begint. */
	deleteExceptPrefix(prefix: string): Promise<void>;
}

export type CacheAccess = { hit: boolean; offset: number; length: number };

export class CachedPmtilesSource implements Source {
	private prunedFor: string | null = null;

	constructor(
		private readonly inner: Source,
		private readonly store: ByteStore | null,
		private readonly onAccess?: (access: CacheAccess) => void,
	) {}

	getKey(): string {
		return this.inner.getKey();
	}

	async getBytes(offset: number, length: number, signal?: AbortSignal, etag?: string): Promise<RangeResponse> {
		if (this.store && etag) {
			const cached = await this.safely(() => this.store!.get(entryKey(etag, offset, length)));
			if (cached) {
				this.onAccess?.({ hit: true, offset, length });
				return { data: cached, etag };
			}
		}
		const response = await this.inner.getBytes(offset, length, signal, etag);
		const responseEtag = response.etag ?? etag;
		if (this.store && responseEtag) {
			this.onAccess?.({ hit: false, offset, length });
			const store = this.store;
			// Niet wachten: een trage of volle opslag mag het tonen van de kaart niet ophouden.
			void this.safely(async () => {
				if (this.prunedFor !== responseEtag) {
					this.prunedFor = responseEtag;
					await store.deleteExceptPrefix(`${responseEtag}/`);
				}
				await store.set(entryKey(responseEtag, offset, length), response.data.slice(0));
			});
		}
		return response;
	}

	private async safely<T>(action: () => Promise<T>): Promise<T | undefined> {
		try {
			return await action();
		} catch (err) {
			console.warn("pmtiles-tegelcache niet beschikbaar", err);
			return undefined;
		}
	}
}

export function entryKey(etag: string, offset: number, length: number): string {
	return `${etag}/${offset}-${length}`;
}

/** IndexedDB-opslag; null als IndexedDB ontbreekt (bv. sommige privévensters). */
export function openIndexedDbStore(name = "pmtiles-tile-cache"): ByteStore | null {
	if (typeof indexedDB === "undefined") return null;
	const STORE = "ranges";
	let dbPromise: Promise<IDBDatabase> | null = null;
	const open = () => {
		dbPromise ??= new Promise<IDBDatabase>((resolve, reject) => {
			const request = indexedDB.open(name, 1);
			request.onupgradeneeded = () => request.result.createObjectStore(STORE);
			request.onsuccess = () => resolve(request.result);
			request.onerror = () => reject(request.error);
		});
		return dbPromise;
	};
	const run = async <T>(mode: IDBTransactionMode, work: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> => {
		const db = await open();
		return new Promise<T>((resolve, reject) => {
			const request = work(db.transaction(STORE, mode).objectStore(STORE));
			request.onsuccess = () => resolve(request.result);
			request.onerror = () => reject(request.error);
		});
	};
	return {
		get: (key) => run<ArrayBuffer | undefined>("readonly", (store) => store.get(key)),
		set: async (key, data) => {
			await run("readwrite", (store) => store.put(data, key));
		},
		deleteExceptPrefix: async (prefix) => {
			const keys = (await run<IDBValidKey[]>("readonly", (store) => store.getAllKeys())).map(String);
			for (const key of keys) {
				if (!key.startsWith(prefix)) await run("readwrite", (store) => store.delete(key));
			}
		},
	};
}
