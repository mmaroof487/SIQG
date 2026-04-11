FROM node:20-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm config set fetch-timeout 120000 && \
    npm config set fetch-retry-mintimeout 20000 && \
    npm config set fetch-retry-maxtimeout 120000 && \
    npm config set fetch-retries 10 && \
    npm config set registry https://registry.npmjs.org && \
    npm ci --prefer-offline --no-audit --legacy-peer-deps


COPY . .

EXPOSE 3001

# Run the Vite dev server binding to all network interfaces
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3001"]
