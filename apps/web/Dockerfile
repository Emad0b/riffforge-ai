FROM node:22-slim
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ENV API_URL=http://api:8400
RUN npm run build
USER node
CMD ["npm", "start"]
