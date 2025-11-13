# Build stage
FROM node:20-bullseye-slim AS build
WORKDIR /app

# Set environment variables to prevent SWC download issues
ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_SWC_DOWNLOAD_TIMEOUT=300000

# Copy package files
COPY package*.json ./

# Install dependencies with cache mount for faster rebuilds
RUN --mount=type=cache,target=/root/.npm npm ci

# Copy source code
COPY . .

# Build the application with retry logic
RUN rm -rf .next /root/.cache && npm run build

# Production stage
FROM node:20-bullseye-slim AS production
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install only production dependencies with cache mount
RUN --mount=type=cache,target=/root/.npm npm ci --only=production && npm cache clean --force

# Copy built application from build stage
COPY --from=build /app/.next ./.next
COPY --from=build /app/public ./public
COPY --from=build /app/next.config.js ./

# Expose port 3000 (Next.js default)
EXPOSE 3000

# Start the application
CMD ["npm", "start"]