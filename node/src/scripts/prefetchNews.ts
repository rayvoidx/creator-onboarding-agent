import { refreshNewsCache } from '../services/newsService';

async function main() {
  const items = await refreshNewsCache();
  console.log(`Refreshed news cache with ${items.length} items.`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});


