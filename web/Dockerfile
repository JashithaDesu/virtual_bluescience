FROM node:24-bookworm-slim
WORKDIR /app
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
EXPOSE 5180
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5180", "--strictPort"]
