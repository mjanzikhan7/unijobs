# The image version must match the @playwright/test version in package.json.
FROM mcr.microsoft.com/playwright:v1.63.0-noble

WORKDIR /tests
COPY package.json package-lock.json ./
RUN npm ci

COPY playwright.config.ts tsconfig.json ./
COPY specs ./specs

CMD ["npx", "playwright", "test"]
