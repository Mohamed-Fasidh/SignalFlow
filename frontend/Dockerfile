FROM node:22-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ARG NEXT_PUBLIC_DEMO_TENANT_ID=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_DEMO_TENANT_ID=$NEXT_PUBLIC_DEMO_TENANT_ID
RUN npm run typecheck && npm run build
EXPOSE 3000
CMD ["npm", "run", "start"]
