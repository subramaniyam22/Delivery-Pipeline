FROM node:20-alpine

WORKDIR /app

# Build argument for API URL (set in Render)
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy application code
COPY . .

# Build the application with the env var available
RUN npm run build

# Expose port (Render uses PORT env var)
EXPOSE 3000

# Start the application with PORT from environment
CMD ["sh", "-c", "npx next start -H 0.0.0.0 -p ${PORT:-3000}"]
