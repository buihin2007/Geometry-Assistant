import { chromium } from "playwright";

// Pool nhỏ các trang GeoGebra headless tái dùng giữa các request.
// 20 user bursty → pool 1–2 là đủ; request vượt pool sẽ xếp hàng (acquire chờ).
export class GgbPool {
  constructor({ hostUrl, size = 1, readyTimeoutMs = 60000 }) {
    this.hostUrl = hostUrl;
    this.size = size;
    this.readyTimeoutMs = readyTimeoutMs;
    this.browser = null;
    this.idle = []; // các page sẵn sàng
    this.waiters = []; // resolver đang chờ page
    this.total = 0;
  }

  async init() {
    this.browser = await chromium.launch({
      headless: true,
      args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
    });
  }

  async _newPage() {
    const context = await this.browser.newContext({
      viewport: { width: 960, height: 760 },
    });
    const page = await context.newPage();
    await page.goto(this.hostUrl, { waitUntil: "domcontentloaded" });
    // Chờ applet GeoGebra báo sẵn sàng.
    await page.waitForFunction(() => window.__ggbReady === true, null, {
      timeout: this.readyTimeoutMs,
    });
    this.total += 1;
    return page;
  }

  async acquire() {
    if (this.idle.length > 0) return this.idle.pop();
    if (this.total < this.size) return await this._newPage();
    // Hết slot → chờ page được release.
    return await new Promise((resolve) => this.waiters.push(resolve));
  }

  release(page) {
    const waiter = this.waiters.shift();
    if (waiter) waiter(page);
    else this.idle.push(page);
  }

  async _recyclePage(page) {
    // Page lỗi → đóng và tạo mới để giữ pool khỏe.
    try {
      this.total -= 1;
      await page.context().close();
    } catch (e) {}
    try {
      return await this._newPage();
    } catch (e) {
      return null;
    }
  }

  // Chạy một job với một page mượn từ pool. Tự reset construction trước.
  async withPage(fn) {
    let page = await this.acquire();
    try {
      await page.evaluate(() => window.__ggbReset());
      const result = await fn(page);
      this.release(page);
      return result;
    } catch (err) {
      // Page có thể đã hỏng → thay mới rồi trả về pool.
      const fresh = await this._recyclePage(page);
      if (fresh) this.release(fresh);
      throw err;
    }
  }

  async close() {
    if (this.browser) await this.browser.close();
  }
}
