FROM node:20-alpine AS builder

WORKDIR /app

# 의존성 설치
COPY package*.json ./
RUN npm ci

# 소스 복사 및 빌드
COPY . .
RUN npm run build

# 프로덕션 이미지
FROM node:20-alpine

WORKDIR /app

# 빌드 결과물만 복사
COPY --from=builder /app/build ./build
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/node_modules ./node_modules

ENV NODE_ENV=production
ENV PORT=3000

EXPOSE 3000

CMD ["node", "build"]
