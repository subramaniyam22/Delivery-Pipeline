FROM node:20-alpine

WORKDIR /app

# Disable Next.js telemetry
ENV NEXT_TELEMETRY_DISABLED=1

# Copy package files
COPY package*.json ./

# Install dependencies (avoid peer conflicts in CI)
RUN npm ci --legacy-peer-deps

# Copy application code
COPY . .

# Build the application (cache bust with timestamp)
ARG CACHEBUST=1
RUN echo "Build: $CACHEBUST" && npm run build

# Expose port (Render uses PORT env var)
EXPOSE 3000

# Start the application with PORT from environment
CMD ["sh", "-c", "npx next start -H 0.0.0.0 -p ${PORT:-3000}"]
