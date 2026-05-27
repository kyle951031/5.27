# 智慧鏡頭即時發票對獎系統

這是一個純前端網站，使用瀏覽器攝影機與 Tesseract.js 進行 OCR 辨識，並自動比對最新發票中獎號碼。

## 專案內容

- 純前端 HTML/CSS/JavaScript 應用
- 瀏覽器拍照、圖片上傳
- 即時 OCR 文字辨識
- 自動抓取最新中獎號碼 JSON
- 8 碼發票號碼擷取與對獎結果顯示
- Chart.js 圓餅圖顯示中獎統計

## 相關檔案

- `index.html` - 前端網頁入口
- `static/style.css` - 網頁樣式
- `static/main.js` - 前端對獎邏輯
- `smart_invoice_lottery.py` - 桌面程式（可保留參考）
- `app.py`、`templates/` - 原 Flask 版本，可保留但不再作為部署主體

## 本機測試

可直接用靜態伺服器測試：

```bash
python -m http.server 8000
```

然後開啟瀏覽器並訪問：

```bash
http://127.0.0.1:8000
```

## GitHub Pages 部署

此專案可直接部署到 GitHub Pages，無需後端伺服器。只要將所有檔案推送到倉庫後，在 GitHub Pages 設定中啟用 `main` 分支的根目錄即可。

```bash
git init
git add .
git commit -m "Add frontend invoice lottery web app"
git branch -M main
git remote add origin https://github.com/你的帳號/你的倉庫.git
git push -u origin main
```

## 使用方式

1. 開啟網站。
2. 點擊「啟用攝影機」。
3. 將發票對準鏡頭並按「拍照送出」。
4. 或選擇圖片上傳進行對獎。

## 注意事項

- 瀏覽器需要允許攝影機權限。
- OCR 以 8 碼數字辨識為主，請盡量拍攝清晰發票號碼區塊。
- 若線上中獎號碼無法取得，網站會改用內建預設號碼。
