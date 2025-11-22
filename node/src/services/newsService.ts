import fs from 'fs';
import path from 'path';
import Parser from 'rss-parser';

export type NewsItem = {
  title: string;
  link?: string;
  pubDate?: string;
  source?: string;
};

const CACHE_DIR = path.join(process.cwd(), 'data');
const CACHE_FILE = path.join(CACHE_DIR, 'news.cache.json');

function ensureCacheDir(): void {
  if (!fs.existsSync(CACHE_DIR)) {
    fs.mkdirSync(CACHE_DIR, { recursive: true });
  }
}

export async function refreshNewsCache(feeds?: string[]): Promise<NewsItem[]> {
  const rss = new Parser();
  const feedUrls = feeds && feeds.length > 0 ? feeds : [
    'https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en',
    'https://hnrss.org/frontpage'
  ];

  const results: NewsItem[] = [];
  for (const url of feedUrls) {
    try {
      const parsed = await rss.parseURL(url);
      for (const it of parsed.items.slice(0, 10)) {
        results.push({
          title: it.title || '',
          link: it.link,
          pubDate: it.pubDate,
          source: parsed.title || url
        });
      }
    } catch {
      // ignore single feed error
    }
  }

  ensureCacheDir();
  fs.writeFileSync(CACHE_FILE, JSON.stringify({ updatedAt: Date.now(), items: results }, null, 2), 'utf-8');
  return results;
}

export function readNewsCache(): { updatedAt?: number; items: NewsItem[] } {
  try {
    const raw = fs.readFileSync(CACHE_FILE, 'utf-8');
    const data = JSON.parse(raw);
    return { updatedAt: data.updatedAt, items: Array.isArray(data.items) ? data.items : [] };
  } catch {
    return { items: [] };
  }
}


