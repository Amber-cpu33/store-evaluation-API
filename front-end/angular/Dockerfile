# 階段一：建置應用程式 (Build Stage)
FROM node:lts-alpine as build-stage

# 設定工作目錄
WORKDIR /app

# 1. 先複製 package 檔案以利用 Docker 快取層
COPY package*.json ./

# 2. 安裝所有依賴
RUN npm install

RUN npm install -g @angular/cli

# 3. 複製其餘原始碼
COPY . .

# 4. 關鍵：執行 npm script 而非直接執行 ng 指令
# 這會調用 node_modules/.bin/ng，避免 "Cannot find module" 錯誤
RUN npm run build -- --configuration production

# 5. 啟動
CMD ["ng", "serve", "--host", "0.0.0.0", "--port", "4200"]