# Playwright image đã kèm Chromium + dependency hệ thống.
FROM mcr.microsoft.com/playwright:v1.49.1-jammy

WORKDIR /app

COPY package.json ./
# Bỏ postinstall (browser đã có sẵn trong image) để build nhanh.
RUN npm install --omit=dev --ignore-scripts

COPY . .

ENV GGB_SERVICE_PORT=8081
EXPOSE 8081

CMD ["node", "src/server.js"]
