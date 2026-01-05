FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy application code
COPY . .

# Build the application
RUN npm run build

# Expose port (Render uses PORT env var)
EXPOSE 3000

# Start the application with PORT from environment
CMD ["sh", "-c", "npx next start -H 0.0.0.0 -p ${PORT:-3000}"]
