# syntax=docker/dockerfile:1
#
# The build context is the repository root, because the app depends on the workspace
# package in packages/accessibility-toolbar.
#
#   development  Vite dev server
#   production   nginx gateway: serves the built app and passes /api to the backend

ARG NODE_VERSION=22

# ---------------------------------------------------------------- dependencies
# Debian, not Alpine. Tailwind's CSS engine ships a native binary, and npm does not
# always pick the right one for Alpine's C library.
FROM node:${NODE_VERSION}-bookworm-slim AS dependencies

WORKDIR /app
COPY package.json package-lock.json ./
COPY frontend/package.json ./frontend/package.json
COPY packages/accessibility-toolbar/package.json ./packages/accessibility-toolbar/package.json
RUN --mount=type=cache,target=/root/.npm \
    npm ci

# ---------------------------------------------------------------- development
FROM dependencies AS development

COPY frontend ./frontend
COPY packages ./packages
RUN npm run build --workspace=@unijobs/a11y

WORKDIR /app/frontend
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ---------------------------------------------------------------- build
FROM dependencies AS build

COPY frontend ./frontend
COPY packages ./packages
RUN npm run build --workspace=@unijobs/a11y \
    && npm run build --workspace=frontend

# ---------------------------------------------------------------- production
# The unprivileged image runs nginx as a normal user, on port 8080.
FROM nginxinc/nginx-unprivileged:1.29-alpine AS production

COPY frontend/nginx/security-headers.conf /etc/nginx/snippets/security-headers.conf
COPY frontend/nginx/gateway.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/frontend/dist /usr/share/nginx/html

EXPOSE 8080
